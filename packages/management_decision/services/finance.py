"""
Finance service · GL 科目 + 记账凭证
=====================================
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.management_decision.models.finance import (
    GLAccount,
    JournalEntry,
    JournalLine,
    JournalStatus,
)


# --------------------------------------------------------------------------- #
# GL Account
# --------------------------------------------------------------------------- #


async def create_gl_account(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    code: str,
    name: str,
    account_type: str,
    parent_id: UUID | None = None,
    level: int = 1,
    description: str | None = None,
    created_by: UUID | None = None,
) -> GLAccount:
    account = GLAccount(
        id=uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=name,
        account_type=account_type,
        parent_id=parent_id,
        level=level,
        description=description,
        created_by=created_by,
    )
    session.add(account)
    await session.flush()
    return account


async def list_gl_accounts(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    account_type: str | None = None,
) -> list[GLAccount]:
    stmt = (
        select(GLAccount)
        .where(GLAccount.tenant_id == tenant_id, GLAccount.is_active.is_(True))
        .order_by(GLAccount.code)
    )
    if account_type:
        stmt = stmt.where(GLAccount.account_type == account_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_gl_account(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    account_id: UUID,
) -> GLAccount | None:
    stmt = select(GLAccount).where(
        GLAccount.id == account_id,
        GLAccount.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# --------------------------------------------------------------------------- #
# Journal Entry
# --------------------------------------------------------------------------- #


async def _next_entry_no(session: AsyncSession, tenant_id: UUID, entry_date: date) -> str:
    """生成凭证号: JV-YYYYMM-NNNN"""
    prefix = f"JV-{entry_date.strftime('%Y%m')}-"
    stmt = (
        select(func.count())
        .select_from(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.entry_no.like(f"{prefix}%"),
        )
    )
    result = await session.execute(stmt)
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:04d}"


async def create_journal_entry(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    entry_date: date,
    memo: str | None,
    lines: list[dict],
    created_by: UUID | None = None,
) -> JournalEntry:
    """创建记账凭证。调用方应确保 lines 已通过 schema 校验 (借贷平衡)。"""
    entry_no = await _next_entry_no(session, tenant_id, entry_date)
    entry = JournalEntry(
        id=uuid4(),
        tenant_id=tenant_id,
        entry_no=entry_no,
        entry_date=entry_date,
        status=JournalStatus.DRAFT,
        memo=memo,
        created_by=created_by,
    )
    for idx, ln in enumerate(lines, start=1):
        line = JournalLine(
            id=uuid4(),
            tenant_id=tenant_id,
            entry_id=entry.id,
            line_no=idx,
            account_id=ln["account_id"],
            debit_amount=ln.get("debit_amount", Decimal("0")),
            credit_amount=ln.get("credit_amount", Decimal("0")),
            description=ln.get("description"),
        )
        entry.lines.append(line)

    session.add(entry)
    await session.flush()
    return entry


async def get_journal_entry(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    entry_id: UUID,
) -> JournalEntry | None:
    stmt = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(
            JournalEntry.id == entry_id,
            JournalEntry.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_journal_entries(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[JournalEntry]:
    stmt = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.tenant_id == tenant_id)
        .order_by(JournalEntry.entry_date.desc(), JournalEntry.entry_no.desc())
    )
    if date_from:
        stmt = stmt.where(JournalEntry.entry_date >= date_from)
    if date_to:
        stmt = stmt.where(JournalEntry.entry_date <= date_to)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def post_journal_entry(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    entry_id: UUID,
) -> JournalEntry | None:
    """过账:将凭证状态从 DRAFT → POSTED。"""
    entry = await get_journal_entry(session, tenant_id=tenant_id, entry_id=entry_id)
    if entry is None:
        return None
    if entry.status != JournalStatus.DRAFT:
        raise ValueError(f"只有草稿状态的凭证才能过账,当前状态: {entry.status}")
    entry.status = JournalStatus.POSTED
    entry.posted_at = datetime.now(timezone.utc)
    await session.flush()
    return entry
