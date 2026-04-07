"""
KPI 定义注册表 + 数据点
========================

KPIDefinition: 与 contracts/management.py KPIDefinitionDTO 对齐。
KPIDataPoint:  时序数据,供 BI 看板消费 (TASK-MGMT-009 聚合写入)。
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Date, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db.base import Base
from packages.shared.db.mixins import AuditMixin, TenantMixin, TimestampMixin, UUIDPKMixin

SCHEMA = "mgmt"


class KPIDefinition(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """KPI 元数据注册表。"""

    __tablename__ = "kpi_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_kpi_defs_tenant_code"),
        Index("ix_kpi_defs_category", "tenant_id", "category"),
        {"schema": SCHEMA},
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="KPI 编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="KPI 名称")
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="financial/operations/quality/hr/safety/energy"
    )
    unit: Mapped[str] = mapped_column(String(32), nullable=False, comment="单位")
    source_lane: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="数据来源 lane: plm/mfg/scm/mgmt"
    )
    aggregation: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="聚合方式: sum/avg/max/latest"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class KPIDataPoint(Base, UUIDPKMixin, TenantMixin, TimestampMixin):
    """KPI 时序数据点 — 由 Celery beat 或 event consumer 写入。"""

    __tablename__ = "kpi_data_points"
    __table_args__ = (
        UniqueConstraint("tenant_id", "kpi_code", "period", name="uq_kpi_dp_tenant_code_period"),
        Index("ix_kpi_dp_code_period", "tenant_id", "kpi_code", "period"),
        {"schema": SCHEMA},
    )

    kpi_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="关联 KPI code")
    period: Mapped[date] = mapped_column(Date, nullable=False, comment="数据周期")
    value: Mapped[float] = mapped_column(Float, nullable=False)
    target: Mapped[float | None] = mapped_column(Float, nullable=True, comment="目标值")
