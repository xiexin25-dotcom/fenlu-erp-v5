"""WorkOrder CRUD endpoints · TASK-MFG-002。

Routes:
    POST   /mfg/work-orders          创建工单
    GET    /mfg/work-orders           列表 (租户隔离)
    GET    /mfg/work-orders/{id}      单条
    PATCH  /mfg/work-orders/{id}/status  状态流转
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import WorkOrder
from packages.production.services.bom_client import BomClient, BomNotFoundError
from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Quantity, UnitOfMeasure
from packages.shared.contracts.production import WorkOrderDTO, WorkOrderStatus
from packages.shared.db import get_session

router = APIRouter(prefix="/work-orders", tags=["work-orders"])

# ── 合法状态流转 ────────────────────────────────────────────────────────────── #

_ALLOWED_TRANSITIONS: dict[WorkOrderStatus, list[WorkOrderStatus]] = {
    WorkOrderStatus.PLANNED: [WorkOrderStatus.RELEASED],
    WorkOrderStatus.RELEASED: [WorkOrderStatus.IN_PROGRESS],
    WorkOrderStatus.IN_PROGRESS: [WorkOrderStatus.COMPLETED],
    WorkOrderStatus.COMPLETED: [WorkOrderStatus.CLOSED],
    WorkOrderStatus.CLOSED: [],
}


# ── Request schemas ─────────────────────────────────────────────────────────── #


class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_no: str = Field(..., max_length=64)
    product_id: UUID
    bom_id: UUID
    routing_id: UUID
    planned_quantity: Quantity
    planned_start: datetime
    planned_end: datetime
    sales_order_id: UUID | None = None


class StatusTransition(BaseModel):
    status: WorkOrderStatus


# ── Helpers ─────────────────────────────────────────────────────────────────── #


def _to_dto(wo: WorkOrder) -> WorkOrderDTO:
    """ORM → WorkOrderDTO (Quantity 列拼回嵌套对象)。"""
    return WorkOrderDTO.model_validate(
        {
            "id": wo.id,
            "order_no": wo.order_no,
            "product_id": wo.product_id,
            "bom_id": wo.bom_id,
            "routing_id": wo.routing_id,
            "planned_quantity": {"value": wo.planned_quantity, "uom": wo.planned_quantity_uom},
            "completed_quantity": {
                "value": wo.completed_quantity,
                "uom": wo.completed_quantity_uom,
            },
            "scrap_quantity": {"value": wo.scrap_quantity, "uom": wo.scrap_quantity_uom},
            "status": wo.status,
            "planned_start": wo.planned_start,
            "planned_end": wo.planned_end,
            "actual_start": wo.actual_start,
            "actual_end": wo.actual_end,
            "sales_order_id": wo.sales_order_id,
            "created_at": wo.created_at,
            "updated_at": wo.updated_at,
        }
    )


# ── Endpoints ───────────────────────────────────────────────────────────────── #


@router.post("", response_model=WorkOrderDTO, status_code=201)
async def create_work_order(
    body: WorkOrderCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> WorkOrderDTO:
    wo = WorkOrder(
        tenant_id=user.tenant_id,
        order_no=body.order_no,
        product_id=body.product_id,
        bom_id=body.bom_id,
        routing_id=body.routing_id,
        planned_quantity=body.planned_quantity.value,
        planned_quantity_uom=body.planned_quantity.uom.value,
        completed_quantity=Decimal(0),
        completed_quantity_uom=body.planned_quantity.uom.value,
        scrap_quantity=Decimal(0),
        scrap_quantity_uom=body.planned_quantity.uom.value,
        status=WorkOrderStatus.PLANNED,
        planned_start=body.planned_start,
        planned_end=body.planned_end,
        sales_order_id=body.sales_order_id,
        created_by=user.id,
    )
    session.add(wo)
    await session.flush()
    await session.refresh(wo)
    return _to_dto(wo)


@router.get("", response_model=list[WorkOrderDTO])
async def list_work_orders(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[WorkOrderDTO]:
    result = await session.execute(
        select(WorkOrder)
        .where(WorkOrder.tenant_id == user.tenant_id)
        .order_by(WorkOrder.created_at.desc())
    )
    return [_to_dto(wo) for wo in result.scalars().all()]


@router.get("/{work_order_id}", response_model=WorkOrderDTO)
async def get_work_order(
    work_order_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> WorkOrderDTO:
    wo = (
        await session.execute(
            select(WorkOrder).where(
                WorkOrder.id == work_order_id,
                WorkOrder.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if wo is None:
        raise HTTPException(404, "work order not found")
    return _to_dto(wo)


@router.patch("/{work_order_id}/status", response_model=WorkOrderDTO)
async def transition_status(
    work_order_id: UUID,
    body: StatusTransition,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> WorkOrderDTO:
    wo = (
        await session.execute(
            select(WorkOrder).where(
                WorkOrder.id == work_order_id,
                WorkOrder.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if wo is None:
        raise HTTPException(404, "work order not found")

    current = WorkOrderStatus(wo.status)
    target = body.status
    allowed = _ALLOWED_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(
            422,
            f"cannot transition from {current.value} to {target.value}; "
            f"allowed: {[s.value for s in allowed]}",
        )

    # TASK-MFG-003: releasing requires BOM validation
    if target == WorkOrderStatus.RELEASED:
        bom_client = BomClient()
        try:
            await bom_client.get_bom(wo.bom_id)
        except BomNotFoundError:
            raise HTTPException(422, f"BOM {wo.bom_id} not found in PLM, cannot release")

    wo.status = target.value
    wo.updated_by = user.id
    await session.flush()
    await session.refresh(wo)
    return _to_dto(wo)
