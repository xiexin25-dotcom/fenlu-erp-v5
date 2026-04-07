"""JobTicket endpoints · TASK-MFG-004。

Routes:
    POST   /mfg/job-tickets                创建报工单
    POST   /mfg/job-tickets/{id}/report     报工 (填入完成数/报废数/工时)
    GET    /mfg/job-tickets?work_order_id=  按工单查
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import JobTicket, WorkOrder
from packages.production.services.event_publisher import (
    EventPublisher,
    RedisEventPublisher,
)
from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Lane, Quantity, UnitOfMeasure
from packages.shared.contracts.events import EventType, WorkOrderCompletedEvent
from packages.shared.db import get_session

router = APIRouter(prefix="/job-tickets", tags=["job-tickets"])

# ── DI for event publisher ──────────────────────────────────────────────────── #

_publisher: EventPublisher | None = None


def get_publisher() -> EventPublisher:
    global _publisher
    if _publisher is None:
        _publisher = RedisEventPublisher()
    return _publisher


def override_publisher(pub: EventPublisher) -> None:
    global _publisher
    _publisher = pub


# ── Request schemas ─────────────────────────────────────────────────────────── #


class JobTicketCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    work_order_id: UUID
    ticket_no: str = Field(..., max_length=64)


class ReportBody(BaseModel):
    completed_qty: Decimal = Field(..., ge=0)
    scrap_qty: Decimal = Field(Decimal(0), ge=0)
    minutes: Decimal = Field(..., ge=0)
    remark: str | None = None


# ── Response schema ─────────────────────────────────────────────────────────── #


class JobTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    work_order_id: UUID
    ticket_no: str
    completed_qty: Decimal
    scrap_qty: Decimal
    minutes: Decimal
    reported_at: datetime | None
    remark: str | None
    created_at: datetime
    updated_at: datetime


# ── Endpoints ───────────────────────────────────────────────────────────────── #


@router.post("", response_model=JobTicketOut, status_code=201)
async def create_job_ticket(
    body: JobTicketCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> JobTicket:
    # Verify work order exists and belongs to tenant
    wo = (
        await session.execute(
            select(WorkOrder).where(
                WorkOrder.id == body.work_order_id,
                WorkOrder.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if wo is None:
        raise HTTPException(404, "work order not found")

    ticket = JobTicket(
        tenant_id=user.tenant_id,
        work_order_id=body.work_order_id,
        ticket_no=body.ticket_no,
        created_by=user.id,
    )
    session.add(ticket)
    await session.flush()
    await session.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/report", response_model=JobTicketOut)
async def report(
    ticket_id: UUID,
    body: ReportBody,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    publisher: EventPublisher = Depends(get_publisher),
) -> JobTicket:
    ticket = (
        await session.execute(
            select(JobTicket).where(
                JobTicket.id == ticket_id,
                JobTicket.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if ticket is None:
        raise HTTPException(404, "job ticket not found")
    if ticket.reported_at is not None:
        raise HTTPException(409, "job ticket already reported")

    # Fill report data
    ticket.completed_qty = body.completed_qty
    ticket.scrap_qty = body.scrap_qty
    ticket.minutes = body.minutes
    ticket.remark = body.remark
    ticket.reported_at = datetime.now(timezone.utc)
    ticket.updated_by = user.id

    # Atomically update work order quantities
    wo = (
        await session.execute(select(WorkOrder).where(WorkOrder.id == ticket.work_order_id))
    ).scalar_one()

    wo.completed_quantity = wo.completed_quantity + body.completed_qty
    wo.scrap_quantity = wo.scrap_quantity + body.scrap_qty

    await session.flush()
    await session.refresh(wo)
    await session.refresh(ticket)

    # Emit event if work order has reached planned quantity
    if wo.completed_quantity >= wo.planned_quantity:
        # Sum total minutes from all reported tickets for this WO
        result = await session.execute(
            select(JobTicket.minutes).where(
                JobTicket.work_order_id == wo.id,
                JobTicket.reported_at.isnot(None),
            )
        )
        total_minutes = float(sum(row[0] for row in result.all()))

        event = WorkOrderCompletedEvent(
            event_id=uuid4(),
            event_type=EventType.WORK_ORDER_COMPLETED,
            source_lane=Lane.PRODUCTION,
            occurred_at=datetime.now(timezone.utc),
            tenant_id=wo.tenant_id,
            actor_id=user.id,
            work_order_id=wo.id,
            product_id=wo.product_id,
            completed_quantity=Quantity(
                value=wo.completed_quantity, uom=UnitOfMeasure(wo.completed_quantity_uom)
            ),
            scrap_quantity=Quantity(
                value=wo.scrap_quantity, uom=UnitOfMeasure(wo.scrap_quantity_uom)
            ),
            actual_minutes=total_minutes,
        )
        await publisher.publish(event)

    return ticket


@router.get("", response_model=list[JobTicketOut])
async def list_job_tickets(
    user: CurrentUser,
    work_order_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[JobTicket]:
    stmt = select(JobTicket).where(JobTicket.tenant_id == user.tenant_id)
    if work_order_id is not None:
        stmt = stmt.where(JobTicket.work_order_id == work_order_id)
    stmt = stmt.order_by(JobTicket.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())
