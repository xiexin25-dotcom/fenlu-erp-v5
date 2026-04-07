"""Tests for three financial statements (TASK-MGMT-011).

Seed GL accounts + posted journal entries, then verify balance sheet,
income statement, and cash flow statement outputs.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.ap_ar import APRecord, APStatus, ARRecord
from packages.management_decision.models.finance import (
    AccountType,
    GLAccount,
    JournalEntry,
    JournalLine,
    JournalStatus,
)


# --------------------------------------------------------------------------- #
# Seed helpers
# --------------------------------------------------------------------------- #


async def _seed_chart_of_accounts(session: AsyncSession, tid: Any) -> dict[str, Any]:
    """创建标准科目表,返回科目 ID map。"""
    accounts = {
        "1001": ("库存现金", AccountType.ASSET),
        "1002": ("银行存款", AccountType.ASSET),
        "1100": ("应收账款", AccountType.ASSET),
        "2001": ("短期借款", AccountType.LIABILITY),
        "2100": ("应付账款", AccountType.LIABILITY),
        "3001": ("实收资本", AccountType.EQUITY),
        "6001": ("主营业务收入", AccountType.REVENUE),
        "6002": ("其他业务收入", AccountType.REVENUE),
        "6601": ("管理费用", AccountType.EXPENSE),
        "6602": ("销售费用", AccountType.EXPENSE),
    }
    ids = {}
    for code, (name, acct_type) in accounts.items():
        acct = GLAccount(
            id=uuid4(), tenant_id=tid, code=code, name=name,
            account_type=acct_type, level=1,
        )
        session.add(acct)
        ids[code] = acct.id
    await session.flush()
    return ids


async def _post_journal(
    session: AsyncSession,
    tid: Any,
    entry_date: date,
    lines: list[tuple[Any, str, str]],
) -> JournalEntry:
    """创建并过账凭证。lines: [(account_id, debit, credit), ...]"""
    entry = JournalEntry(
        id=uuid4(), tenant_id=tid,
        entry_no=f"JV-{uuid4().hex[:8]}",
        entry_date=entry_date,
        status=JournalStatus.POSTED,
    )
    session.add(entry)
    for i, (acct_id, debit, credit) in enumerate(lines, 1):
        session.add(JournalLine(
            id=uuid4(), tenant_id=tid, entry_id=entry.id,
            line_no=i, account_id=acct_id,
            debit_amount=Decimal(debit), credit_amount=Decimal(credit),
        ))
    await session.flush()
    return entry


# --------------------------------------------------------------------------- #
# Balance Sheet
# --------------------------------------------------------------------------- #


class TestBalanceSheet:
    @pytest.mark.asyncio
    async def test_balance_sheet_balanced(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        """资产 = 负债 + 权益 (含留存收益)。"""
        from packages.management_decision.services.statements import balance_sheet

        tid = seed_admin["tenant_id"]
        accts = await _seed_chart_of_accounts(db_session, tid)

        # 投入资本: 借 银行存款 100000, 贷 实收资本 100000
        await _post_journal(db_session, tid, date(2026, 4, 1), [
            (accts["1002"], "100000", "0"),
            (accts["3001"], "0", "100000"),
        ])
        # 销售收入: 借 应收账款 50000, 贷 主营业务收入 50000
        await _post_journal(db_session, tid, date(2026, 4, 5), [
            (accts["1100"], "50000", "0"),
            (accts["6001"], "0", "50000"),
        ])
        # 付管理费用: 借 管理费用 8000, 贷 银行存款 8000
        await _post_journal(db_session, tid, date(2026, 4, 10), [
            (accts["6601"], "8000", "0"),
            (accts["1002"], "0", "8000"),
        ])
        await db_session.commit()

        bs = await balance_sheet(db_session, tenant_id=tid, period="2026-04")

        assert bs["title"] == "资产负债表"
        assert bs["period"] == "2026-04"

        # Assets: 银行 92000 + 应收 50000 = 142000
        assert bs["assets"]["total"] == 142000.0

        # Liabilities: 0
        assert bs["liabilities"]["total"] == 0.0

        # Equity: 实收资本 100000 + 留存 (50000-8000=42000) = 142000
        assert bs["equity"]["retained_earnings"] == 42000.0
        assert bs["equity"]["total"] == 142000.0

        # Balanced check
        assert bs["balanced"] is True
        assert bs["liabilities_and_equity"] == 142000.0

    @pytest.mark.asyncio
    async def test_balance_sheet_with_liabilities(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.statements import balance_sheet

        tid = seed_admin["tenant_id"]
        accts = await _seed_chart_of_accounts(db_session, tid)

        # 借款: 借 银行存款 200000, 贷 短期借款 200000
        await _post_journal(db_session, tid, date(2026, 4, 1), [
            (accts["1002"], "200000", "0"),
            (accts["2001"], "0", "200000"),
        ])
        await db_session.commit()

        bs = await balance_sheet(db_session, tenant_id=tid, period="2026-04")
        assert bs["assets"]["total"] == 200000.0
        assert bs["liabilities"]["total"] == 200000.0
        assert bs["balanced"] is True


# --------------------------------------------------------------------------- #
# Income Statement
# --------------------------------------------------------------------------- #


class TestIncomeStatement:
    @pytest.mark.asyncio
    async def test_income_statement(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.statements import income_statement

        tid = seed_admin["tenant_id"]
        accts = await _seed_chart_of_accounts(db_session, tid)

        # 收入 80000
        await _post_journal(db_session, tid, date(2026, 4, 5), [
            (accts["1002"], "80000", "0"),
            (accts["6001"], "0", "80000"),
        ])
        # 其他收入 5000
        await _post_journal(db_session, tid, date(2026, 4, 8), [
            (accts["1001"], "5000", "0"),
            (accts["6002"], "0", "5000"),
        ])
        # 管理费用 12000
        await _post_journal(db_session, tid, date(2026, 4, 10), [
            (accts["6601"], "12000", "0"),
            (accts["1002"], "0", "12000"),
        ])
        # 销售费用 3000
        await _post_journal(db_session, tid, date(2026, 4, 12), [
            (accts["6602"], "3000", "0"),
            (accts["1001"], "0", "3000"),
        ])
        await db_session.commit()

        inc = await income_statement(db_session, tenant_id=tid, period="2026-04")

        assert inc["title"] == "利润表"
        assert inc["revenue"]["total"] == 85000.0  # 80000 + 5000
        assert inc["expenses"]["total"] == 15000.0  # 12000 + 3000
        assert inc["net_income"] == 70000.0

    @pytest.mark.asyncio
    async def test_income_excludes_other_periods(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        """3 月的凭证不应出现在 4 月利润表。"""
        from packages.management_decision.services.statements import income_statement

        tid = seed_admin["tenant_id"]
        accts = await _seed_chart_of_accounts(db_session, tid)

        # 3月收入
        await _post_journal(db_session, tid, date(2026, 3, 15), [
            (accts["1002"], "20000", "0"),
            (accts["6001"], "0", "20000"),
        ])
        # 4月收入
        await _post_journal(db_session, tid, date(2026, 4, 15), [
            (accts["1002"], "30000", "0"),
            (accts["6001"], "0", "30000"),
        ])
        await db_session.commit()

        inc = await income_statement(db_session, tenant_id=tid, period="2026-04")
        assert inc["revenue"]["total"] == 30000.0  # only April


# --------------------------------------------------------------------------- #
# Cash Flow Statement
# --------------------------------------------------------------------------- #


class TestCashFlowStatement:
    @pytest.mark.asyncio
    async def test_cash_flow_from_gl(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.statements import cash_flow_statement

        tid = seed_admin["tenant_id"]
        accts = await _seed_chart_of_accounts(db_session, tid)

        # 收到现金: 借 银行存款 50000, 贷 主营收入 50000
        await _post_journal(db_session, tid, date(2026, 4, 5), [
            (accts["1002"], "50000", "0"),
            (accts["6001"], "0", "50000"),
        ])
        # 付费用: 借 管理费用 10000, 贷 银行存款 10000
        await _post_journal(db_session, tid, date(2026, 4, 10), [
            (accts["6601"], "10000", "0"),
            (accts["1002"], "0", "10000"),
        ])
        await db_session.commit()

        cf = await cash_flow_statement(db_session, tenant_id=tid, period="2026-04")

        assert cf["title"] == "现金流量表"
        # GL cash movement: in=50000, out=10000, net=40000
        assert cf["gl_cash_movement"]["cash_in"] == 50000.0
        assert cf["gl_cash_movement"]["cash_out"] == 10000.0
        assert cf["gl_cash_movement"]["net_change"] == 40000.0

    @pytest.mark.asyncio
    async def test_cash_flow_from_ar_ap(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.statements import cash_flow_statement

        tid = seed_admin["tenant_id"]
        # AR with received
        db_session.add(ARRecord(
            id=uuid4(), tenant_id=tid, sales_order_id=uuid4(),
            customer_id=uuid4(), total_amount=Decimal("80000"),
            received_amount=Decimal("60000"), currency="CNY",
            due_date=date(2026, 5, 1), status=APStatus.PARTIAL,
        ))
        # AP with paid
        db_session.add(APRecord(
            id=uuid4(), tenant_id=tid, purchase_order_id=uuid4(),
            supplier_id=uuid4(), total_amount=Decimal("40000"),
            paid_amount=Decimal("25000"), currency="CNY",
            due_date=date(2026, 5, 1), status=APStatus.PARTIAL,
        ))
        await db_session.commit()

        cf = await cash_flow_statement(db_session, tenant_id=tid, period="2026-04")
        assert cf["operating"]["ar_received"] == 60000.0
        assert cf["operating"]["ap_paid"] == 25000.0
        assert cf["operating"]["net"] == 35000.0


# --------------------------------------------------------------------------- #
# API endpoints
# --------------------------------------------------------------------------- #


class TestStatementsAPI:
    def test_balance_sheet_endpoint(self, auth_client: TestClient) -> None:
        r = auth_client.get(
            "/mgmt/finance/statements/balance_sheet",
            params={"period": "2026-04"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["title"] == "资产负债表"
        assert "assets" in data
        assert "liabilities" in data
        assert "equity" in data

    def test_income_endpoint(self, auth_client: TestClient) -> None:
        r = auth_client.get(
            "/mgmt/finance/statements/income",
            params={"period": "2026-04"},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "利润表"

    def test_cash_flow_endpoint(self, auth_client: TestClient) -> None:
        r = auth_client.get(
            "/mgmt/finance/statements/cash_flow",
            params={"period": "2026-04"},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "现金流量表"

    def test_unknown_type_422(self, auth_client: TestClient) -> None:
        r = auth_client.get(
            "/mgmt/finance/statements/unknown",
            params={"period": "2026-04"},
        )
        assert r.status_code == 422

    def test_bad_period_422(self, auth_client: TestClient) -> None:
        r = auth_client.get(
            "/mgmt/finance/statements/income",
            params={"period": "202604"},
        )
        assert r.status_code == 422

    def test_empty_data_returns_zeros(self, auth_client: TestClient) -> None:
        r = auth_client.get(
            "/mgmt/finance/statements/income",
            params={"period": "2026-04"},
        )
        data = r.json()
        assert data["revenue"]["total"] == 0
        assert data["expenses"]["total"] == 0
        assert data["net_income"] == 0
