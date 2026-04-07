"""
SCM · 供应商 + 供应商评分模型
=============================

对应 V5 contract: SupplierSummary, SupplierTier
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin

SCM_SCHEMA = "scm"


class Supplier(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """供应商主表。"""

    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_supplier_tenant_code"),
        Index("ix_supplier_tenant_tier", "tenant_id", "tier"),
        {"schema": SCM_SCHEMA},
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    tier: Mapped[str] = mapped_column(
        String(16), nullable=False, default="approved",
    )
    rating_score: Mapped[float] = mapped_column(
        Float, CheckConstraint("rating_score >= 0 AND rating_score <= 100"), nullable=False, default=0.0,
    )
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 扩展信息
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 关联
    ratings: Mapped[list[SupplierRating]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan", lazy="selectin",
    )
    tier_changes: Mapped[list[SupplierTierChange]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan", lazy="selectin",
    )


class SupplierRating(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """供应商评分记录 (按周期)。"""

    __tablename__ = "supplier_ratings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "supplier_id", "period_start",
            name="uq_rating_tenant_supplier_period",
        ),
        {"schema": SCM_SCHEMA},
    )

    supplier_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    delivery_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    price_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    service_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_score: Mapped[float] = mapped_column(
        Float, CheckConstraint("total_score >= 0 AND total_score <= 100"), nullable=False, default=0.0,
    )

    supplier: Mapped[Supplier] = relationship(back_populates="ratings")


class SupplierTierChange(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """供应商等级变更记录 (需审批)。"""

    __tablename__ = "supplier_tier_changes"
    __table_args__ = (
        {"schema": SCM_SCHEMA},
    )

    supplier_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    to_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 审批状态: pending / approved / rejected
    approval_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approval_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True,
        comment="Lane 4 审批单 ID",
    )

    supplier: Mapped[Supplier] = relationship(back_populates="tier_changes")
