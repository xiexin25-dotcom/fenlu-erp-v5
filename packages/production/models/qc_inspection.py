"""QCInspection model · 质量检验。

TASK-MFG-005: 字段对齐 packages.shared.contracts.production.QCInspectionDTO。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class QCInspection(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """质量检验记录 — IQC/IPQC/OQC/FAI。"""

    __tablename__ = "qc_inspections"
    __table_args__ = {"schema": "mfg"}

    inspection_no: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # InspectionType
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    work_order_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True, index=True
    )
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    defect_count: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)  # InspectionResult
    inspector_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
