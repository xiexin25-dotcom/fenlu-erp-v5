"""BOM business logic: CRUD, cycle detection, cost rollup, deep-copy."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.product_lifecycle.models import BOM, BOMItem, Product


# --------------------------------------------------------------------------- #
# Cycle detection
# --------------------------------------------------------------------------- #


class CycleDetectedError(Exception):
    """Raised when adding a BOM item would create a circular dependency."""

    def __init__(self, path: list[UUID]) -> None:
        self.path = path
        codes = " → ".join(str(p) for p in path)
        super().__init__(f"BOM cycle detected: {codes}")


async def _collect_child_product_ids(
    session: AsyncSession,
    product_id: UUID,
    tenant_id: UUID,
) -> set[UUID]:
    """递归收集某产品下所有子组件的 product_id (通过该产品当前版本的 BOM)。"""
    visited: set[UUID] = set()
    stack = [product_id]
    while stack:
        pid = stack.pop()
        if pid in visited:
            continue
        visited.add(pid)
        # 找该产品的 BOM
        result = await session.execute(
            select(BOMItem.component_id)
            .join(BOM, BOMItem.bom_id == BOM.id)
            .where(BOM.product_id == pid, BOM.tenant_id == tenant_id)
        )
        for (cid,) in result.all():
            if cid not in visited:
                stack.append(cid)
    return visited


async def check_cycle(
    session: AsyncSession,
    *,
    bom_product_id: UUID,
    component_id: UUID,
    tenant_id: UUID,
) -> None:
    """检查将 component_id 加入 bom_product_id 的 BOM 是否会产生环。

    逻辑: component 不能是 bom_product_id 自身,
    且 component 的子树中不能包含 bom_product_id。
    """
    if component_id == bom_product_id:
        raise CycleDetectedError([bom_product_id, component_id])

    # 收集 component 的所有下级产品
    descendants = await _collect_child_product_ids(session, component_id, tenant_id)
    if bom_product_id in descendants:
        raise CycleDetectedError([bom_product_id, component_id, bom_product_id])


# --------------------------------------------------------------------------- #
# Cost rollup
# --------------------------------------------------------------------------- #


async def rollup_cost(
    session: AsyncSession,
    bom: BOM,
) -> Decimal | None:
    """递归汇总 BOM 成本。

    叶子节点成本 = quantity * (1 + scrap_rate) * unit_cost
    中间节点成本 = 子 BOM rollup 结果 * quantity * (1 + scrap_rate)
    返回 None 若任一叶子缺 unit_cost 且无子 BOM。
    """
    total = Decimal("0")
    has_cost = False
    for item in bom.items:
        qty_with_scrap = item.quantity * (1 + item.scrap_rate)
        # 尝试找 component 的子 BOM
        child_bom = await get_bom_by_product(
            session,
            tenant_id=bom.tenant_id,
            product_id=item.component_id,
        )
        if child_bom and child_bom.items:
            child_cost = await rollup_cost(session, child_bom)
            if child_cost is not None:
                total += qty_with_scrap * child_cost
                has_cost = True
                continue
        # 叶子: 用 unit_cost
        if item.unit_cost is not None:
            total += qty_with_scrap * item.unit_cost
            has_cost = True
    return total if has_cost else None


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #


async def create_bom(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    version: str,
    description: str | None = None,
) -> BOM:
    bom = BOM(
        tenant_id=tenant_id,
        product_id=product_id,
        version=version,
        description=description,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(bom)
    await session.flush()
    return bom


async def get_bom(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    bom_id: UUID,
) -> BOM | None:
    result = await session.execute(
        select(BOM)
        .options(selectinload(BOM.items).selectinload(BOMItem.component), selectinload(BOM.product))
        .where(BOM.id == bom_id, BOM.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_bom_by_product(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    product_id: UUID,
    version: str | None = None,
) -> BOM | None:
    """获取产品的 BOM,默认取最新版本(按 current_version)。"""
    q = select(BOM).options(
        selectinload(BOM.items).selectinload(BOMItem.component),
        selectinload(BOM.product),
    ).where(BOM.product_id == product_id, BOM.tenant_id == tenant_id)
    if version:
        q = q.where(BOM.version == version)
    else:
        # 取最新: 按 created_at desc
        q = q.order_by(BOM.created_at.desc())
    result = await session.execute(q)
    return result.scalars().first()


async def add_bom_item(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    bom_id: UUID,
    component_id: UUID,
    quantity: Decimal,
    uom: str,
    scrap_rate: Decimal = Decimal("0"),
    unit_cost: Decimal | None = None,
    is_optional: bool = False,
    remark: str | None = None,
) -> BOMItem:
    # 先拿 BOM 头确认存在
    bom = await get_bom(session, tenant_id=tenant_id, bom_id=bom_id)
    if bom is None:
        raise ValueError("BOM not found")

    # 确认 component 存在
    comp = await session.execute(
        select(Product).where(Product.id == component_id, Product.tenant_id == tenant_id)
    )
    if comp.scalar_one_or_none() is None:
        raise ValueError("component product not found")

    # cycle check
    await check_cycle(
        session,
        bom_product_id=bom.product_id,
        component_id=component_id,
        tenant_id=tenant_id,
    )

    item = BOMItem(
        tenant_id=tenant_id,
        bom_id=bom_id,
        component_id=component_id,
        quantity=quantity,
        uom=uom,
        scrap_rate=scrap_rate,
        unit_cost=unit_cost,
        is_optional=is_optional,
        remark=remark,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(item)
    await session.flush()
    return item


# --------------------------------------------------------------------------- #
# Deep-copy BOM for version bump
# --------------------------------------------------------------------------- #


async def deep_copy_bom(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    old_version: str,
    new_version: str,
) -> BOM | None:
    """将旧版本的 BOM 深拷贝到新版本。返回新 BOM,若旧版本无 BOM 则返回 None。"""
    old_bom = await get_bom_by_product(
        session, tenant_id=tenant_id, product_id=product_id, version=old_version,
    )
    if old_bom is None:
        return None

    new_bom = BOM(
        tenant_id=tenant_id,
        product_id=product_id,
        version=new_version,
        status=old_bom.status,
        description=old_bom.description,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(new_bom)
    await session.flush()

    for old_item in old_bom.items:
        new_item = BOMItem(
            tenant_id=tenant_id,
            bom_id=new_bom.id,
            component_id=old_item.component_id,
            quantity=old_item.quantity,
            uom=old_item.uom,
            scrap_rate=old_item.scrap_rate,
            unit_cost=old_item.unit_cost,
            is_optional=old_item.is_optional,
            remark=old_item.remark,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(new_item)

    await session.flush()
    return new_bom
