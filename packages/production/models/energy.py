"""Energy models · 能耗管理。

TASK-MFG-010: EnergyMeter + EnergyReading。
EnergyReading 在 PostgreSQL 中用 TimescaleDB hypertable;
测试用 SQLite 时为普通表(迁移脚本中 CREATE 后调用 create_hypertable)。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class EnergyMeter(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """能源计量表具。"""

    __tablename__ = "energy_meters"
    __table_args__ = {"schema": "mfg"}

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    energy_type: Mapped[str] = mapped_column(String(20), nullable=False)  # EnergyType
    uom: Mapped[str] = mapped_column(String(16), nullable=False)  # kWh / m3 / GJ
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)


class EnergyReading(UUIDPKMixin, TenantMixin, TimestampMixin, Base):
    """能源采集读数 — 时序数据,生产环境用 TimescaleDB hypertable。"""

    __tablename__ = "energy_readings"
    __table_args__ = {"schema": "mfg"}

    meter_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("mfg.energy_meters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    energy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reading: Mapped[float] = mapped_column(Float, nullable=False)
    delta: Mapped[float] = mapped_column(Float, nullable=False)  # 本周期消耗量
    uom: Mapped[str] = mapped_column(String(16), nullable=False)
