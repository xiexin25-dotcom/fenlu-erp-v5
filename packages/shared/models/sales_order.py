"""销售订单 — 独立模型,关联客户+产品+财务。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db.base import Base
from packages.shared.db.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"           # 未付款
    PARTIAL = "partial"         # 部分付款
    PAID = "paid"               # 已付清


class ShipmentStatus(StrEnum):
    UNSHIPPED = "unshipped"     # 未发货
    PARTIAL = "partial"         # 部分发货
    SHIPPED = "shipped"         # 已全部发货
    DELIVERED = "delivered"     # 已签收


class OrderStatus(StrEnum):
    DRAFT = "draft"             # 草稿
    CONFIRMED = "confirmed"     # 已确认
    IN_PROGRESS = "in_progress" # 执行中
    COMPLETED = "completed"     # 已完成
    CANCELLED = "cancelled"     # 已取消


SCHEMA = "public"


class SalesDoc(Base, UUIDPKMixin, TenantMixin, TimestampMixin):
    """销售订单主表。"""

    __tablename__ = "sales_orders_v2"
    __table_args__ = (
        UniqueConstraint("tenant_id", "order_no", name="uq_sales_orders_v2_no"),
        Index("ix_sales_orders_v2_customer", "customer_id"),
        Index("ix_sales_orders_v2_status", "order_status"),
        {"schema": SCHEMA},
    )

    order_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="订单编号")
    customer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, comment="客户ID")
    customer_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", comment="客户名称(冗余)")

    order_status: Mapped[str] = mapped_column(String(20), nullable=False, default=OrderStatus.DRAFT, comment="订单状态")
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default=PaymentStatus.UNPAID, comment="付款状态")
    shipment_status: Mapped[str] = mapped_column(String(20), nullable=False, default=ShipmentStatus.UNSHIPPED, comment="发货状态")

    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"), comment="订单总额")
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"), comment="已收款金额")
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"), comment="应收余额")

    order_date: Mapped[date] = mapped_column(Date, nullable=False, comment="订单日期")
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="要求交货日期")
    shipped_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="实际发货日期")

    salesperson: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="销售员")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True, comment="创建人")

    items: Mapped[list[SalesDocItem]] = relationship("SalesDocItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin")


class SalesDocItem(Base):
    """销售订单明细行。"""

    __tablename__ = "sales_order_items_v2"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey(f"{SCHEMA}.sales_orders_v2.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    product_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", comment="产品名称(冗余)")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, comment="行金额")
    shipped_qty: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"), comment="已发货数量")
    uom: Mapped[str] = mapped_column(String(16), nullable=False, default="pcs")

    order: Mapped[SalesDoc] = relationship("SalesDoc", back_populates="items")
