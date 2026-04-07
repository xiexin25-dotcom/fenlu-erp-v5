"""CRM pipeline models: Lead, Opportunity, SalesOrder, ServiceTicket.

Lead 状态: new → contacted → qualified → converted / disqualified
Opportunity 阶段: qualification → proposal → negotiation → closed_won / closed_lost
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


# --------------------------------------------------------------------------- #
# Lead
# --------------------------------------------------------------------------- #


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    DISQUALIFIED = "disqualified"


LEAD_TRANSITIONS: dict[LeadStatus, list[LeadStatus]] = {
    LeadStatus.NEW: [LeadStatus.CONTACTED, LeadStatus.DISQUALIFIED],
    LeadStatus.CONTACTED: [LeadStatus.QUALIFIED, LeadStatus.DISQUALIFIED],
    LeadStatus.QUALIFIED: [LeadStatus.CONVERTED, LeadStatus.DISQUALIFIED],
    LeadStatus.CONVERTED: [],
    LeadStatus.DISQUALIFIED: [],
}


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
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=LeadStatus.NEW)


# --------------------------------------------------------------------------- #
# Opportunity
# --------------------------------------------------------------------------- #


class OpportunityStage(StrEnum):
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


OPPORTUNITY_TRANSITIONS: dict[OpportunityStage, list[OpportunityStage]] = {
    OpportunityStage.QUALIFICATION: [OpportunityStage.PROPOSAL, OpportunityStage.CLOSED_LOST],
    OpportunityStage.PROPOSAL: [OpportunityStage.NEGOTIATION, OpportunityStage.CLOSED_LOST],
    OpportunityStage.NEGOTIATION: [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST],
    OpportunityStage.CLOSED_WON: [],
    OpportunityStage.CLOSED_LOST: [],
}


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
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default=OpportunityStage.QUALIFICATION)
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    expected_close: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SalesOrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


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
    quote_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=SalesOrderStatus.DRAFT)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    promised_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    lines: Mapped[list[SalesOrderLine]] = relationship(
        "SalesOrderLine", back_populates="order", cascade="all, delete-orphan", lazy="selectin",
    )


class SalesOrderLine(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """销售订单行项,匹配 SalesOrderLineDTO。"""

    __tablename__ = "sales_order_lines"
    __table_args__ = {"schema": "plm"}

    order_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")

    order: Mapped[SalesOrder] = relationship("SalesOrder", back_populates="lines")


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
