"""Workstation model · 工位/工作中心。

TASK-MFG-011: APS 排程需要知道工位容量。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class Workstation(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """工位/工作中心 — APS 排程的资源单元。"""

    __tablename__ = "workstations"
    __table_args__ = {"schema": "mfg"}

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workshop_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    capacity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="同时可处理的工单数 (并行度)",
    )
