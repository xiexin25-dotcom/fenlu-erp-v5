"""Product & ProductVersion business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.product_lifecycle.models import Product, ProductVersion


def _next_version(current: str) -> str:
    """V1.0 → V2.0, V2.0 → V3.0, etc."""
    try:
        major = int(current.removeprefix("V").split(".")[0])
    except (ValueError, IndexError):
        major = 0
    return f"V{major + 1}.0"


async def create_product(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    code: str,
    name: str,
    category: str,
    uom: str,
    description: str | None = None,
) -> Product:
    product = Product(
        tenant_id=tenant_id,
        code=code,
        name=name,
        category=category,
        uom=uom,
        description=description,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(product)
    await session.flush()

    # 创建初始版本 V1.0
    v1 = ProductVersion(
        tenant_id=tenant_id,
        product_id=product.id,
        version="V1.0",
        is_current=True,
        change_summary="Initial version",
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(v1)
    await session.flush()
    return product


async def list_products(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Product], int]:
    base = select(Product).where(Product.tenant_id == tenant_id)

    # count
    from sqlalchemy import func

    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # items
    items_q = base.order_by(Product.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await session.execute(items_q)
    return list(result.scalars().all()), total


async def get_product(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    product_id: UUID,
) -> Product | None:
    result = await session.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def create_version(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    change_summary: str | None = None,
) -> ProductVersion:
    """创建新版本,将旧版本标记为非当前。

    TASK 要求: 新版本深拷贝上一版本的 BOM — BOM 模型在 TASK-PLM-002 实现,
    此处预留 hook 点,待 BOM 模型就绪后补充深拷贝逻辑。
    """
    product = await get_product(session, tenant_id=tenant_id, product_id=product_id)
    if product is None:
        raise ValueError("product not found")

    new_ver_str = _next_version(product.current_version)

    # 将旧版本标记为非当前
    from sqlalchemy import update

    await session.execute(
        update(ProductVersion)
        .where(
            ProductVersion.product_id == product_id,
            ProductVersion.is_current.is_(True),
        )
        .values(is_current=False)
    )

    # 创建新版本
    new_ver = ProductVersion(
        tenant_id=tenant_id,
        product_id=product_id,
        version=new_ver_str,
        is_current=True,
        change_summary=change_summary,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(new_ver)

    # 更新产品的当前版本号
    product.current_version = new_ver_str
    product.updated_by = user_id

    await session.flush()

    # TODO(TASK-PLM-002): deep-copy BOM from previous version to new version

    return new_ver
