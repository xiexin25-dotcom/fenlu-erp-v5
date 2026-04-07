"""EAM models · 设备管理。

TASK-MFG-007: Equipment, MaintenancePlan, MaintenanceLog, FaultRecord。
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class Equipment(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """设备台账。"""

    __tablename__ = "equipment"
    __table_args__ = {"schema": "mfg"}

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workshop_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="idle")
    is_special_equipment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MaintenancePlan(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """预防性维保计划 — 按间隔天数自动生成维保工单。"""

    __tablename__ = "maintenance_plans"
    __table_args__ = {"schema": "mfg"}

    equipment_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mfg.equipment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    last_generated: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MaintenanceLog(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """维保执行记录。"""

    __tablename__ = "maintenance_logs"
    __table_args__ = {"schema": "mfg"}

    equipment_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mfg.equipment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mfg.maintenance_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    performed_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)


class FaultRecord(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """设备故障记录 — OEE 可用率计算的输入。"""

    __tablename__ = "fault_records"
    __table_args__ = {"schema": "mfg"}

    equipment_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mfg.equipment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fault_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # minor/major/critical
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
