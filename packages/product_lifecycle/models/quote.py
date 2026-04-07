"""Quote & QuoteItem ORM models.

报价单流程: draft → submitted → approved → contracted → ordered
approved 后创建合同(此处简化为 contracted 状态), ordered 后转为 SalesOrder。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    CONTRACTED = "contracted"
    ORDERED = "ordered"
    REJECTED = "rejected"


QUOTE_TRANSITIONS: dict[QuoteStatus, list[QuoteStatus]] = {
    QuoteStatus.DRAFT: [QuoteStatus.SUBMITTED],
    QuoteStatus.SUBMITTED: [QuoteStatus.APPROVED, QuoteStatus.REJECTED],
    QuoteStatus.APPROVED: [QuoteStatus.CONTRACTED],
    QuoteStatus.CONTRACTED: [QuoteStatus.ORDERED],
    QuoteStatus.ORDERED: [],
    QuoteStatus.REJECTED: [QuoteStatus.DRAFT],  # 可以退回修改后重新提交
}


class Quote(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """报价单。"""

    __tablename__ = "quotes"
    __table_args__ = {"schema": "plm"}

    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quote_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=QuoteStatus.DRAFT)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[QuoteItem]] = relationship(
        "QuoteItem", back_populates="quote", cascade="all, delete-orphan", lazy="selectin",
    )


class QuoteItem(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """报价单行项。"""

    __tablename__ = "quote_items"
    __table_args__ = {"schema": "plm"}

    quote_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")

    quote: Mapped[Quote] = relationship("Quote", back_populates="items")
