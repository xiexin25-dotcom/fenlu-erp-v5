"""
应付账款 (AP) / 应收账款 (AR)
==============================

AP 数据最终由 Lane 3 (SCM) 的 PurchaseOrderApprovedEvent 驱动创建,
AR 数据由 Lane 1 (PLM) 的 SalesOrderConfirmedEvent 驱动创建。
TASK-MGMT-002 阶段先通过 REST API 手动创建。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db.base import Base
from packages.shared.db.mixins import AuditMixin, TenantMixin, TimestampMixin, UUIDPKMixin

SCHEMA = "mgmt"


class APStatus(StrEnum):
    """应付/应收状态,与 contracts/management.py 保持一致。"""

    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    WRITTEN_OFF = "written_off"


class APRecord(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """应付账款 — 对应采购订单。"""

    __tablename__ = "ap_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "purchase_order_id", name="uq_ap_records_tenant_po"),
        Index("ix_ap_records_tenant_status", "tenant_id", "status"),
        Index("ix_ap_records_tenant_due", "tenant_id", "due_date"),
        {"schema": SCHEMA},
    )

    purchase_order_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, comment="采购订单 ID (Lane 3)"
    )
    supplier_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, comment="供应商 ID"
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="应付总额"
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="已付金额"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    due_date: Mapped[date] = mapped_column(Date, nullable=False, comment="到期日")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=APStatus.UNPAID, comment="状态"
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    @property
    def balance(self) -> Decimal:
        return self.total_amount - self.paid_amount


class ARRecord(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """应收账款 — 对应销售订单。"""

    __tablename__ = "ar_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sales_order_id", name="uq_ar_records_tenant_so"),
        Index("ix_ar_records_tenant_status", "tenant_id", "status"),
        Index("ix_ar_records_tenant_due", "tenant_id", "due_date"),
        {"schema": SCHEMA},
    )

    sales_order_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, comment="销售订单 ID (Lane 1)"
    )
    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, comment="客户 ID"
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="应收总额"
    )
    received_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="已收金额"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    due_date: Mapped[date] = mapped_column(Date, nullable=False, comment="到期日")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=APStatus.UNPAID, comment="状态"
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    @property
    def balance(self) -> Decimal:
        return self.total_amount - self.received_amount
