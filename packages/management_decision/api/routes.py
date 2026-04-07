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


router.include_router(finance_router)
