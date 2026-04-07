"""Routing business logic: CRUD for routings and operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.product_lifecycle.models import Routing, RoutingOperation


async def create_routing(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    version: str,
    description: str | None = None,
) -> Routing:
    routing = Routing(
        tenant_id=tenant_id,
        product_id=product_id,
        version=version,
        description=description,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(routing)
    await session.flush()
    return routing


async def get_routing(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    routing_id: UUID,
) -> Routing | None:
    result = await session.execute(
        select(Routing)
        .options(selectinload(Routing.operations), selectinload(Routing.product))
        .where(Routing.id == routing_id, Routing.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def add_operation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    routing_id: UUID,
    sequence: int,
    operation_code: str,
    operation_name: str,
    standard_minutes: float,
    setup_minutes: float = 0.0,
    workstation_code: str | None = None,
) -> RoutingOperation:
    # 确认 routing 存在
    routing = await get_routing(session, tenant_id=tenant_id, routing_id=routing_id)
    if routing is None:
        raise ValueError("routing not found")

    op = RoutingOperation(
        tenant_id=tenant_id,
        routing_id=routing_id,
        sequence=sequence,
        operation_code=operation_code,
        operation_name=operation_name,
        standard_minutes=standard_minutes,
        setup_minutes=setup_minutes,
        workstation_code=workstation_code,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(op)
    await session.flush()
    return op
