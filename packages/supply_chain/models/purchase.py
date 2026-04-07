"""
SCM · 采购链模型: PR → RFQ → PO → Receipt
==========================================

状态机:
  PR:  draft → submitted → approved → closed / cancelled
  RFQ: draft → sent → responded → closed / cancelled
  PO:  draft → submitted → approved → closed / cancelled
  Receipt: draft → confirmed → closed

合法转换在 VALID_TRANSITIONS 中声明,service 层强制校验。
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

# --------------------------------------------------------------------------- #
# 状态转换规则
# --------------------------------------------------------------------------- #

VALID_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "purchase_request": {
        "draft": {"submitted", "cancelled"},
        "submitted": {"approved", "rejected", "cancelled"},
        "approved": {"closed", "cancelled"},
        "rejected": {"draft"},
        "cancelled": set(),
        "closed": set(),
    },
    "rfq": {
        "draft": {"sent", "cancelled"},
        "sent": {"responded", "cancelled"},
        "responded": {"closed", "cancelled"},
        "cancelled": set(),
        "closed": set(),
    },
    "purchase_order": {
        "draft": {"submitted", "cancelled"},
        "submitted": {"approved", "rejected", "cancelled"},
        "approved": {"closed", "cancelled"},
        "rejected": {"draft"},
        "cancelled": set(),
        "closed": set(),
    },
    "purchase_receipt": {
        "draft": {"confirmed", "cancelled"},
        "confirmed": {"closed"},
        "cancelled": set(),
        "closed": set(),
    },
}


def validate_transition(doc_type: str, from_status: str, to_status: str) -> None:
    """校验状态转换合法性,不合法则抛 ValueError。"""
    allowed = VALID_TRANSITIONS.get(doc_type, {}).get(from_status, set())
    if to_status not in allowed:
        raise ValueError(
            f"{doc_type}: transition {from_status!r} → {to_status!r} not allowed "
            f"(allowed: {allowed or 'none'})"
        )


# --------------------------------------------------------------------------- #
# 采购申请 (Purchase Request)
# --------------------------------------------------------------------------- #


class PurchaseRequest(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    __tablename__ = "purchase_requests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "request_no", name="uq_pr_tenant_no"),
        Index("ix_pr_tenant_status", "tenant_id", "status"),
        {"schema": SCM_SCHEMA},
    )

    request_no: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    requested_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    needed_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[PurchaseRequestLine]] = relationship(
        back_populates="header", cascade="all, delete-orphan", lazy="selectin",
    )


class PurchaseRequestLine(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "purchase_request_lines"
    __table_args__ = ({"schema": SCM_SCHEMA},)

    request_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.purchase_requests.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(8), nullable=False, default="pcs")
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)

    header: Mapped[PurchaseRequest] = relationship(back_populates="lines")


# --------------------------------------------------------------------------- #
# 询价单 (RFQ)
# --------------------------------------------------------------------------- #


class RFQ(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    __tablename__ = "rfqs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "rfq_no", name="uq_rfq_tenant_no"),
        {"schema": SCM_SCHEMA},
    )

    rfq_no: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    supplier_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.suppliers.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    request_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.purchase_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[RFQLine]] = relationship(
        back_populates="header", cascade="all, delete-orphan", lazy="selectin",
    )


class RFQLine(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "rfq_lines"
    __table_args__ = ({"schema": SCM_SCHEMA},)

    rfq_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.rfqs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(8), nullable=False, default="pcs")
    quoted_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")

    header: Mapped[RFQ] = relationship(back_populates="lines")


# --------------------------------------------------------------------------- #
# 采购订单 (Purchase Order)
# --------------------------------------------------------------------------- #


class PurchaseOrder(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "order_no", name="uq_po_tenant_no"),
        Index("ix_po_tenant_status", "tenant_id", "status"),
        Index("ix_po_tenant_supplier", "tenant_id", "supplier_id"),
        {"schema": SCM_SCHEMA},
    )

    order_no: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    supplier_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rfq_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.rfqs.id", ondelete="SET NULL"),
        nullable=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    expected_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[PurchaseOrderLine]] = relationship(
        back_populates="header", cascade="all, delete-orphan", lazy="selectin",
    )


class PurchaseOrderLine(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "purchase_order_lines"
    __table_args__ = ({"schema": SCM_SCHEMA},)

    order_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.purchase_orders.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(8), nullable=False, default="pcs")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)

    header: Mapped[PurchaseOrder] = relationship(back_populates="lines")


# --------------------------------------------------------------------------- #
# 收货单 (Purchase Receipt)
# --------------------------------------------------------------------------- #


class PurchaseReceipt(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    __tablename__ = "purchase_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "receipt_no", name="uq_receipt_tenant_no"),
        {"schema": SCM_SCHEMA},
    )

    receipt_no: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    order_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.purchase_orders.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    supplier_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[PurchaseReceiptLine]] = relationship(
        back_populates="header", cascade="all, delete-orphan", lazy="selectin",
    )


class PurchaseReceiptLine(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "purchase_receipt_lines"
    __table_args__ = ({"schema": SCM_SCHEMA},)

    receipt_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.purchase_receipts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    rejected_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    uom: Mapped[str] = mapped_column(String(8), nullable=False, default="pcs")
    batch_no: Mapped[str | None] = mapped_column(String(32), nullable=True)

    header: Mapped[PurchaseReceipt] = relationship(back_populates="lines")
