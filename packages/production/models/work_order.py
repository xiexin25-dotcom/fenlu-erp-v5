"""WorkOrder model · 生产工单。

TASK-MFG-001: 所有字段对齐 packages.shared.contracts.production.WorkOrderDTO。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class WorkOrder(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """生产工单 — Lane 2 核心实体。"""

    __tablename__ = "work_orders"
    __table_args__ = (
        Index("ix_mfg_wo_order_no", "tenant_id", "order_no", unique=True),
        {"schema": "mfg"},
    )

    order_no: Mapped[str] = mapped_column(String(64), nullable=False)
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    bom_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    routing_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)

    # 数量 — Quantity DTO 拆成 value + uom 两列
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    planned_quantity_uom: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, server_default="0"
    )
    completed_quantity_uom: Mapped[str] = mapped_column(String(16), nullable=False)
    scrap_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, server_default="0"
    )
    scrap_quantity_uom: Mapped[str] = mapped_column(String(16), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")

    planned_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    planned_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sales_order_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
