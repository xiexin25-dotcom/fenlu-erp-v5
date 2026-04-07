"""
考勤 service · Attendance CRUD + V4 ETL 批量导入
=================================================
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.attendance import Attendance, AttendanceStatus
from packages.management_decision.models.hr import Employee


async def create_attendance(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    work_date: date,
    clock_in: time | None = None,
    clock_out: time | None = None,
    status: str = AttendanceStatus.NORMAL,
    work_hours: Decimal = Decimal("8.00"),
    overtime_hours: Decimal = Decimal("0"),
    memo: str | None = None,
    created_by: UUID | None = None,
) -> Attendance:
    record = Attendance(
        id=uuid4(),
        tenant_id=tenant_id,
        employee_id=employee_id,
        work_date=work_date,
        clock_in=clock_in,
        clock_out=clock_out,
        status=status,
        work_hours=work_hours,
        overtime_hours=overtime_hours,
        memo=memo,
        created_by=created_by,
    )
    session.add(record)
    await session.flush()
    return record


async def list_attendance(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    employee_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Attendance]:
    stmt = (
        select(Attendance)
        .where(Attendance.tenant_id == tenant_id)
        .order_by(Attendance.work_date.desc())
    )
    if employee_id:
        stmt = stmt.where(Attendance.employee_id == employee_id)
    if date_from:
        stmt = stmt.where(Attendance.work_date >= date_from)
    if date_to:
        stmt = stmt.where(Attendance.work_date <= date_to)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_attendance(
    session: AsyncSession, *, tenant_id: UUID, record_id: UUID
) -> Attendance | None:
    stmt = select(Attendance).where(
        Attendance.id == record_id, Attendance.tenant_id == tenant_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# --------------------------------------------------------------------------- #
# V4 ETL 批量导入
# --------------------------------------------------------------------------- #


async def import_attendance_batch(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    rows: list[dict],
    created_by: UUID | None = None,
) -> dict:
    """从 V4 考勤数据批量导入。

    每行用 employee_no 关联,自动跳过工号不存在或日期重复的行。
    返回 {"imported": N, "skipped": N, "errors": [...]}.
    """
    # 预加载员工映射 employee_no -> Employee
    emp_result = await session.execute(
        select(Employee).where(Employee.tenant_id == tenant_id)
    )
    emp_map: dict[str, Employee] = {e.employee_no: e for e in emp_result.scalars().all()}

    # 预加载已有考勤 (employee_id, work_date) 集合
    existing_result = await session.execute(
        select(Attendance.employee_id, Attendance.work_date).where(
            Attendance.tenant_id == tenant_id
        )
    )
    existing_keys: set[tuple[UUID, date]] = {
        (row[0], row[1]) for row in existing_result.all()
    }

    imported = 0
    skipped = 0
    errors: list[str] = []

    for i, row in enumerate(rows):
        emp_no = row["employee_no"]
        work_date = row["work_date"]

        emp = emp_map.get(emp_no)
        if emp is None:
            errors.append(f"行 {i + 1}: 工号 {emp_no} 不存在")
            skipped += 1
            continue

        if (emp.id, work_date) in existing_keys:
            skipped += 1
            continue

        record = Attendance(
            id=uuid4(),
            tenant_id=tenant_id,
            employee_id=emp.id,
            work_date=work_date,
            clock_in=row.get("clock_in"),
            clock_out=row.get("clock_out"),
            status=row.get("status", AttendanceStatus.NORMAL),
            work_hours=Decimal(str(row.get("work_hours", "8.00"))),
            overtime_hours=Decimal(str(row.get("overtime_hours", "0"))),
            memo=row.get("memo"),
            created_by=created_by,
        )
        session.add(record)
        existing_keys.add((emp.id, work_date))
        imported += 1

    if imported > 0:
        await session.flush()

    return {"imported": imported, "skipped": skipped, "errors": errors}


# --------------------------------------------------------------------------- #
# 月度考勤汇总 (供 payroll run 使用)
# --------------------------------------------------------------------------- #


async def get_monthly_attendance_summary(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    period: str,
) -> dict:
    """返回某员工某月考勤汇总。

    Returns: {"work_days": int, "overtime_hours": Decimal, "absent_days": int, "late_days": int}
    """
    year, month = int(period[:4]), int(period[5:7])
    from calendar import monthrange

    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    records = await list_attendance(
        session,
        tenant_id=tenant_id,
        employee_id=employee_id,
        date_from=start,
        date_to=end,
    )

    work_days = 0
    overtime_hours = Decimal("0")
    absent_days = 0
    late_days = 0

    for r in records:
        if r.status in (AttendanceStatus.NORMAL, AttendanceStatus.LATE):
            work_days += 1
            overtime_hours += r.overtime_hours
        if r.status == AttendanceStatus.LATE:
            late_days += 1
        if r.status == AttendanceStatus.ABSENT:
            absent_days += 1

    return {
        "work_days": work_days,
        "overtime_hours": overtime_hours,
        "absent_days": absent_days,
        "late_days": late_days,
    }
