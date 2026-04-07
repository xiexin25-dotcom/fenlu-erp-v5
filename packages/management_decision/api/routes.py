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
    ARRecordCreate,
    ARRecordOut,
    ARRecordUpdate,
    GLAccountCreate,
    GLAccountOut,
    JournalEntryCreate,
    JournalEntryOut,
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
