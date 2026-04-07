"""
Management Decision · Pydantic schemas (request / response)
============================================================
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, computed_field, model_validator

from packages.shared.contracts.base import BaseSchema


# --------------------------------------------------------------------------- #
# GL Account
# --------------------------------------------------------------------------- #


class GLAccountCreate(BaseSchema):
    code: str = Field(..., max_length=32, description="科目编码")
    name: str = Field(..., max_length=128, description="科目名称")
    account_type: str = Field(..., description="asset/liability/equity/revenue/expense")
    parent_id: UUID | None = None
    level: int = Field(1, ge=1, le=4)
    description: str | None = None


class GLAccountOut(BaseSchema):
    id: UUID
    code: str
    name: str
    account_type: str
    parent_id: UUID | None
    level: int
    is_active: bool
    description: str | None


# --------------------------------------------------------------------------- #
# Journal Entry
# --------------------------------------------------------------------------- #


class JournalLineIn(BaseSchema):
    account_id: UUID
    debit_amount: Decimal = Field(Decimal("0"), ge=0, max_digits=18, decimal_places=4)
    credit_amount: Decimal = Field(Decimal("0"), ge=0, max_digits=18, decimal_places=4)
    description: str | None = None

    @model_validator(mode="after")
    def one_side_only(self) -> JournalLineIn:
        d, c = self.debit_amount, self.credit_amount
        if d > 0 and c > 0:
            raise ValueError("一行只能填借方或贷方,不能同时非零")
        if d == 0 and c == 0:
            raise ValueError("借方和贷方不能同时为零")
        return self


class JournalEntryCreate(BaseSchema):
    entry_date: date
    memo: str | None = None
    lines: list[JournalLineIn] = Field(..., min_length=2)

    @model_validator(mode="after")
    def balanced(self) -> JournalEntryCreate:
        total_debit = sum(ln.debit_amount for ln in self.lines)
        total_credit = sum(ln.credit_amount for ln in self.lines)
        if total_debit != total_credit:
            raise ValueError(
                f"借贷不平衡: 借方合计 {total_debit}, 贷方合计 {total_credit}"
            )
        return self


class JournalLineOut(BaseSchema):
    id: UUID
    line_no: int
    account_id: UUID
    debit_amount: Decimal
    credit_amount: Decimal
    description: str | None


class JournalEntryOut(BaseSchema):
    id: UUID
    entry_no: str
    entry_date: date
    status: str
    memo: str | None
    lines: list[JournalLineOut]


# --------------------------------------------------------------------------- #
# AP (应付账款)
# --------------------------------------------------------------------------- #


class APRecordCreate(BaseSchema):
    purchase_order_id: UUID
    supplier_id: UUID
    total_amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    paid_amount: Decimal = Field(Decimal("0"), ge=0, max_digits=18, decimal_places=4)
    currency: str = Field("CNY", max_length=3)
    due_date: date
    memo: str | None = None


class APRecordUpdate(BaseSchema):
    paid_amount: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=4)
    status: str | None = None
    memo: str | None = None


class APRecordOut(BaseSchema):
    id: UUID
    purchase_order_id: UUID
    supplier_id: UUID
    total_amount: Decimal
    paid_amount: Decimal
    currency: str
    due_date: date
    status: str
    memo: str | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def balance(self) -> Decimal:
        return self.total_amount - self.paid_amount


# --------------------------------------------------------------------------- #
# AR (应收账款)
# --------------------------------------------------------------------------- #


class ARRecordCreate(BaseSchema):
    sales_order_id: UUID
    customer_id: UUID
    total_amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    received_amount: Decimal = Field(Decimal("0"), ge=0, max_digits=18, decimal_places=4)
    currency: str = Field("CNY", max_length=3)
    due_date: date
    memo: str | None = None


class ARRecordUpdate(BaseSchema):
    received_amount: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=4)
    status: str | None = None
    memo: str | None = None


class ARRecordOut(BaseSchema):
    id: UUID
    sales_order_id: UUID
    customer_id: UUID
    total_amount: Decimal
    received_amount: Decimal
    currency: str
    due_date: date
    status: str
    memo: str | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def balance(self) -> Decimal:
        return self.total_amount - self.received_amount


# --------------------------------------------------------------------------- #
# Employee (员工)
# --------------------------------------------------------------------------- #


class EmployeeCreate(BaseSchema):
    employee_no: str = Field(..., max_length=32)
    name: str = Field(..., max_length=64)
    user_id: UUID | None = None
    department_id: UUID | None = None
    position: str = Field("", max_length=64)
    base_salary: Decimal = Field(Decimal("0"), ge=0, max_digits=18, decimal_places=4)
    memo: str | None = None


class EmployeeUpdate(BaseSchema):
    name: str | None = Field(None, max_length=64)
    department_id: UUID | None = None
    position: str | None = Field(None, max_length=64)
    base_salary: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=4)
    is_active: bool | None = None
    memo: str | None = None


class EmployeeOut(BaseSchema):
    id: UUID
    employee_no: str
    name: str
    user_id: UUID | None
    department_id: UUID | None
    position: str
    base_salary: Decimal
    is_active: bool
    memo: str | None


# --------------------------------------------------------------------------- #
# Payroll (薪资)
# --------------------------------------------------------------------------- #


class PayrollItemOut(BaseSchema):
    id: UUID
    employee_id: UUID
    employee_no: str
    employee_name: str
    base_salary: Decimal
    overtime_pay: Decimal
    deductions: Decimal
    net_pay: Decimal
    memo: str | None


class PayrollOut(BaseSchema):
    id: UUID
    period: str
    status: str
    total_amount: Decimal
    head_count: int
    memo: str | None
    items: list[PayrollItemOut]


# --------------------------------------------------------------------------- #
# Attendance (考勤)
# --------------------------------------------------------------------------- #


class AttendanceCreate(BaseSchema):
    employee_id: UUID
    work_date: date
    clock_in: time | None = None
    clock_out: time | None = None
    status: str = Field("normal", description="normal/late/early_leave/absent/leave/holiday")
    work_hours: Decimal = Field(Decimal("8.00"), ge=0, max_digits=5, decimal_places=2)
    overtime_hours: Decimal = Field(Decimal("0"), ge=0, max_digits=5, decimal_places=2)
    memo: str | None = None


class AttendanceOut(BaseSchema):
    id: UUID
    employee_id: UUID
    work_date: date
    clock_in: time | None
    clock_out: time | None
    status: str
    work_hours: Decimal
    overtime_hours: Decimal
    memo: str | None


class AttendanceImportRow(BaseSchema):
    """V4 ETL 批量导入行 — 用 employee_no 而非 UUID 关联。"""

    employee_no: str = Field(..., max_length=32)
    work_date: date
    clock_in: time | None = None
    clock_out: time | None = None
    status: str = "normal"
    work_hours: Decimal = Field(Decimal("8.00"), ge=0, max_digits=5, decimal_places=2)
    overtime_hours: Decimal = Field(Decimal("0"), ge=0, max_digits=5, decimal_places=2)
    memo: str | None = None


class AttendanceImportRequest(BaseSchema):
    rows: list[AttendanceImportRow] = Field(..., min_length=1)


class AttendanceImportResult(BaseSchema):
    imported: int
    skipped: int
    errors: list[str]


# --------------------------------------------------------------------------- #
# Approval Definition (审批模板)
# --------------------------------------------------------------------------- #


class ApprovalStepConfig(BaseSchema):
    """审批模板中的步骤配置。"""

    step_no: int = Field(..., ge=1)
    name: str = Field(..., max_length=128)
    approver_id: UUID


class ApprovalDefinitionCreate(BaseSchema):
    business_type: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    steps_config: list[ApprovalStepConfig] = Field(..., min_length=1)
    description: str | None = None


class ApprovalDefinitionOut(BaseSchema):
    id: UUID
    business_type: str
    name: str
    steps_config: list[dict[str, Any]]
    is_active: bool
    description: str | None


# --------------------------------------------------------------------------- #
# Approval Instance + Step (审批实例)
# --------------------------------------------------------------------------- #


class ApprovalSubmit(BaseSchema):
    """发起审批 — 匹配 contracts/management.py ApprovalRequest。"""

    business_type: str = Field(..., max_length=64)
    business_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalActionRequest(BaseSchema):
    """审批动作 (approve / reject / withdraw)。"""

    action: str = Field(..., description="approve / reject / withdraw")
    comment: str | None = None


class ApprovalStepOut(BaseSchema):
    id: UUID
    step_no: int
    name: str
    approver_id: UUID
    status: str
    action: str | None
    comment: str | None
    acted_at: datetime | None


class ApprovalInstanceOut(BaseSchema):
    id: UUID
    business_type: str
    business_id: UUID
    initiator_id: UUID
    payload: dict[str, Any]
    status: str
    current_step: int
    total_steps: int
    completed_at: datetime | None
    steps: list[ApprovalStepOut]
