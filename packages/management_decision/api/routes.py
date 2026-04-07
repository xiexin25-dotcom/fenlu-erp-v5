"""Lane: management_decision · API routes。

提供 GL 科目与记账凭证的 CRUD 端点,路径前缀 /mgmt。
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.auth.deps import CurrentUser, require_permission
from packages.shared.db import get_session

from .schemas import (
    APRecordCreate,
    APRecordOut,
    APRecordUpdate,
    ApprovalActionRequest,
    ApprovalDefinitionCreate,
    ApprovalDefinitionOut,
    ApprovalInstanceOut,
    ApprovalSubmit,
    ARRecordCreate,
    ARRecordOut,
    ARRecordUpdate,
    AttendanceCreate,
    AttendanceImportRequest,
    AttendanceImportResult,
    AttendanceOut,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    GLAccountCreate,
    GLAccountOut,
    JournalEntryCreate,
    JournalEntryOut,
    PayrollOut,
)

router = APIRouter(prefix="/mgmt", tags=["management"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Lane-level health probe."""
    return {"status": "ok", "lane": "management_decision"}


# --------------------------------------------------------------------------- #
# GL Accounts
# --------------------------------------------------------------------------- #

finance_router = APIRouter(prefix="/finance", tags=["finance"])


@finance_router.post(
    "/accounts",
    response_model=GLAccountOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.gl_account", "create"))],
)
async def create_account(
    body: GLAccountCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> GLAccountOut:
    from packages.management_decision.services.finance import create_gl_account

    account = await create_gl_account(
        session,
        tenant_id=user.tenant_id,
        code=body.code,
        name=body.name,
        account_type=body.account_type,
        parent_id=body.parent_id,
        level=body.level,
        description=body.description,
        created_by=user.id,
    )
    return GLAccountOut.model_validate(account)


@finance_router.get(
    "/accounts",
    response_model=list[GLAccountOut],
    dependencies=[Depends(require_permission("mgmt.gl_account", "read"))],
)
async def list_accounts(
    user: CurrentUser,
    account_type: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[GLAccountOut]:
    from packages.management_decision.services.finance import list_gl_accounts

    accounts = await list_gl_accounts(
        session, tenant_id=user.tenant_id, account_type=account_type
    )
    return [GLAccountOut.model_validate(a) for a in accounts]


@finance_router.get(
    "/accounts/{account_id}",
    response_model=GLAccountOut,
    dependencies=[Depends(require_permission("mgmt.gl_account", "read"))],
)
async def get_account(
    account_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> GLAccountOut:
    from packages.management_decision.services.finance import get_gl_account

    account = await get_gl_account(session, tenant_id=user.tenant_id, account_id=account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="科目不存在")
    return GLAccountOut.model_validate(account)


# --------------------------------------------------------------------------- #
# Journal Entries
# --------------------------------------------------------------------------- #


@finance_router.post(
    "/journal",
    response_model=JournalEntryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.journal", "create"))],
)
async def create_journal(
    body: JournalEntryCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> JournalEntryOut:
    from packages.management_decision.services.finance import create_journal_entry

    entry = await create_journal_entry(
        session,
        tenant_id=user.tenant_id,
        entry_date=body.entry_date,
        memo=body.memo,
        lines=[ln.model_dump() for ln in body.lines],
        created_by=user.id,
    )
    return JournalEntryOut.model_validate(entry)


@finance_router.get(
    "/journal",
    response_model=list[JournalEntryOut],
    dependencies=[Depends(require_permission("mgmt.journal", "read"))],
)
async def list_journals(
    user: CurrentUser,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[JournalEntryOut]:
    from packages.management_decision.services.finance import list_journal_entries

    entries = await list_journal_entries(
        session,
        tenant_id=user.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )
    return [JournalEntryOut.model_validate(e) for e in entries]


@finance_router.get(
    "/journal/{entry_id}",
    response_model=JournalEntryOut,
    dependencies=[Depends(require_permission("mgmt.journal", "read"))],
)
async def get_journal(
    entry_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> JournalEntryOut:
    from packages.management_decision.services.finance import get_journal_entry

    entry = await get_journal_entry(session, tenant_id=user.tenant_id, entry_id=entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="凭证不存在")
    return JournalEntryOut.model_validate(entry)


@finance_router.post(
    "/journal/{entry_id}/post",
    response_model=JournalEntryOut,
    dependencies=[Depends(require_permission("mgmt.journal", "post"))],
)
async def post_journal(
    entry_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> JournalEntryOut:
    from packages.management_decision.services.finance import post_journal_entry

    try:
        entry = await post_journal_entry(
            session, tenant_id=user.tenant_id, entry_id=entry_id
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if entry is None:
        raise HTTPException(status_code=404, detail="凭证不存在")
    return JournalEntryOut.model_validate(entry)


# --------------------------------------------------------------------------- #
# AP (应付账款)
# --------------------------------------------------------------------------- #


@finance_router.post(
    "/ap",
    response_model=APRecordOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.ap", "create"))],
)
async def create_ap(
    body: APRecordCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APRecordOut:
    from packages.management_decision.services.ap_ar import create_ap_record

    record = await create_ap_record(
        session,
        tenant_id=user.tenant_id,
        purchase_order_id=body.purchase_order_id,
        supplier_id=body.supplier_id,
        total_amount=body.total_amount,
        paid_amount=body.paid_amount,
        currency=body.currency,
        due_date=body.due_date,
        memo=body.memo,
        created_by=user.id,
    )
    return APRecordOut.model_validate(record)


@finance_router.get(
    "/ap",
    response_model=list[APRecordOut],
    dependencies=[Depends(require_permission("mgmt.ap", "read"))],
)
async def list_ap(
    user: CurrentUser,
    ap_status: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[APRecordOut]:
    from packages.management_decision.services.ap_ar import list_ap_records

    records = await list_ap_records(session, tenant_id=user.tenant_id, status=ap_status)
    return [APRecordOut.model_validate(r) for r in records]


@finance_router.get(
    "/ap/{record_id}",
    response_model=APRecordOut,
    dependencies=[Depends(require_permission("mgmt.ap", "read"))],
)
async def get_ap(
    record_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APRecordOut:
    from packages.management_decision.services.ap_ar import get_ap_record

    record = await get_ap_record(session, tenant_id=user.tenant_id, record_id=record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="应付记录不存在")
    return APRecordOut.model_validate(record)


@finance_router.patch(
    "/ap/{record_id}",
    response_model=APRecordOut,
    dependencies=[Depends(require_permission("mgmt.ap", "update"))],
)
async def update_ap(
    record_id: UUID,
    body: APRecordUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APRecordOut:
    from packages.management_decision.services.ap_ar import update_ap_record

    record = await update_ap_record(
        session,
        tenant_id=user.tenant_id,
        record_id=record_id,
        paid_amount=body.paid_amount,
        status=body.status,
        memo=body.memo,
        updated_by=user.id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="应付记录不存在")
    return APRecordOut.model_validate(record)


# --------------------------------------------------------------------------- #
# AR (应收账款)
# --------------------------------------------------------------------------- #


@finance_router.post(
    "/ar",
    response_model=ARRecordOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.ar", "create"))],
)
async def create_ar(
    body: ARRecordCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ARRecordOut:
    from packages.management_decision.services.ap_ar import create_ar_record

    record = await create_ar_record(
        session,
        tenant_id=user.tenant_id,
        sales_order_id=body.sales_order_id,
        customer_id=body.customer_id,
        total_amount=body.total_amount,
        received_amount=body.received_amount,
        currency=body.currency,
        due_date=body.due_date,
        memo=body.memo,
        created_by=user.id,
    )
    return ARRecordOut.model_validate(record)


@finance_router.get(
    "/ar",
    response_model=list[ARRecordOut],
    dependencies=[Depends(require_permission("mgmt.ar", "read"))],
)
async def list_ar(
    user: CurrentUser,
    ar_status: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[ARRecordOut]:
    from packages.management_decision.services.ap_ar import list_ar_records

    records = await list_ar_records(session, tenant_id=user.tenant_id, status=ar_status)
    return [ARRecordOut.model_validate(r) for r in records]


@finance_router.get(
    "/ar/{record_id}",
    response_model=ARRecordOut,
    dependencies=[Depends(require_permission("mgmt.ar", "read"))],
)
async def get_ar(
    record_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ARRecordOut:
    from packages.management_decision.services.ap_ar import get_ar_record

    record = await get_ar_record(session, tenant_id=user.tenant_id, record_id=record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="应收记录不存在")
    return ARRecordOut.model_validate(record)


@finance_router.patch(
    "/ar/{record_id}",
    response_model=ARRecordOut,
    dependencies=[Depends(require_permission("mgmt.ar", "update"))],
)
async def update_ar(
    record_id: UUID,
    body: ARRecordUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ARRecordOut:
    from packages.management_decision.services.ap_ar import update_ar_record

    record = await update_ar_record(
        session,
        tenant_id=user.tenant_id,
        record_id=record_id,
        received_amount=body.received_amount,
        status=body.status,
        memo=body.memo,
        updated_by=user.id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="应收记录不存在")
    return ARRecordOut.model_validate(record)


router.include_router(finance_router)


# =========================================================================== #
# HR
# =========================================================================== #

hr_router = APIRouter(prefix="/hr", tags=["hr"])


# --------------------------------------------------------------------------- #
# Employee
# --------------------------------------------------------------------------- #


@hr_router.post(
    "/employees",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.employee", "create"))],
)
async def create_employee(
    body: EmployeeCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> EmployeeOut:
    from packages.management_decision.services.hr import create_employee as _create

    emp = await _create(
        session,
        tenant_id=user.tenant_id,
        employee_no=body.employee_no,
        name=body.name,
        user_id=body.user_id,
        department_id=body.department_id,
        position=body.position,
        base_salary=body.base_salary,
        memo=body.memo,
        created_by=user.id,
    )
    return EmployeeOut.model_validate(emp)


@hr_router.get(
    "/employees",
    response_model=list[EmployeeOut],
    dependencies=[Depends(require_permission("mgmt.employee", "read"))],
)
async def list_employees_api(
    user: CurrentUser,
    active_only: bool = Query(True),
    session: AsyncSession = Depends(get_session),
) -> list[EmployeeOut]:
    from packages.management_decision.services.hr import list_employees

    emps = await list_employees(session, tenant_id=user.tenant_id, active_only=active_only)
    return [EmployeeOut.model_validate(e) for e in emps]


@hr_router.get(
    "/employees/{employee_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(require_permission("mgmt.employee", "read"))],
)
async def get_employee_api(
    employee_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> EmployeeOut:
    from packages.management_decision.services.hr import get_employee

    emp = await get_employee(session, tenant_id=user.tenant_id, employee_id=employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    return EmployeeOut.model_validate(emp)


@hr_router.patch(
    "/employees/{employee_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(require_permission("mgmt.employee", "update"))],
)
async def update_employee_api(
    employee_id: UUID,
    body: EmployeeUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> EmployeeOut:
    from packages.management_decision.services.hr import update_employee

    emp = await update_employee(
        session,
        tenant_id=user.tenant_id,
        employee_id=employee_id,
        name=body.name,
        department_id=body.department_id,
        position=body.position,
        base_salary=body.base_salary,
        is_active=body.is_active,
        memo=body.memo,
        updated_by=user.id,
    )
    if emp is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    return EmployeeOut.model_validate(emp)


# --------------------------------------------------------------------------- #
# Payroll
# --------------------------------------------------------------------------- #


@hr_router.post(
    "/payroll/run",
    response_model=PayrollOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.payroll", "create"))],
)
async def run_payroll_api(
    user: CurrentUser,
    period: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="薪资周期 YYYY-MM"),
    session: AsyncSession = Depends(get_session),
) -> PayrollOut:
    from packages.management_decision.services.hr import run_payroll

    try:
        payroll = await run_payroll(
            session, tenant_id=user.tenant_id, period=period, created_by=user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return PayrollOut.model_validate(payroll)


@hr_router.get(
    "/payroll",
    response_model=list[PayrollOut],
    dependencies=[Depends(require_permission("mgmt.payroll", "read"))],
)
async def list_payrolls_api(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[PayrollOut]:
    from packages.management_decision.services.hr import list_payrolls

    payrolls = await list_payrolls(session, tenant_id=user.tenant_id)
    return [PayrollOut.model_validate(p) for p in payrolls]


@hr_router.get(
    "/payroll/{payroll_id}",
    response_model=PayrollOut,
    dependencies=[Depends(require_permission("mgmt.payroll", "read"))],
)
async def get_payroll_api(
    payroll_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> PayrollOut:
    from packages.management_decision.services.hr import get_payroll

    payroll = await get_payroll(session, tenant_id=user.tenant_id, payroll_id=payroll_id)
    if payroll is None:
        raise HTTPException(status_code=404, detail="薪资批次不存在")
    return PayrollOut.model_validate(payroll)


# --------------------------------------------------------------------------- #
# Attendance (考勤)
# --------------------------------------------------------------------------- #


@hr_router.post(
    "/attendance",
    response_model=AttendanceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.attendance", "create"))],
)
async def create_attendance_api(
    body: AttendanceCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> AttendanceOut:
    from packages.management_decision.services.attendance import create_attendance

    record = await create_attendance(
        session,
        tenant_id=user.tenant_id,
        employee_id=body.employee_id,
        work_date=body.work_date,
        clock_in=body.clock_in,
        clock_out=body.clock_out,
        status=body.status,
        work_hours=body.work_hours,
        overtime_hours=body.overtime_hours,
        memo=body.memo,
        created_by=user.id,
    )
    return AttendanceOut.model_validate(record)


@hr_router.get(
    "/attendance",
    response_model=list[AttendanceOut],
    dependencies=[Depends(require_permission("mgmt.attendance", "read"))],
)
async def list_attendance_api(
    user: CurrentUser,
    employee_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[AttendanceOut]:
    from packages.management_decision.services.attendance import list_attendance

    records = await list_attendance(
        session,
        tenant_id=user.tenant_id,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )
    return [AttendanceOut.model_validate(r) for r in records]


@hr_router.get(
    "/attendance/{record_id}",
    response_model=AttendanceOut,
    dependencies=[Depends(require_permission("mgmt.attendance", "read"))],
)
async def get_attendance_api(
    record_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> AttendanceOut:
    from packages.management_decision.services.attendance import get_attendance

    record = await get_attendance(session, tenant_id=user.tenant_id, record_id=record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="考勤记录不存在")
    return AttendanceOut.model_validate(record)


@hr_router.post(
    "/attendance/import",
    response_model=AttendanceImportResult,
    dependencies=[Depends(require_permission("mgmt.attendance", "create"))],
)
async def import_attendance_api(
    body: AttendanceImportRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> AttendanceImportResult:
    """V4 考勤数据批量导入 — 用 employee_no 关联员工。"""
    from packages.management_decision.services.attendance import import_attendance_batch

    result = await import_attendance_batch(
        session,
        tenant_id=user.tenant_id,
        rows=[r.model_dump() for r in body.rows],
        created_by=user.id,
    )
    return AttendanceImportResult(**result)


router.include_router(hr_router)


# =========================================================================== #
# Approval (审批流)
# =========================================================================== #

approval_router = APIRouter(prefix="/approval", tags=["approval"])


# --------------------------------------------------------------------------- #
# Definition CRUD
# --------------------------------------------------------------------------- #


@approval_router.post(
    "/definitions",
    response_model=ApprovalDefinitionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.approval_def", "create"))],
)
async def create_definition_api(
    body: ApprovalDefinitionCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ApprovalDefinitionOut:
    from packages.management_decision.services.approval import create_definition

    defn = await create_definition(
        session,
        tenant_id=user.tenant_id,
        business_type=body.business_type,
        name=body.name,
        steps_config=[s.model_dump(mode="json") for s in body.steps_config],
        description=body.description,
        created_by=user.id,
    )
    return ApprovalDefinitionOut.model_validate(defn)


@approval_router.get(
    "/definitions",
    response_model=list[ApprovalDefinitionOut],
    dependencies=[Depends(require_permission("mgmt.approval_def", "read"))],
)
async def list_definitions_api(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[ApprovalDefinitionOut]:
    from packages.management_decision.services.approval import list_definitions

    defs = await list_definitions(session, tenant_id=user.tenant_id)
    return [ApprovalDefinitionOut.model_validate(d) for d in defs]


@approval_router.get(
    "/definitions/{definition_id}",
    response_model=ApprovalDefinitionOut,
    dependencies=[Depends(require_permission("mgmt.approval_def", "read"))],
)
async def get_definition_api(
    definition_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ApprovalDefinitionOut:
    from packages.management_decision.services.approval import get_definition

    defn = await get_definition(
        session, tenant_id=user.tenant_id, definition_id=definition_id
    )
    if defn is None:
        raise HTTPException(status_code=404, detail="审批定义不存在")
    return ApprovalDefinitionOut.model_validate(defn)


# --------------------------------------------------------------------------- #
# Submit + Action
# --------------------------------------------------------------------------- #


@approval_router.post(
    "",
    response_model=ApprovalInstanceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("mgmt.approval", "create"))],
)
async def submit_approval_api(
    body: ApprovalSubmit,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ApprovalInstanceOut:
    from packages.management_decision.services.approval import submit_approval

    try:
        instance = await submit_approval(
            session,
            tenant_id=user.tenant_id,
            business_type=body.business_type,
            business_id=body.business_id,
            initiator_id=user.id,
            payload=body.payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ApprovalInstanceOut.model_validate(instance)


@approval_router.post(
    "/{instance_id}/action",
    response_model=ApprovalInstanceOut,
    dependencies=[Depends(require_permission("mgmt.approval", "action"))],
)
async def act_on_approval_api(
    instance_id: UUID,
    body: ApprovalActionRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ApprovalInstanceOut:
    from packages.management_decision.services.approval import act_on_approval

    try:
        instance = await act_on_approval(
            session,
            tenant_id=user.tenant_id,
            instance_id=instance_id,
            actor_id=user.id,
            action=body.action,
            comment=body.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ApprovalInstanceOut.model_validate(instance)


# --------------------------------------------------------------------------- #
# Query
# --------------------------------------------------------------------------- #


@approval_router.get(
    "",
    response_model=list[ApprovalInstanceOut],
    dependencies=[Depends(require_permission("mgmt.approval", "read"))],
)
async def list_instances_api(
    user: CurrentUser,
    business_type: str | None = Query(None),
    inst_status: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[ApprovalInstanceOut]:
    from packages.management_decision.services.approval import list_instances

    instances = await list_instances(
        session,
        tenant_id=user.tenant_id,
        business_type=business_type,
        status=inst_status,
    )
    return [ApprovalInstanceOut.model_validate(i) for i in instances]


@approval_router.get(
    "/pending",
    response_model=list[ApprovalInstanceOut],
    dependencies=[Depends(require_permission("mgmt.approval", "read"))],
)
async def list_pending_api(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[ApprovalInstanceOut]:
    from packages.management_decision.services.approval import list_pending_for_approver

    instances = await list_pending_for_approver(
        session, tenant_id=user.tenant_id, approver_id=user.id
    )
    return [ApprovalInstanceOut.model_validate(i) for i in instances]


@approval_router.get(
    "/{instance_id}",
    response_model=ApprovalInstanceOut,
    dependencies=[Depends(require_permission("mgmt.approval", "read"))],
)
async def get_instance_api(
    instance_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ApprovalInstanceOut:
    from packages.management_decision.services.approval import get_instance

    instance = await get_instance(
        session, tenant_id=user.tenant_id, instance_id=instance_id
    )
    if instance is None:
        raise HTTPException(status_code=404, detail="审批实例不存在")
    return ApprovalInstanceOut.model_validate(instance)


router.include_router(approval_router)
