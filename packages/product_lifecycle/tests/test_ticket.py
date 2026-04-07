"""Tests for TASK-PLM-009: ServiceTicket with SLA timer + close with NPS."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest


def _create_customer(
    auth_client: Any, code: str = "TK-C", rating: str | None = "A",
) -> dict[str, Any]:
    r = auth_client.post(
        "/plm/customers",
        json={"code": code, "name": "Ticket Customer", "kind": "b2b", "rating": rating},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_ticket(
    auth_client: Any, customer_id: str, ticket_no: str = "TK-001",
) -> dict[str, Any]:
    r = auth_client.post(
        "/plm/service/tickets",
        json={"customer_id": customer_id, "ticket_no": ticket_no, "description": "Something broke"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _transition(auth_client: Any, ticket_id: str, target: str) -> Any:
    return auth_client.post(
        f"/plm/service/tickets/{ticket_id}/transition",
        json={"target_status": target},
    )


def _close(auth_client: Any, ticket_id: str, nps: int) -> Any:
    return auth_client.post(
        f"/plm/service/tickets/{ticket_id}/close",
        json={"nps_score": nps},
    )


# ── CRUD ──────────────────────────────────────────────────────────────────── #


class TestTicketCRUD:
    def test_create_ticket(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "TK-CR")
        ticket = _create_ticket(auth_client, cust["id"], "TK-CR-001")
        assert ticket["ticket_no"] == "TK-CR-001"
        assert ticket["status"] == "open"
        assert ticket["description"] == "Something broke"
        assert ticket["nps_score"] is None
        assert ticket["sla_due_at"] is not None

    def test_create_requires_auth(self, client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000001"
        r = client.post("/plm/service/tickets", json={"customer_id": fake, "ticket_no": "X"})
        assert r.status_code == 401

    def test_create_customer_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.post("/plm/service/tickets", json={"customer_id": fake, "ticket_no": "X"})
        assert r.status_code == 404

    def test_get_ticket(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "TK-GET")
        ticket = _create_ticket(auth_client, cust["id"], "TK-GET-001")
        r = auth_client.get(f"/plm/service/tickets/{ticket['id']}")
        assert r.status_code == 200
        assert r.json()["ticket_no"] == "TK-GET-001"

    def test_get_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.get(f"/plm/service/tickets/{fake}")
        assert r.status_code == 404


# ── SLA timer ─────────────────────────────────────────────────────────────── #


class TestSLATimer:
    def test_rating_a_4h(self, auth_client: Any) -> None:
        """A 级客户 SLA = 4 小时。"""
        cust = _create_customer(auth_client, "SLA-A", rating="A")
        ticket = _create_ticket(auth_client, cust["id"], "SLA-A-001")
        sla = datetime.fromisoformat(ticket["sla_due_at"])
        now = datetime.now(timezone.utc)
        diff = sla - now
        # 应在 3.5h ~ 4.5h 之间 (允许测试执行时间误差)
        assert timedelta(hours=3, minutes=30) < diff < timedelta(hours=4, minutes=30)

    def test_rating_b_8h(self, auth_client: Any) -> None:
        """B 级客户 SLA = 8 小时。"""
        cust = _create_customer(auth_client, "SLA-B", rating="B")
        ticket = _create_ticket(auth_client, cust["id"], "SLA-B-001")
        sla = datetime.fromisoformat(ticket["sla_due_at"])
        now = datetime.now(timezone.utc)
        diff = sla - now
        assert timedelta(hours=7, minutes=30) < diff < timedelta(hours=8, minutes=30)

    def test_rating_c_24h(self, auth_client: Any) -> None:
        """C 级客户 SLA = 24 小时。"""
        cust = _create_customer(auth_client, "SLA-C", rating="C")
        ticket = _create_ticket(auth_client, cust["id"], "SLA-C-001")
        sla = datetime.fromisoformat(ticket["sla_due_at"])
        now = datetime.now(timezone.utc)
        diff = sla - now
        assert timedelta(hours=23, minutes=30) < diff < timedelta(hours=24, minutes=30)

    def test_no_rating_default_24h(self, auth_client: Any) -> None:
        """无评级客户默认 SLA = 24 小时。"""
        cust = _create_customer(auth_client, "SLA-NONE", rating=None)
        ticket = _create_ticket(auth_client, cust["id"], "SLA-NONE-001")
        sla = datetime.fromisoformat(ticket["sla_due_at"])
        now = datetime.now(timezone.utc)
        diff = sla - now
        assert timedelta(hours=23, minutes=30) < diff < timedelta(hours=24, minutes=30)


# ── Status transitions ────────────────────────────────────────────────────── #


class TestTicketTransitions:
    def test_happy_path(self, auth_client: Any) -> None:
        """open → in_progress → resolved → closed (via /close)"""
        cust = _create_customer(auth_client, "TK-HP")
        ticket = _create_ticket(auth_client, cust["id"], "TK-HP-001")
        tid = ticket["id"]

        r = _transition(auth_client, tid, "in_progress")
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

        r = _transition(auth_client, tid, "resolved")
        assert r.status_code == 200
        assert r.json()["status"] == "resolved"

        # close via /close endpoint (requires NPS)
        r = _close(auth_client, tid, 8)
        assert r.status_code == 200
        assert r.json()["status"] == "closed"
        assert r.json()["nps_score"] == 8

    def test_pending_customer(self, auth_client: Any) -> None:
        """in_progress → pending_customer → in_progress"""
        cust = _create_customer(auth_client, "TK-PEND")
        ticket = _create_ticket(auth_client, cust["id"], "TK-PEND-001")
        tid = ticket["id"]

        _transition(auth_client, tid, "in_progress")
        r = _transition(auth_client, tid, "pending_customer")
        assert r.status_code == 200
        r = _transition(auth_client, tid, "in_progress")
        assert r.status_code == 200

    def test_reopen_from_resolved(self, auth_client: Any) -> None:
        """resolved → in_progress (reopen)"""
        cust = _create_customer(auth_client, "TK-REOPEN")
        ticket = _create_ticket(auth_client, cust["id"], "TK-REOPEN-001")
        tid = ticket["id"]

        _transition(auth_client, tid, "in_progress")
        _transition(auth_client, tid, "resolved")
        r = _transition(auth_client, tid, "in_progress")
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_invalid_transition(self, auth_client: Any) -> None:
        """open 不能直接 resolved。"""
        cust = _create_customer(auth_client, "TK-INV")
        ticket = _create_ticket(auth_client, cust["id"], "TK-INV-001")
        r = _transition(auth_client, ticket["id"], "resolved")
        assert r.status_code == 422

    def test_closed_is_terminal(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "TK-TERM")
        ticket = _create_ticket(auth_client, cust["id"], "TK-TERM-001")
        r = _close(auth_client, ticket["id"], 5)
        assert r.status_code == 200
        r = _transition(auth_client, ticket["id"], "in_progress")
        assert r.status_code == 422

    def test_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = _transition(auth_client, fake, "in_progress")
        assert r.status_code == 404


# ── Close with NPS ────────────────────────────────────────────────────────── #


class TestCloseWithNPS:
    def test_close_from_open(self, auth_client: Any) -> None:
        """open → closed 直接关闭(快速解决)。"""
        cust = _create_customer(auth_client, "TK-CLO")
        ticket = _create_ticket(auth_client, cust["id"], "TK-CLO-001")
        r = _close(auth_client, ticket["id"], 10)
        assert r.status_code == 200
        assert r.json()["nps_score"] == 10
        assert r.json()["status"] == "closed"

    def test_close_from_resolved(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "TK-CLR")
        ticket = _create_ticket(auth_client, cust["id"], "TK-CLR-001")
        tid = ticket["id"]
        _transition(auth_client, tid, "in_progress")
        _transition(auth_client, tid, "resolved")
        r = _close(auth_client, tid, 7)
        assert r.status_code == 200
        assert r.json()["nps_score"] == 7

    def test_close_requires_nps(self, auth_client: Any) -> None:
        """不传 nps_score 应 422。"""
        cust = _create_customer(auth_client, "TK-NPS-REQ")
        ticket = _create_ticket(auth_client, cust["id"], "TK-NPS-001")
        r = auth_client.post(
            f"/plm/service/tickets/{ticket['id']}/close",
            json={},
        )
        assert r.status_code == 422

    def test_nps_out_of_range(self, auth_client: Any) -> None:
        """nps_score > 10 应 422。"""
        cust = _create_customer(auth_client, "TK-NPS-RNG")
        ticket = _create_ticket(auth_client, cust["id"], "TK-NPS-RNG-001")
        r = _close(auth_client, ticket["id"], 11)
        assert r.status_code == 422

    def test_nps_negative(self, auth_client: Any) -> None:
        """nps_score < 0 应 422。"""
        cust = _create_customer(auth_client, "TK-NPS-NEG")
        ticket = _create_ticket(auth_client, cust["id"], "TK-NPS-NEG-001")
        r = _close(auth_client, ticket["id"], -1)
        assert r.status_code == 422

    def test_close_not_from_in_progress(self, auth_client: Any) -> None:
        """in_progress 不能直接 close (需先 resolved)。"""
        cust = _create_customer(auth_client, "TK-NIP")
        ticket = _create_ticket(auth_client, cust["id"], "TK-NIP-001")
        _transition(auth_client, ticket["id"], "in_progress")
        r = _close(auth_client, ticket["id"], 5)
        assert r.status_code == 422

    def test_close_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = _close(auth_client, fake, 5)
        assert r.status_code == 404
