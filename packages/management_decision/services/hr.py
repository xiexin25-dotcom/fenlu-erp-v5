"""
HR service · 员工 + 薪资
=========================
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.management_decision.models.hr import (
    Employee,
    Payroll,
    PayrollItem,
    PayrollStatus,
)


# --------------------------------------------------------------------------- #
# Employee
# --------------------------------------------------------------------------- #


async def create_employee(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    employee_no: str,
    name: str,
    user_id: UUID | None = None,
    department_id: UUID | None = None,
    position: str = "",
    base_salary: Decimal = Decimal("0"),
    memo: str | None = None,
    created_by: UUID | None = None,
) -> Employee:
    emp = Employee(
        id=uuid4(),
        tenant_id=tenant_id,
        employee_no=employee_no,
        name=name,
        user_id=user_id,
        department_id=department_id,
        position=position,
        base_salary=base_salary,
        memo=memo,
        created_by=created_by,
    )
    session.add(emp)
    await session.flush()
    return emp


async def get_employee(
    session: AsyncSession, *, tenant_id: UUID, employee_id: UUID
) -> Employee | None:
    stmt = select(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_employees(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    active_only: bool = True,
) -> list[Employee]:
    stmt = (
        select(Employee)
        .where(Employee.tenant_id == tenant_id)
        .order_by(Employee.employee_no)
    )
    if active_only:
        stmt = stmt.where(Employee.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_employee(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    name: str | None = None,
    department_id: UUID | None = None,
    position: str | None = None,
    base_salary: Decimal | None = None,
    is_active: bool | None = None,
    memo: str | None = None,
    updated_by: UUID | None = None,
) -> Employee | None:
    emp = await get_employee(session, tenant_id=tenant_id, employee_id=employee_id)
    if emp is None:
        return None
    if name is not None:
        emp.name = name
    if department_id is not None:
        emp.department_id = department_id
    if position is not None:
        emp.position = position
    if base_salary is not None:
        emp.base_salary = base_salary
    if is_active is not None:
        emp.is_active = is_active
    if memo is not None:
        emp.memo = memo
    if updated_by is not None:
        emp.updated_by = updated_by
    await session.flush()
    return emp


# --------------------------------------------------------------------------- #
# Payroll
# --------------------------------------------------------------------------- #


async def run_payroll(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    period: str,
    created_by: UUID | None = None,
) -> Payroll:
    """生成月度工资批次,为每个在职员工创建 PayrollItem。

    如果该 period 已存在则抛出 ValueError。
    """
    # 检查是否已存在
    existing = await session.execute(
        select(Payroll).where(Payroll.tenant_id == tenant_id, Payroll.period == period)
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"薪资批次 {period} 已存在,不可重复生成")

    # 查询在职员工
    employees = await list_employees(session, tenant_id=tenant_id, active_only=True)
    if not employees:
        raise ValueError("没有在职员工,无法生成工资")

    payroll = Payroll(
        id=uuid4(),
        tenant_id=tenant_id,
        period=period,
        status=PayrollStatus.DRAFT,
        head_count=len(employees),
        memo=None,
        created_by=created_by,
    )

    from packages.management_decision.services.attendance import (
        get_monthly_attendance_summary,
    )

    # 薪资参数: 加班费 = base / 21.75 / 8 * 1.5 * overtime_hours
    # 缺勤扣除 = base / 21.75 * absent_days
    MONTHLY_WORK_DAYS = Decimal("21.75")
    OVERTIME_RATE = Decimal("1.5")
    DAILY_HOURS = Decimal("8")

    total = Decimal("0")
    for emp in employees:
        summary = await get_monthly_attendance_summary(
            session, tenant_id=tenant_id, employee_id=emp.id, period=period
        )
        hourly_rate = emp.base_salary / MONTHLY_WORK_DAYS / DAILY_HOURS
        overtime_pay = (hourly_rate * OVERTIME_RATE * summary["overtime_hours"]).quantize(
            Decimal("0.0001")
        )
        daily_rate = emp.base_salary / MONTHLY_WORK_DAYS
        deductions = (daily_rate * summary["absent_days"]).quantize(Decimal("0.0001"))
        net = emp.base_salary + overtime_pay - deductions

        item = PayrollItem(
            id=uuid4(),
            tenant_id=tenant_id,
            payroll_id=payroll.id,
            employee_id=emp.id,
            employee_no=emp.employee_no,
            employee_name=emp.name,
            base_salary=emp.base_salary,
            overtime_pay=overtime_pay,
            deductions=deductions,
            net_pay=net,
        )
        payroll.items.append(item)
        total += net

    payroll.total_amount = total
    session.add(payroll)
    await session.flush()
    return payroll


async def get_payroll(
    session: AsyncSession, *, tenant_id: UUID, payroll_id: UUID
) -> Payroll | None:
    stmt = (
        select(Payroll)
        .options(selectinload(Payroll.items))
        .where(Payroll.id == payroll_id, Payroll.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_payrolls(
    session: AsyncSession, *, tenant_id: UUID
) -> list[Payroll]:
    stmt = (
        select(Payroll)
        .options(selectinload(Payroll.items))
        .where(Payroll.tenant_id == tenant_id)
        .order_by(Payroll.period.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
