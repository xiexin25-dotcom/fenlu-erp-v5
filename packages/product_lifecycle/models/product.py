"""Product & ProductVersion ORM models.

Product 是产品主数据,ProductVersion 是版本记录。
BOM 版本不可变 — 修改创建新版本 + ECN。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class Product(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """产品主数据。"""

    __tablename__ = "products"
    __table_args__ = {"schema": "plm"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), nullable=False)
    current_version: Mapped[str] = mapped_column(String(32), nullable=False, default="V1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    versions: Mapped[list[ProductVersion]] = relationship(
        "ProductVersion",
        back_populates="product",
        order_by="ProductVersion.version",
        lazy="selectin",
    )


class ProductVersion(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """产品版本记录。每次变更 BOM/工艺后产生新版本。"""

    __tablename__ = "product_versions"
    __table_args__ = {"schema": "plm"}

    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # relationships
    product: Mapped[Product] = relationship("Product", back_populates="versions")
