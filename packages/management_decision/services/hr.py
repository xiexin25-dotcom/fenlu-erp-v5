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

    # ── 薪资参数 ──
    MONTHLY_WORK_DAYS = Decimal("21.75")
    OVERTIME_RATE = Decimal("1.5")
    DAILY_HOURS = Decimal("8")
    Q4 = Decimal("0.0001")  # 精度: 4位小数

    # ── 吉林省五险一金费率 ──
    SOCIAL_BASE_MIN = Decimal("4900")
    SOCIAL_BASE_MAX = Decimal("26533")
    HOUSING_BASE_MIN = Decimal("2100")
    HOUSING_BASE_MAX = Decimal("26533")
    # 个人
    PENSION_EMP_RATE = Decimal("0.08")
    MEDICAL_EMP_RATE = Decimal("0.02")
    UNEMPLOYMENT_EMP_RATE = Decimal("0.003")
    HOUSING_EMP_RATE = Decimal("0.08")
    # 单位
    PENSION_ER_RATE = Decimal("0.16")
    MEDICAL_ER_RATE = Decimal("0.08")
    UNEMPLOYMENT_ER_RATE = Decimal("0.007")
    INJURY_ER_RATE = Decimal("0.005")
    HOUSING_ER_RATE = Decimal("0.08")
    # 个税
    TAX_THRESHOLD = Decimal("5000")
    TAX_BRACKETS = [
        (Decimal("3000"), Decimal("0.03"), Decimal("0")),
        (Decimal("12000"), Decimal("0.10"), Decimal("210")),
        (Decimal("25000"), Decimal("0.20"), Decimal("1410")),
        (Decimal("35000"), Decimal("0.25"), Decimal("2660")),
        (Decimal("55000"), Decimal("0.30"), Decimal("4410")),
        (Decimal("80000"), Decimal("0.35"), Decimal("7160")),
        (Decimal("9999999"), Decimal("0.45"), Decimal("15160")),
    ]

    def _clamp(val: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
        return max(lo, min(hi, val))

    def _calc_tax(taxable: Decimal) -> Decimal:
        if taxable <= 0:
            return Decimal("0")
        for upper, rate, deduct in TAX_BRACKETS:
            if taxable <= upper:
                return (taxable * rate - deduct).quantize(Q4)
        return Decimal("0")

    total = Decimal("0")
    for emp in employees:
        summary = await get_monthly_attendance_summary(
            session, tenant_id=tenant_id, employee_id=emp.id, period=period
        )
        hourly_rate = emp.base_salary / MONTHLY_WORK_DAYS / DAILY_HOURS
        overtime_pay = (hourly_rate * OVERTIME_RATE * summary["overtime_hours"]).quantize(Q4)
        daily_rate = emp.base_salary / MONTHLY_WORK_DAYS
        absent_deductions = (daily_rate * summary["absent_days"]).quantize(Q4)
        gross = emp.base_salary + overtime_pay - absent_deductions

        # 五险一金基数
        social_base = _clamp(emp.base_salary, SOCIAL_BASE_MIN, SOCIAL_BASE_MAX)
        housing_base = _clamp(emp.base_salary, HOUSING_BASE_MIN, HOUSING_BASE_MAX)

        # 个人部分
        pension_emp = (social_base * PENSION_EMP_RATE).quantize(Q4)
        medical_emp = (social_base * MEDICAL_EMP_RATE).quantize(Q4)
        unemployment_emp = (social_base * UNEMPLOYMENT_EMP_RATE).quantize(Q4)
        housing_emp = (housing_base * HOUSING_EMP_RATE).quantize(Q4)
        si_employee = pension_emp + medical_emp + unemployment_emp

        # 单位部分
        pension_er = (social_base * PENSION_ER_RATE).quantize(Q4)
        medical_er = (social_base * MEDICAL_ER_RATE).quantize(Q4)
        unemployment_er = (social_base * UNEMPLOYMENT_ER_RATE).quantize(Q4)
        injury_er = (social_base * INJURY_ER_RATE).quantize(Q4)
        housing_er = (housing_base * HOUSING_ER_RATE).quantize(Q4)
        si_employer = pension_er + medical_er + unemployment_er + injury_er

        # 个税
        taxable_income = gross - si_employee - housing_emp - TAX_THRESHOLD
        income_tax = _calc_tax(taxable_income)

        # 实发
        net = gross - si_employee - housing_emp - income_tax

        item = PayrollItem(
            id=uuid4(),
            tenant_id=tenant_id,
            payroll_id=payroll.id,
            employee_id=emp.id,
            employee_no=emp.employee_no,
            employee_name=emp.name,
            base_salary=emp.base_salary,
            overtime_pay=overtime_pay,
            deductions=absent_deductions,
            gross_pay=gross,
            pension_employee=pension_emp,
            medical_employee=medical_emp,
            unemployment_employee=unemployment_emp,
            housing_fund_employee=housing_emp,
            social_insurance_employee=si_employee,
            pension_employer=pension_er,
            medical_employer=medical_er,
            unemployment_employer=unemployment_er,
            injury_employer=injury_er,
            housing_fund_employer=housing_er,
            social_insurance_employer=si_employer + housing_er,
            taxable_income=max(taxable_income, Decimal("0")),
            income_tax=income_tax,
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
