"""ECN business logic: state machine + auto version-bump on effective."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.product_lifecycle.models import ECN, ECNStatus, ECN_TRANSITIONS, Product


class InvalidTransitionError(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"invalid transition: {current} → {target}")


async def create_ecn(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    ecn_no: str,
    title: str,
    reason: str | None = None,
    description: str | None = None,
) -> ECN:
    # 确认 product 存在
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if result.scalar_one_or_none() is None:
        raise ValueError("product not found")

    ecn = ECN(
        tenant_id=tenant_id,
        product_id=product_id,
        ecn_no=ecn_no,
        title=title,
        reason=reason,
        description=description,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(ecn)
    await session.flush()
    return ecn


async def list_ecns(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[ECN]:
    result = await session.execute(
        select(ECN)
        .options(selectinload(ECN.product))
        .where(ECN.tenant_id == tenant_id)
        .order_by(ECN.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_ecn(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    ecn_id: UUID,
) -> ECN | None:
    result = await session.execute(
        select(ECN)
        .options(selectinload(ECN.product))
        .where(ECN.id == ecn_id, ECN.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def transition_ecn(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    ecn_id: UUID,
    target_status: str,
) -> ECN:
    """推进 ECN 状态。到 effective 时自动 version-bump BOM/routing。"""
    ecn = await get_ecn(session, tenant_id=tenant_id, ecn_id=ecn_id)
    if ecn is None:
        raise ValueError("ECN not found")

    current = ECNStatus(ecn.status)
    target = ECNStatus(target_status)
    allowed = ECN_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidTransitionError(ecn.status, target_status)

    ecn.status = target.value
    ecn.updated_by = user_id

    # effective → auto version-bump
    if target == ECNStatus.EFFECTIVE:
        await _apply_ecn(session, ecn=ecn, user_id=user_id)

    await session.flush()

    # re-fetch to pick up server-side updated_at
    refreshed = await get_ecn(session, tenant_id=tenant_id, ecn_id=ecn_id)
    assert refreshed is not None
    return refreshed


async def _apply_ecn(
    session: AsyncSession,
    *,
    ecn: ECN,
    user_id: UUID,
) -> None:
    """ECN 生效: 对关联产品进行 version-bump (深拷贝 BOM + routing)。"""
    from packages.product_lifecycle.services.product_service import create_version

    await create_version(
        session,
        tenant_id=ecn.tenant_id,
        user_id=user_id,
        product_id=ecn.product_id,
        change_summary=f"ECN {ecn.ecn_no}: {ecn.title}",
    )
