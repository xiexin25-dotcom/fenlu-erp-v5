"""
SCM · 盘点模型 (Stocktake)
==========================

流程:
  1. 创建盘点单 (draft)
  2. 录入盘点行 (system_quantity 自动从 Inventory 快照, actual_quantity 人工填)
  3. 确认 (draft → confirmed): 计算 variance, 自动创建 adjustment StockMove
  4. 关闭 (confirmed → closed)

状态: draft → confirmed → closed / cancelled
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin

SCM_SCHEMA = "scm"

STOCKTAKE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"confirmed", "cancelled"},
    "confirmed": {"closed"},
    "cancelled": set(),
    "closed": set(),
}


def validate_stocktake_transition(from_status: str, to_status: str) -> None:
    allowed = STOCKTAKE_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValueError(
            f"Stocktake transition {from_status!r} → {to_status!r} not allowed "
            f"(allowed: {allowed or 'none'})"
        )


class Stocktake(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """盘点单表头。"""

    __tablename__ = "stocktakes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "stocktake_no", name="uq_st_tenant_no"),
        Index("ix_st_tenant_status", "tenant_id", "status"),
        {"schema": SCM_SCHEMA},
    )

    stocktake_no: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    warehouse_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    stocktake_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[StocktakeLine]] = relationship(
        back_populates="header", cascade="all, delete-orphan", lazy="selectin",
    )


class StocktakeLine(Base, UUIDPKMixin, TimestampMixin):
    """盘点行: 每行一个 product+batch 的实盘记录。"""

    __tablename__ = "stocktake_lines"
    __table_args__ = (
        UniqueConstraint(
            "stocktake_id", "product_id", "batch_no",
            name="uq_stl_stocktake_prod_batch",
        ),
        {"schema": SCM_SCHEMA},
    )

    stocktake_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.stocktakes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    batch_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    uom: Mapped[str] = mapped_column(String(8), nullable=False, default="pcs")

    system_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    actual_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    variance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)

    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)

    header: Mapped[Stocktake] = relationship(back_populates="lines")
