"""Routing & RoutingOperation ORM models.

工艺路线绑定 product_id + version。Lane 2 APS 通过 GET /plm/routing/{id} 拉取。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class Routing(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """工艺路线头。"""

    __tablename__ = "routings"
    __table_args__ = {"schema": "plm"}

    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    operations: Mapped[list[RoutingOperation]] = relationship(
        "RoutingOperation",
        back_populates="routing",
        cascade="all, delete-orphan",
        order_by="RoutingOperation.sequence",
        lazy="selectin",
    )
    product: Mapped["packages.product_lifecycle.models.product.Product"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Product",
        lazy="selectin",
    )


class RoutingOperation(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """工艺路线工序。"""

    __tablename__ = "routing_operations"
    __table_args__ = {"schema": "plm"}

    routing_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.routings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_name: Mapped[str] = mapped_column(String(200), nullable=False)
    workstation_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    standard_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    setup_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # relationships
    routing: Mapped[Routing] = relationship("Routing", back_populates="operations")
