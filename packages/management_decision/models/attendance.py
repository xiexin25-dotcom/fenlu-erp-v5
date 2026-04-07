"""
考勤 · Attendance
==================

每日每人一条考勤记录,V4 系统打卡数据通过 ETL 批量导入。
与 Payroll 集成: payroll run 时按月汇总出勤天数、加班小时、缺勤天数来计算
overtime_pay 和 deductions。
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db.base import Base
from packages.shared.db.mixins import AuditMixin, TenantMixin, TimestampMixin, UUIDPKMixin

SCHEMA = "mgmt"


class AttendanceStatus(StrEnum):
    NORMAL = "normal"  # 正常
    LATE = "late"  # 迟到
    EARLY_LEAVE = "early_leave"  # 早退
    ABSENT = "absent"  # 缺勤
    LEAVE = "leave"  # 请假
    HOLIDAY = "holiday"  # 休假/节假日


class Attendance(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """每日考勤记录。"""

    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "employee_id", "work_date", name="uq_attendances_tenant_emp_date"
        ),
        Index("ix_attendances_tenant_date", "tenant_id", "work_date"),
        Index("ix_attendances_employee", "employee_id"),
        {"schema": SCHEMA},
    )

    employee_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False, comment="考勤日期")
    clock_in: Mapped[time | None] = mapped_column(Time, nullable=True, comment="上班打卡")
    clock_out: Mapped[time | None] = mapped_column(Time, nullable=True, comment="下班打卡")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AttendanceStatus.NORMAL, comment="出勤状态"
    )
    work_hours: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("8.00"), comment="工作时长"
    )
    overtime_hours: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0"), comment="加班时长"
    )
    memo: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="备注")
