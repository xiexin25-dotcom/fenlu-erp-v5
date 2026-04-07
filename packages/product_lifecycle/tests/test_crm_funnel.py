"""Tests for TASK-PLM-007: Lead/Opportunity stage transitions + funnel."""

from __future__ import annotations

from typing import Any

import pytest


def _create_customer(auth_client: Any, code: str = "FNL-C") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/customers",
        json={"code": code, "name": "Funnel Customer", "kind": "b2b"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_lead(auth_client: Any, customer_id: str, title: str = "Lead X") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/crm/leads",
        json={"customer_id": customer_id, "title": title, "source": "web"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_opp(auth_client: Any, customer_id: str, title: str = "Opp X") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/crm/opportunities",
        json={"customer_id": customer_id, "title": title, "expected_amount": "50000.0000"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Lead ──────────────────────────────────────────────────────────────────── #


class TestLeadCRUD:
    def test_create_lead(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "LD-CR")
        lead = _create_lead(auth_client, cust["id"], "New lead")
        assert lead["status"] == "new"
        assert lead["title"] == "New lead"
        assert lead["source"] == "web"

    def test_create_requires_auth(self, client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000001"
        r = client.post("/plm/crm/leads", json={"customer_id": fake, "title": "X"})
        assert r.status_code == 401


class TestLeadTransitions:
    def test_happy_path(self, auth_client: Any) -> None:
        """new → contacted → qualified → converted"""
        cust = _create_customer(auth_client, "LD-HP")
        lead = _create_lead(auth_client, cust["id"])
        lid = lead["id"]

        for target, expected in [
            ("contacted", "contacted"),
            ("qualified", "qualified"),
            ("converted", "converted"),
        ]:
            r = auth_client.post(f"/plm/crm/leads/{lid}/transition", json={"target_status": target})
            assert r.status_code == 200, r.text
            assert r.json()["status"] == expected

    def test_disqualify_from_new(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "LD-DQ")
        lead = _create_lead(auth_client, cust["id"])
        r = auth_client.post(
            f"/plm/crm/leads/{lead['id']}/transition",
            json={"target_status": "disqualified"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "disqualified"

    def test_invalid_transition(self, auth_client: Any) -> None:
        """new 不能直接跳 qualified。"""
        cust = _create_customer(auth_client, "LD-INV")
        lead = _create_lead(auth_client, cust["id"])
        r = auth_client.post(
            f"/plm/crm/leads/{lead['id']}/transition",
            json={"target_status": "qualified"},
        )
        assert r.status_code == 422

    def test_terminal_state(self, auth_client: Any) -> None:
        """converted 是终态。"""
        cust = _create_customer(auth_client, "LD-TRM")
        lead = _create_lead(auth_client, cust["id"])
        lid = lead["id"]
        auth_client.post(f"/plm/crm/leads/{lid}/transition", json={"target_status": "contacted"})
        auth_client.post(f"/plm/crm/leads/{lid}/transition", json={"target_status": "qualified"})
        auth_client.post(f"/plm/crm/leads/{lid}/transition", json={"target_status": "converted"})
        r = auth_client.post(f"/plm/crm/leads/{lid}/transition", json={"target_status": "new"})
        assert r.status_code == 422

    def test_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.post(f"/plm/crm/leads/{fake}/transition", json={"target_status": "contacted"})
        assert r.status_code == 404


# ── Opportunity ───────────────────────────────────────────────────────────── #


class TestOpportunityCRUD:
    def test_create_opportunity(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "OP-CR")
        opp = _create_opp(auth_client, cust["id"], "Big deal")
        assert opp["stage"] == "qualification"
        assert opp["title"] == "Big deal"

    def test_create_requires_auth(self, client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000001"
        r = client.post("/plm/crm/opportunities", json={"customer_id": fake, "title": "X"})
        assert r.status_code == 401


class TestOpportunityTransitions:
    def test_happy_path_won(self, auth_client: Any) -> None:
        """qualification → proposal → negotiation → closed_won"""
        cust = _create_customer(auth_client, "OP-WON")
        opp = _create_opp(auth_client, cust["id"])
        oid = opp["id"]

        for target, expected in [
            ("proposal", "proposal"),
            ("negotiation", "negotiation"),
            ("closed_won", "closed_won"),
        ]:
            r = auth_client.post(f"/plm/crm/opportunities/{oid}/transition", json={"target_stage": target})
            assert r.status_code == 200, r.text
            assert r.json()["stage"] == expected

    def test_lost_from_any_stage(self, auth_client: Any) -> None:
        """可以从任何非终态直接 closed_lost。"""
        cust = _create_customer(auth_client, "OP-LOST")
        opp = _create_opp(auth_client, cust["id"])
        r = auth_client.post(
            f"/plm/crm/opportunities/{opp['id']}/transition",
            json={"target_stage": "closed_lost"},
        )
        assert r.status_code == 200
        assert r.json()["stage"] == "closed_lost"

    def test_invalid_transition(self, auth_client: Any) -> None:
        """qualification 不能直接 negotiation。"""
        cust = _create_customer(auth_client, "OP-INV")
        opp = _create_opp(auth_client, cust["id"])
        r = auth_client.post(
            f"/plm/crm/opportunities/{opp['id']}/transition",
            json={"target_stage": "negotiation"},
        )
        assert r.status_code == 422

    def test_terminal_state(self, auth_client: Any) -> None:
        """closed_won 是终态。"""
        cust = _create_customer(auth_client, "OP-TRM")
        opp = _create_opp(auth_client, cust["id"])
        oid = opp["id"]
        auth_client.post(f"/plm/crm/opportunities/{oid}/transition", json={"target_stage": "proposal"})
        auth_client.post(f"/plm/crm/opportunities/{oid}/transition", json={"target_stage": "negotiation"})
        auth_client.post(f"/plm/crm/opportunities/{oid}/transition", json={"target_stage": "closed_won"})
        r = auth_client.post(f"/plm/crm/opportunities/{oid}/transition", json={"target_stage": "qualification"})
        assert r.status_code == 422


# ── Funnel ────────────────────────────────────────────────────────────────── #


class TestFunnel:
    def test_empty_funnel(self, auth_client: Any) -> None:
        r = auth_client.get("/plm/crm/funnel")
        assert r.status_code == 200
        data = r.json()
        assert data["leads"] == {}
        assert data["opportunities"] == {}

    def test_funnel_counts(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "FNL-CNT")
        cid = cust["id"]

        # 3 leads: 2 new, 1 contacted
        _create_lead(auth_client, cid, "L1")
        _create_lead(auth_client, cid, "L2")
        l3 = _create_lead(auth_client, cid, "L3")
        auth_client.post(f"/plm/crm/leads/{l3['id']}/transition", json={"target_status": "contacted"})

        # 2 opps: 1 qualification, 1 proposal
        _create_opp(auth_client, cid, "O1")
        o2 = _create_opp(auth_client, cid, "O2")
        auth_client.post(f"/plm/crm/opportunities/{o2['id']}/transition", json={"target_stage": "proposal"})

        r = auth_client.get("/plm/crm/funnel")
        assert r.status_code == 200
        data = r.json()
        assert data["leads"]["new"] == 2
        assert data["leads"]["contacted"] == 1
        assert data["opportunities"]["qualification"] == 1
        assert data["opportunities"]["proposal"] == 1

    def test_funnel_with_period(self, auth_client: Any) -> None:
        """period 参数过滤 created_at 范围。"""
        cust = _create_customer(auth_client, "FNL-PER")
        _create_lead(auth_client, cust["id"], "Recent lead")

        # Very wide period → should include everything
        r = auth_client.get("/plm/crm/funnel?period_start=2020-01-01T00:00:00&period_end=2030-12-31T23:59:59")
        assert r.status_code == 200
        assert r.json()["leads"].get("new", 0) >= 1

        # Future period → should be empty
        r = auth_client.get("/plm/crm/funnel?period_start=2099-01-01T00:00:00&period_end=2099-12-31T23:59:59")
        assert r.status_code == 200
        assert r.json()["leads"] == {}
