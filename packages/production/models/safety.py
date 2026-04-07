"""Safety models · 安全生产。

TASK-MFG-009: SafetyHazard + HazardAuditLog。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class SafetyHazard(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """安全隐患 — 状态机: reported → assigned → rectifying → verified → closed。"""

    __tablename__ = "safety_hazards"
    __table_args__ = {"schema": "mfg"}

    hazard_no: Mapped[str] = mapped_column(String(64), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)  # HazardLevel
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="reported")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    rectified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HazardAuditLog(UUIDPKMixin, TenantMixin, TimestampMixin, Base):
    """隐患状态流转审计日志 — 每次 transition 写一行。"""

    __tablename__ = "hazard_audit_logs"
    __table_args__ = {"schema": "mfg"}

    hazard_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mfg.safety_hazards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str] = mapped_column(String(16), nullable=False)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    transitioned_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
