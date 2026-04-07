"""APS (Advanced Planning & Scheduling) endpoint · TASK-MFG-011。

Routes:
    POST  /mfg/aps/run       运行排程,返回建议计划
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import WorkOrder, Workstation
from packages.production.services.aps import APSOrder, APSSlot, APSWorkstation, schedule_fifo
from packages.shared.auth import CurrentUser
from packages.shared.contracts.production import WorkOrderStatus
from packages.shared.db import get_session

router = APIRouter(prefix="/aps", tags=["aps"])


# ── Request / Response ──────────────────────────────────────────────────────── #


class WorkstationCreate(BaseModel):
    code: str
    name: str
    workshop_id: UUID
    capacity: int = 1


class WorkstationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    workshop_id: UUID
    capacity: int
    created_at: datetime


class APSRunRequest(BaseModel):
    range_start: datetime
    range_end: datetime
    estimated_hours_per_order: float = 8.0  # 默认每单 8 小时,后续可按工艺路线算


class APSSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    work_order_id: UUID
    workstation_id: UUID
    planned_start: datetime
    planned_end: datetime


class APSRunResponse(BaseModel):
    total_orders: int
    total_workstations: int
    slots: list[APSSlotOut]


# ── Workstation CRUD ────────────────────────────────────────────────────────── #


@router.post("/workstations", response_model=WorkstationOut, status_code=201)
async def create_workstation(
    body: WorkstationCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Workstation:
    ws = Workstation(
        tenant_id=user.tenant_id,
        code=body.code,
        name=body.name,
        workshop_id=body.workshop_id,
        capacity=body.capacity,
        created_by=user.id,
    )
    session.add(ws)
    await session.flush()
    await session.refresh(ws)
    return ws


@router.get("/workstations", response_model=list[WorkstationOut])
async def list_workstations(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[Workstation]:
    result = await session.execute(
        select(Workstation)
        .where(Workstation.tenant_id == user.tenant_id)
        .order_by(Workstation.code)
    )
    return list(result.scalars().all())


# ── APS Run Endpoint ───────────────────────────────────────────────────────── #


@router.post("/run", response_model=APSRunResponse)
async def run_aps(
    body: APSRunRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APSRunResponse:
    if body.range_end <= body.range_start:
        raise HTTPException(422, "range_end must be after range_start")

    # Fetch released/in_progress work orders (eligible for scheduling)
    wo_result = await session.execute(
        select(WorkOrder).where(
            WorkOrder.tenant_id == user.tenant_id,
            WorkOrder.status.in_([
                WorkOrderStatus.RELEASED.value,
                WorkOrderStatus.IN_PROGRESS.value,
            ]),
        ).order_by(WorkOrder.planned_end.asc())
    )
    work_orders = list(wo_result.scalars().all())

    # Fetch workstations
    ws_result = await session.execute(
        select(Workstation).where(
            Workstation.tenant_id == user.tenant_id,
        ).order_by(Workstation.code)
    )
    workstations = list(ws_result.scalars().all())

    if not workstations:
        raise HTTPException(422, "no workstations configured, cannot schedule")

    orders = [
        APSOrder(
            work_order_id=wo.id,
            planned_end=wo.planned_end,
            estimated_hours=body.estimated_hours_per_order,
        )
        for wo in work_orders
    ]

    ws_list = [
        APSWorkstation(workstation_id=ws.id, capacity=ws.capacity)
        for ws in workstations
    ]

    slots = schedule_fifo(orders, ws_list, body.range_start)

    return APSRunResponse(
        total_orders=len(orders),
        total_workstations=len(workstations),
        slots=[
            APSSlotOut(
                work_order_id=s.work_order_id,
                workstation_id=s.workstation_id,
                planned_start=s.planned_start,
                planned_end=s.planned_end,
            )
            for s in slots
        ],
    )
