"""Tests for GL accounts + journal entries (TASK-MGMT-001)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from packages.management_decision.api.schemas import JournalEntryCreate, JournalLineIn


# --------------------------------------------------------------------------- #
# Schema-level validation (double-entry balance)
# --------------------------------------------------------------------------- #


class TestJournalEntrySchema:
    """Pydantic 层借贷平衡校验。"""

    def test_balanced_entry_ok(self) -> None:
        entry = JournalEntryCreate(
            entry_date="2026-04-06",
            memo="test",
            lines=[
                JournalLineIn(
                    account_id="00000000-0000-0000-0000-000000000001",
                    debit_amount=Decimal("100.0000"),
                ),
                JournalLineIn(
                    account_id="00000000-0000-0000-0000-000000000002",
                    credit_amount=Decimal("100.0000"),
                ),
            ],
        )
        assert len(entry.lines) == 2

    def test_unbalanced_entry_rejected(self) -> None:
        with pytest.raises(ValueError, match="借贷不平衡"):
            JournalEntryCreate(
                entry_date="2026-04-06",
                lines=[
                    JournalLineIn(
                        account_id="00000000-0000-0000-0000-000000000001",
                        debit_amount=Decimal("100.0000"),
                    ),
                    JournalLineIn(
                        account_id="00000000-0000-0000-0000-000000000002",
                        credit_amount=Decimal("50.0000"),
                    ),
                ],
            )

    def test_line_both_sides_rejected(self) -> None:
        with pytest.raises(ValueError, match="不能同时非零"):
            JournalLineIn(
                account_id="00000000-0000-0000-0000-000000000001",
                debit_amount=Decimal("100"),
                credit_amount=Decimal("100"),
            )

    def test_line_both_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="不能同时为零"):
            JournalLineIn(
                account_id="00000000-0000-0000-0000-000000000001",
                debit_amount=Decimal("0"),
                credit_amount=Decimal("0"),
            )

    def test_minimum_two_lines(self) -> None:
        with pytest.raises(ValueError):
            JournalEntryCreate(
                entry_date="2026-04-06",
                lines=[
                    JournalLineIn(
                        account_id="00000000-0000-0000-0000-000000000001",
                        debit_amount=Decimal("100"),
                    ),
                ],
            )


# --------------------------------------------------------------------------- #
# API integration tests
# --------------------------------------------------------------------------- #


class TestGLAccountAPI:
    def test_create_account(self, auth_client: TestClient) -> None:
        r = auth_client.post(
            "/mgmt/finance/accounts",
            json={
                "code": "1001",
                "name": "库存现金",
                "account_type": "asset",
                "level": 1,
            },
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["code"] == "1001"
        assert data["account_type"] == "asset"
        assert data["is_active"] is True

    def test_list_accounts(self, auth_client: TestClient) -> None:
        # create two accounts
        auth_client.post(
            "/mgmt/finance/accounts",
            json={"code": "1001", "name": "库存现金", "account_type": "asset"},
        )
        auth_client.post(
            "/mgmt/finance/accounts",
            json={"code": "6001", "name": "收入", "account_type": "revenue"},
        )
        r = auth_client.get("/mgmt/finance/accounts")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_list_accounts_filter_type(self, auth_client: TestClient) -> None:
        auth_client.post(
            "/mgmt/finance/accounts",
            json={"code": "1001", "name": "现金", "account_type": "asset"},
        )
        auth_client.post(
            "/mgmt/finance/accounts",
            json={"code": "6001", "name": "收入", "account_type": "revenue"},
        )
        r = auth_client.get("/mgmt/finance/accounts", params={"account_type": "asset"})
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["account_type"] == "asset"

    def test_get_account_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get("/mgmt/finance/accounts/00000000-0000-0000-0000-000000000099")
        assert r.status_code == 404


class TestJournalAPI:
    def test_create_balanced_journal(
        self, auth_client: TestClient, seed_gl_accounts: dict[str, Any]
    ) -> None:
        cash_id = str(seed_gl_accounts["cash_id"])
        revenue_id = str(seed_gl_accounts["revenue_id"])
        r = auth_client.post(
            "/mgmt/finance/journal",
            json={
                "entry_date": "2026-04-06",
                "memo": "销售收款",
                "lines": [
                    {"account_id": cash_id, "debit_amount": "1000.0000"},
                    {"account_id": revenue_id, "credit_amount": "1000.0000"},
                ],
            },
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["entry_no"].startswith("JV-202604-")
        assert data["status"] == "draft"
        assert len(data["lines"]) == 2

    def test_create_unbalanced_journal_422(
        self, auth_client: TestClient, seed_gl_accounts: dict[str, Any]
    ) -> None:
        cash_id = str(seed_gl_accounts["cash_id"])
        revenue_id = str(seed_gl_accounts["revenue_id"])
        r = auth_client.post(
            "/mgmt/finance/journal",
            json={
                "entry_date": "2026-04-06",
                "lines": [
                    {"account_id": cash_id, "debit_amount": "1000.0000"},
                    {"account_id": revenue_id, "credit_amount": "500.0000"},
                ],
            },
        )
        assert r.status_code == 422

    def test_post_journal(
        self, auth_client: TestClient, seed_gl_accounts: dict[str, Any]
    ) -> None:
        cash_id = str(seed_gl_accounts["cash_id"])
        revenue_id = str(seed_gl_accounts["revenue_id"])
        # create
        r = auth_client.post(
            "/mgmt/finance/journal",
            json={
                "entry_date": "2026-04-06",
                "memo": "test",
                "lines": [
                    {"account_id": cash_id, "debit_amount": "500.0000"},
                    {"account_id": revenue_id, "credit_amount": "500.0000"},
                ],
            },
        )
        entry_id = r.json()["id"]
        # post it
        r2 = auth_client.post(f"/mgmt/finance/journal/{entry_id}/post")
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "posted"

    def test_list_and_get_journal(
        self, auth_client: TestClient, seed_gl_accounts: dict[str, Any]
    ) -> None:
        cash_id = str(seed_gl_accounts["cash_id"])
        revenue_id = str(seed_gl_accounts["revenue_id"])
        r = auth_client.post(
            "/mgmt/finance/journal",
            json={
                "entry_date": "2026-04-06",
                "memo": "test",
                "lines": [
                    {"account_id": cash_id, "debit_amount": "200.0000"},
                    {"account_id": revenue_id, "credit_amount": "200.0000"},
                ],
            },
        )
        entry_id = r.json()["id"]

        # list
        r2 = auth_client.get("/mgmt/finance/journal")
        assert r2.status_code == 200
        assert len(r2.json()) >= 1

        # get single
        r3 = auth_client.get(f"/mgmt/finance/journal/{entry_id}")
        assert r3.status_code == 200
        assert r3.json()["id"] == entry_id
