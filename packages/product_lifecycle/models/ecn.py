"""ECN (Engineering Change Notice) ORM model.

状态机: draft → reviewing → approved → released → effective
生效时自动 version-bump 关联的 BOM/routing。
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class ECNStatus(StrEnum):
    DRAFT = "draft"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    RELEASED = "released"
    EFFECTIVE = "effective"


# 合法状态转换
ECN_TRANSITIONS: dict[ECNStatus, list[ECNStatus]] = {
    ECNStatus.DRAFT: [ECNStatus.REVIEWING],
    ECNStatus.REVIEWING: [ECNStatus.APPROVED, ECNStatus.DRAFT],  # reject → back to draft
    ECNStatus.APPROVED: [ECNStatus.RELEASED],
    ECNStatus.RELEASED: [ECNStatus.EFFECTIVE],
    ECNStatus.EFFECTIVE: [],  # terminal
}


class ECN(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """工程变更通知。"""

    __tablename__ = "ecns"
    __table_args__ = {"schema": "plm"}

    ecn_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ECNStatus.DRAFT)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    product: Mapped["packages.product_lifecycle.models.product.Product"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Product",
        lazy="selectin",
    )
