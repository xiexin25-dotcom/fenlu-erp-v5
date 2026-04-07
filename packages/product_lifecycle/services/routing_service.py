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


async def get_routing_by_product(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    product_id: UUID,
    version: str | None = None,
) -> Routing | None:
    """获取产品的 routing,默认取最新。"""
    q = (
        select(Routing)
        .options(selectinload(Routing.operations), selectinload(Routing.product))
        .where(Routing.product_id == product_id, Routing.tenant_id == tenant_id)
    )
    if version:
        q = q.where(Routing.version == version)
    else:
        q = q.order_by(Routing.created_at.desc())
    result = await session.execute(q)
    return result.scalars().first()


async def deep_copy_routing(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    old_version: str,
    new_version: str,
) -> Routing | None:
    """将旧版本的 routing 深拷贝到新版本。"""
    old = await get_routing_by_product(
        session, tenant_id=tenant_id, product_id=product_id, version=old_version,
    )
    if old is None:
        return None

    new_routing = Routing(
        tenant_id=tenant_id,
        product_id=product_id,
        version=new_version,
        description=old.description,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(new_routing)
    await session.flush()

    for old_op in old.operations:
        new_op = RoutingOperation(
            tenant_id=tenant_id,
            routing_id=new_routing.id,
            sequence=old_op.sequence,
            operation_code=old_op.operation_code,
            operation_name=old_op.operation_name,
            workstation_code=old_op.workstation_code,
            standard_minutes=old_op.standard_minutes,
            setup_minutes=old_op.setup_minutes,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(new_op)

    await session.flush()
    return new_routing
