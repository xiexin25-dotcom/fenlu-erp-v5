"""
SCM · 物料-供应商映射 (Approved Supplier List)
===============================================

记录每个物料由哪些供应商供应,BOM 反算采购时据此按供应商分组。
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin

SCM_SCHEMA = "scm"


class SupplierProduct(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """物料-供应商关联表 (ASL, Approved Supplier List)。"""

    __tablename__ = "supplier_products"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "supplier_id", "product_id",
            name="uq_sp_tenant_supplier_product",
        ),
        {"schema": SCM_SCHEMA},
    )

    supplier_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.suppliers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, index=True,
    )
    is_preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lead_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    min_order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    uom: Mapped[str] = mapped_column(String(8), nullable=False, default="pcs")
    reference_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")

    supplier: Mapped["Supplier"] = relationship(lazy="selectin")  # noqa: F821


# 避免循环导入,这里用字符串引用 Supplier
from packages.supply_chain.models.supplier import Supplier  # noqa: E402, F401
