"""JobTicket model · 报工单。

TASK-MFG-004: 车间工人扫码报工,记录完成数/报废数/工时。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class JobTicket(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """报工单 — 每次扫码报工生成一条记录。"""

    __tablename__ = "job_tickets"
    __table_args__ = {"schema": "mfg"}

    work_order_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mfg.work_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_no: Mapped[str] = mapped_column(String(64), nullable=False)

    # 报工数据 (report 之前为 0)
    completed_qty: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, server_default="0"
    )
    scrap_qty: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, server_default="0"
    )
    minutes: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0"
    )

    reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
