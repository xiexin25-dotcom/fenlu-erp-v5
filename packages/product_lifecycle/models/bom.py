"""BOM & BOMItem ORM models.

BOM 绑定到 Product + version 字符串。BOM 版本不可变,修改需通过 ECN 产生新版本。
BOMItem.component_id 指向 Product (自引用),构成多级 BOM 树。
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class BOM(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """物料清单头。每个 product+version 对应一份 BOM。"""

    __tablename__ = "boms"
    __table_args__ = {"schema": "plm"}

    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    items: Mapped[list[BOMItem]] = relationship(
        "BOMItem",
        back_populates="bom",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    product: Mapped["packages.product_lifecycle.models.product.Product"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Product",
        lazy="selectin",
    )


class BOMItem(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """BOM 行项。component_id → Product 构成自引用树。"""

    __tablename__ = "bom_items"
    __table_args__ = {"schema": "plm"}

    bom_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.boms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False,
    )
    uom: Mapped[str] = mapped_column(String(16), nullable=False)
    scrap_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0"),
    )
    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True,
    )
    is_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # relationships
    bom: Mapped[BOM] = relationship("BOM", back_populates="items")
    component: Mapped["packages.product_lifecycle.models.product.Product"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Product",
        foreign_keys=[component_id],
        lazy="selectin",
    )
