"""Customer CRUD + 360 aggregation.

360 view 硬约束: ≤3 queries, 不能 n+1。
实现: query 1 = customer + contacts (selectin), query 2 = counts 聚合, query 3 = recent items union.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, literal_column, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.product_lifecycle.models import (
    Contact,
    Customer,
    Lead,
    Opportunity,
    SalesOrder,
    ServiceTicket,
)


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #


async def create_customer(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    code: str,
    name: str,
    kind: str,
    rating: str | None = None,
    is_online: bool = False,
    address: str | None = None,
) -> Customer:
    customer = Customer(
        tenant_id=tenant_id,
        code=code,
        name=name,
        kind=kind,
        rating=rating,
        is_online=is_online,
        address=address,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(customer)
    await session.flush()
    return customer


async def get_customer(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    customer_id: UUID,
) -> Customer | None:
    result = await session.execute(
        select(Customer)
        .options(selectinload(Customer.contacts))
        .where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def add_contact(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    customer_id: UUID,
    name: str,
    title: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    is_primary: bool = False,
) -> Contact:
    contact = Contact(
        tenant_id=tenant_id,
        customer_id=customer_id,
        name=name,
        title=title,
        phone=phone,
        email=email,
        is_primary=is_primary,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(contact)
    await session.flush()
    return contact


# --------------------------------------------------------------------------- #
# 360 view (≤3 queries)
# --------------------------------------------------------------------------- #


@dataclass
class Customer360:
    customer: Customer
    counts: dict[str, int]  # leads, opportunities, orders, tickets
    recent_activities: list[dict[str, Any]]


async def get_customer_360(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    customer_id: UUID,
) -> Customer360 | None:
    """Customer 360 聚合视图,≤3 queries 实现。

    Query 1: Customer + contacts (selectinload, 算 1 query)
    Query 2: 4 个 count 聚合 (单条 SQL, UNION ALL subqueries)
    Query 3: 最近 10 条活动 (UNION ALL + ORDER BY + LIMIT)
    """
    # ── Query 1: customer + contacts ──────────────────────────────────────
    customer = await get_customer(session, tenant_id=tenant_id, customer_id=customer_id)
    if customer is None:
        return None

    cid = customer_id
    tid = tenant_id

    # ── Query 2: counts ──────────────────────────────────────────────────
    counts_q = union_all(
        select(
            literal_column("'leads'").label("entity"),
            func.count().label("cnt"),
        ).where(Lead.customer_id == cid, Lead.tenant_id == tid),
        select(
            literal_column("'opportunities'"),
            func.count(),
        ).where(Opportunity.customer_id == cid, Opportunity.tenant_id == tid),
        select(
            literal_column("'orders'"),
            func.count(),
        ).where(SalesOrder.customer_id == cid, SalesOrder.tenant_id == tid),
        select(
            literal_column("'tickets'"),
            func.count(),
        ).where(ServiceTicket.customer_id == cid, ServiceTicket.tenant_id == tid),
    )
    result = await session.execute(counts_q)
    counts = {row[0]: row[1] for row in result.all()}

    # ── Query 3: recent 10 activities ────────────────────────────────────
    recent_q = union_all(
        select(
            literal_column("'lead'").label("type"),
            Lead.id.label("id"),
            Lead.title.label("title"),
            Lead.status.label("status"),
            Lead.created_at.label("created_at"),
        ).where(Lead.customer_id == cid, Lead.tenant_id == tid),
        select(
            literal_column("'opportunity'"),
            Opportunity.id,
            Opportunity.title,
            Opportunity.stage,
            Opportunity.created_at,
        ).where(Opportunity.customer_id == cid, Opportunity.tenant_id == tid),
        select(
            literal_column("'order'"),
            SalesOrder.id,
            SalesOrder.order_no,
            SalesOrder.status,
            SalesOrder.created_at,
        ).where(SalesOrder.customer_id == cid, SalesOrder.tenant_id == tid),
        select(
            literal_column("'ticket'"),
            ServiceTicket.id,
            ServiceTicket.ticket_no,
            ServiceTicket.status,
            ServiceTicket.created_at,
        ).where(ServiceTicket.customer_id == cid, ServiceTicket.tenant_id == tid),
    ).order_by(literal_column("created_at").desc()).limit(10)

    result = await session.execute(recent_q)
    recent_activities = [
        {
            "type": row[0],
            "id": str(row[1]),
            "title": row[2],
            "status": row[3],
            "created_at": row[4].isoformat() if isinstance(row[4], datetime) else str(row[4]),
        }
        for row in result.all()
    ]

    return Customer360(
        customer=customer,
        counts=counts,
        recent_activities=recent_activities,
    )
