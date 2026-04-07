"""Customer & Contact ORM models.

Customer 匹配 CustomerSummary 契约。Contact 是联系人。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class Customer(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """客户主数据。"""

    __tablename__ = "customers"
    __table_args__ = {"schema": "plm"}

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # b2b / b2c
    rating: Mapped[str | None] = mapped_column(String(8), nullable=True)  # A/B/C/D
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    contacts: Mapped[list[Contact]] = relationship(
        "Contact", back_populates="customer", cascade="all, delete-orphan", lazy="selectin",
    )


class Contact(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """客户联系人。"""

    __tablename__ = "contacts"
    __table_args__ = {"schema": "plm"}

    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    customer: Mapped[Customer] = relationship("Customer", back_populates="contacts")
