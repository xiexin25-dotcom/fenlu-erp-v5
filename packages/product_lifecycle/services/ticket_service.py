"""ServiceTicket business logic: SLA timer, status transitions, close with NPS."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.product_lifecycle.models import Customer, ServiceTicket


# --------------------------------------------------------------------------- #
# Status machine (matches ServiceTicketStatus contract)
# --------------------------------------------------------------------------- #


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


TICKET_TRANSITIONS: dict[TicketStatus, list[TicketStatus]] = {
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS, TicketStatus.CLOSED],
    TicketStatus.IN_PROGRESS: [TicketStatus.PENDING_CUSTOMER, TicketStatus.RESOLVED],
    TicketStatus.PENDING_CUSTOMER: [TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.IN_PROGRESS],  # reopen
    TicketStatus.CLOSED: [],  # terminal
}


class InvalidTicketTransitionError(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"invalid ticket transition: {current} → {target}")


# --------------------------------------------------------------------------- #
# SLA timer: A=4h, B=8h, C=24h, default=24h
# --------------------------------------------------------------------------- #

SLA_HOURS: dict[str, int] = {
    "A": 4,
    "B": 8,
    "C": 24,
    "D": 48,
}


def calculate_sla_due(rating: str | None) -> datetime:
    """基于客户评级计算 SLA 到期时间。"""
    hours = SLA_HOURS.get(rating or "", 24)
    return datetime.now(timezone.utc) + timedelta(hours=hours)


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #


async def create_ticket(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    customer_id: UUID,
    ticket_no: str,
    product_id: UUID | None = None,
    description: str | None = None,
) -> ServiceTicket:
    # 查 customer 获取 rating 以计算 SLA
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise ValueError("customer not found")

    sla_due = calculate_sla_due(customer.rating)

    ticket = ServiceTicket(
        tenant_id=tenant_id,
        customer_id=customer_id,
        ticket_no=ticket_no,
        product_id=product_id,
        description=description,
        status=TicketStatus.OPEN,
        sla_due_at=sla_due,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(ticket)
    await session.flush()
    return ticket


async def get_ticket(
    session: AsyncSession, *, tenant_id: UUID, ticket_id: UUID,
) -> ServiceTicket | None:
    result = await session.execute(
        select(ServiceTicket).where(
            ServiceTicket.id == ticket_id, ServiceTicket.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def transition_ticket(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    ticket_id: UUID,
    target_status: str,
) -> ServiceTicket:
    ticket = await get_ticket(session, tenant_id=tenant_id, ticket_id=ticket_id)
    if ticket is None:
        raise ValueError("ticket not found")

    current = TicketStatus(ticket.status)
    target = TicketStatus(target_status)
    if target not in TICKET_TRANSITIONS.get(current, []):
        raise InvalidTicketTransitionError(ticket.status, target_status)

    ticket.status = target.value
    ticket.updated_by = user_id
    await session.flush()
    return ticket


async def close_ticket(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    ticket_id: UUID,
    nps_score: int,
) -> ServiceTicket:
    """关闭工单,必须提供 NPS score (0-10)。

    可以从 open / resolved 关闭。
    """
    if not (0 <= nps_score <= 10):
        raise ValueError("nps_score must be between 0 and 10")

    ticket = await get_ticket(session, tenant_id=tenant_id, ticket_id=ticket_id)
    if ticket is None:
        raise ValueError("ticket not found")

    current = TicketStatus(ticket.status)
    if TicketStatus.CLOSED not in TICKET_TRANSITIONS.get(current, []):
        raise InvalidTicketTransitionError(ticket.status, "closed")

    ticket.status = TicketStatus.CLOSED
    ticket.nps_score = nps_score
    ticket.updated_by = user_id
    await session.flush()
    return ticket
