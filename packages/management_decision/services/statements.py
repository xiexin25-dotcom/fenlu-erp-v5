"""
三张财务报表
=============

从 GL 已过账凭证 (JournalEntry.status == 'posted') 聚合生成:
1. 资产负债表 (Balance Sheet)
2. 利润表 (Income Statement)
3. 现金流量表 (Cash Flow Statement)

会计恒等式: 资产 = 负债 + 所有者权益
利润 = 收入 - 费用 → 结转到权益

借方增加: 资产、费用
贷方增加: 负债、权益、收入
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.ap_ar import APRecord, APStatus, ARRecord
from packages.management_decision.models.finance import (
    AccountType,
    GLAccount,
    JournalEntry,
    JournalLine,
    JournalStatus,
)


def _period_range(period: str) -> tuple[date, date]:
    """YYYY-MM → (first_day, last_day)。"""
    y, m = int(period[:4]), int(period[5:7])
    _, last = monthrange(y, m)
    return date(y, m, 1), date(y, m, last)


async def _account_balances(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, list[dict]]:
    """按科目类型聚合已过账凭证行,返回各科目余额。

    Returns: {account_type: [{code, name, balance}, ...]}
    """
    # 子查询: 已过账凭证 ID
    posted_ids = (
        select(JournalEntry.id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.status == JournalStatus.POSTED,
        )
    )
    if date_from:
        posted_ids = posted_ids.where(JournalEntry.entry_date >= date_from)
    if date_to:
        posted_ids = posted_ids.where(JournalEntry.entry_date <= date_to)
    posted_ids = posted_ids.scalar_subquery()

    stmt = (
        select(
            GLAccount.code,
            GLAccount.name,
            GLAccount.account_type,
            func.coalesce(func.sum(JournalLine.debit_amount), 0).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit_amount), 0).label("total_credit"),
        )
        .join(GLAccount, JournalLine.account_id == GLAccount.id)
        .where(
            JournalLine.tenant_id == tenant_id,
            JournalLine.entry_id.in_(posted_ids),
        )
        .group_by(GLAccount.code, GLAccount.name, GLAccount.account_type)
        .order_by(GLAccount.code)
    )

    rows = (await session.execute(stmt)).all()

    result: dict[str, list[dict]] = {
        AccountType.ASSET: [],
        AccountType.LIABILITY: [],
        AccountType.EQUITY: [],
        AccountType.REVENUE: [],
        AccountType.EXPENSE: [],
    }

    for code, name, acct_type, total_debit, total_credit in rows:
        # 资产/费用: 余额 = 借方 - 贷方
        # 负债/权益/收入: 余额 = 贷方 - 借方
        if acct_type in (AccountType.ASSET, AccountType.EXPENSE):
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        result.setdefault(acct_type, []).append({
            "code": code,
            "name": name,
            "balance": float(balance),
        })

    return result


def _sum_balances(items: list[dict]) -> float:
    return sum(i["balance"] for i in items)


# --------------------------------------------------------------------------- #
# 1. 资产负债表 (Balance Sheet)
# --------------------------------------------------------------------------- #


async def balance_sheet(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    period: str,
) -> dict:
    """资产负债表: 截至 period 末的资产 / 负债 / 权益。

    累积余额 (从建账到 period 末),非单月增量。
    """
    _, end = _period_range(period)
    balances = await _account_balances(
        session, tenant_id=tenant_id, date_to=end
    )

    # 当期利润结转到权益
    revenue_total = _sum_balances(balances.get(AccountType.REVENUE, []))
    expense_total = _sum_balances(balances.get(AccountType.EXPENSE, []))
    net_income = revenue_total - expense_total

    assets = balances.get(AccountType.ASSET, [])
    liabilities = balances.get(AccountType.LIABILITY, [])
    equity_items = balances.get(AccountType.EQUITY, [])

    total_assets = _sum_balances(assets)
    total_liabilities = _sum_balances(liabilities)
    total_equity = _sum_balances(equity_items) + net_income

    return {
        "title": "资产负债表",
        "period": period,
        "as_of": end.isoformat(),
        "assets": {
            "items": assets,
            "total": round(total_assets, 4),
        },
        "liabilities": {
            "items": liabilities,
            "total": round(total_liabilities, 4),
        },
        "equity": {
            "items": equity_items,
            "retained_earnings": round(net_income, 4),
            "total": round(total_equity, 4),
        },
        "liabilities_and_equity": round(total_liabilities + total_equity, 4),
        "balanced": abs(total_assets - (total_liabilities + total_equity)) < 0.01,
    }


# --------------------------------------------------------------------------- #
# 2. 利润表 (Income Statement)
# --------------------------------------------------------------------------- #


async def income_statement(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    period: str,
) -> dict:
    """利润表: 单月收入 - 费用 = 净利润。"""
    start, end = _period_range(period)
    balances = await _account_balances(
        session, tenant_id=tenant_id, date_from=start, date_to=end
    )

    revenue_items = balances.get(AccountType.REVENUE, [])
    expense_items = balances.get(AccountType.EXPENSE, [])
    total_revenue = _sum_balances(revenue_items)
    total_expense = _sum_balances(expense_items)
    net_income = total_revenue - total_expense

    return {
        "title": "利润表",
        "period": period,
        "date_range": {"from": start.isoformat(), "to": end.isoformat()},
        "revenue": {
            "items": revenue_items,
            "total": round(total_revenue, 4),
        },
        "expenses": {
            "items": expense_items,
            "total": round(total_expense, 4),
        },
        "net_income": round(net_income, 4),
    }


# --------------------------------------------------------------------------- #
# 3. 现金流量表 (Cash Flow Statement)
# --------------------------------------------------------------------------- #


async def cash_flow_statement(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    period: str,
) -> dict:
    """现金流量表 (简易版): 从 AR 收款 / AP 付款 / GL 现金科目变动推导。"""
    start, end = _period_range(period)

    # 经营活动: AR 收款
    ar_stmt = select(func.coalesce(func.sum(ARRecord.received_amount), 0)).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.created_at >= start,
    )
    ar_received = float((await session.execute(ar_stmt)).scalar() or 0)

    # 经营活动: AP 付款
    ap_stmt = select(func.coalesce(func.sum(APRecord.paid_amount), 0)).where(
        APRecord.tenant_id == tenant_id,
        APRecord.created_at >= start,
    )
    ap_paid = float((await session.execute(ap_stmt)).scalar() or 0)

    operating_net = ar_received - ap_paid

    # GL 现金类科目 (code 以 1001/1002 开头) 本期变动
    cash_codes = ("1001%", "1002%")
    posted_ids = (
        select(JournalEntry.id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.status == JournalStatus.POSTED,
            JournalEntry.entry_date >= start,
            JournalEntry.entry_date <= end,
        )
        .scalar_subquery()
    )
    cash_debit_stmt = select(
        func.coalesce(func.sum(JournalLine.debit_amount), 0)
    ).join(GLAccount, JournalLine.account_id == GLAccount.id).where(
        JournalLine.tenant_id == tenant_id,
        JournalLine.entry_id.in_(posted_ids),
        (GLAccount.code.like("1001%") | GLAccount.code.like("1002%")),
    )
    cash_credit_stmt = select(
        func.coalesce(func.sum(JournalLine.credit_amount), 0)
    ).join(GLAccount, JournalLine.account_id == GLAccount.id).where(
        JournalLine.tenant_id == tenant_id,
        JournalLine.entry_id.in_(posted_ids),
        (GLAccount.code.like("1001%") | GLAccount.code.like("1002%")),
    )

    cash_in = float((await session.execute(cash_debit_stmt)).scalar() or 0)
    cash_out = float((await session.execute(cash_credit_stmt)).scalar() or 0)
    gl_cash_change = cash_in - cash_out

    return {
        "title": "现金流量表",
        "period": period,
        "date_range": {"from": start.isoformat(), "to": end.isoformat()},
        "operating": {
            "ar_received": round(ar_received, 4),
            "ap_paid": round(ap_paid, 4),
            "net": round(operating_net, 4),
        },
        "gl_cash_movement": {
            "cash_in": round(cash_in, 4),
            "cash_out": round(cash_out, 4),
            "net_change": round(gl_cash_change, 4),
        },
        "net_cash_change": round(operating_net + gl_cash_change, 4),
    }


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #

STATEMENT_TYPES = {
    "balance_sheet": balance_sheet,
    "income": income_statement,
    "cash_flow": cash_flow_statement,
}


async def generate_statement(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    statement_type: str,
    period: str,
) -> dict:
    func_ = STATEMENT_TYPES.get(statement_type)
    if func_ is None:
        raise ValueError(
            f"未知报表类型: {statement_type}。可选: {', '.join(STATEMENT_TYPES)}"
        )
    return await func_(session, tenant_id=tenant_id, period=period)
