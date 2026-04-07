"""
人力资源 · Employee / Payroll / PayrollItem
============================================

Employee 通过 user_id 关联 foundation 的 User (公用登录账号),
department_id 关联 Organization (公用组织架构)。

Payroll 以月度 period 为粒度,每次 run 生成当月全体在职员工的 PayrollItem。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db.base import Base
from packages.shared.db.mixins import AuditMixin, TenantMixin, TimestampMixin, UUIDPKMixin

SCHEMA = "mgmt"


# --------------------------------------------------------------------------- #
# Employee
# --------------------------------------------------------------------------- #


class Employee(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """员工档案,关联 public.users 和 public.organizations。"""

    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_no", name="uq_employees_tenant_no"),
        UniqueConstraint("tenant_id", "user_id", name="uq_employees_tenant_user"),
        Index("ix_employees_tenant_dept", "tenant_id", "department_id"),
        {"schema": SCHEMA},
    )

    employee_no: Mapped[str] = mapped_column(String(32), nullable=False, comment="工号")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联登录账号",
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("public.organizations.id", ondelete="SET NULL"),
        nullable=True,
        comment="所属部门",
    )
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="", comment="岗位")
    base_salary: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="基本工资"
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# Payroll
# --------------------------------------------------------------------------- #


class PayrollStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PAID = "paid"


class Payroll(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """月度薪资批次。"""

    __tablename__ = "payrolls"
    __table_args__ = (
        UniqueConstraint("tenant_id", "period", name="uq_payrolls_tenant_period"),
        {"schema": SCHEMA},
    )

    period: Mapped[str] = mapped_column(
        String(7), nullable=False, comment="薪资周期 YYYY-MM"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PayrollStatus.DRAFT
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="总金额"
    )
    head_count: Mapped[int] = mapped_column(nullable=False, default=0, comment="人数")
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[PayrollItem]] = relationship(
        "PayrollItem",
        back_populates="payroll",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# --------------------------------------------------------------------------- #
# PayrollItem (工资条)
# --------------------------------------------------------------------------- #


class PayrollItem(Base, UUIDPKMixin, TenantMixin, TimestampMixin):
    """单人工资条。"""

    __tablename__ = "payroll_items"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "payroll_id", "employee_id", name="uq_payroll_items_payroll_emp"
        ),
        Index("ix_payroll_items_payroll", "payroll_id"),
        Index("ix_payroll_items_employee", "employee_id"),
        {"schema": SCHEMA},
    )

    payroll_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.payrolls.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.employees.id", ondelete="RESTRICT"),
        nullable=False,
    )
    employee_no: Mapped[str] = mapped_column(String(32), nullable=False, comment="冗余工号")
    employee_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="冗余姓名")
    base_salary: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="基本工资"
    )
    overtime_pay: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="加班费"
    )
    deductions: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="缺勤扣款"
    )
    gross_pay: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="应发合计"
    )
    # 五险一金 — 个人
    pension_employee: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="养老保险(个人8%)"
    )
    medical_employee: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="医疗保险(个人2%)"
    )
    unemployment_employee: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="失业保险(个人0.3%)"
    )
    housing_fund_employee: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="住房公积金(个人8%)"
    )
    social_insurance_employee: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="五险个人合计"
    )
    # 五险一金 — 单位
    pension_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="养老保险(单位16%)"
    )
    medical_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="医疗保险(单位8%)"
    )
    unemployment_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="失业保险(单位0.7%)"
    )
    injury_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="工伤保险(单位0.5%)"
    )
    housing_fund_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="住房公积金(单位8%)"
    )
    social_insurance_employer: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="五险一金单位合计"
    )
    # 个税
    taxable_income: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="应纳税所得额"
    )
    income_tax: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="个人所得税"
    )
    net_pay: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, comment="实发工资"
    )
    memo: Mapped[str | None] = mapped_column(String(256), nullable=True)

    payroll: Mapped[Payroll] = relationship("Payroll", back_populates="items")
