"""CRM pipeline models: Lead, Opportunity, SalesOrder, ServiceTicket.

TASK-PLM-006 需要这些模型用于 Customer 360 聚合。
各模型会在后续 TASK-PLM-007/008/009 中补充完整逻辑。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class Lead(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """销售线索。"""

    __tablename__ = "leads"
    __table_args__ = {"schema": "plm"}

    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")


class Opportunity(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """商机。"""

    __tablename__ = "opportunities"
    __table_args__ = {"schema": "plm"}

    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="qualification")
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    expected_close: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SalesOrder(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """销售订单。"""

    __tablename__ = "sales_orders"
    __table_args__ = {"schema": "plm"}

    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    promised_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )


class ServiceTicket(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """售后服务工单。"""

    __tablename__ = "service_tickets"
    __table_args__ = {"schema": "plm"}

    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nps_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
