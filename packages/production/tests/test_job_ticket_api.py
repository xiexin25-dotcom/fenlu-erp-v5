"""TASK-MFG-004 · JobTicket report-back tests."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from packages.production.api.job_tickets import override_publisher
from packages.production.services.bom_client import PLM_BASE_URL
from packages.production.services.event_publisher import FakeEventPublisher


@pytest.fixture(autouse=True)
def _fake_publisher() -> FakeEventPublisher:
    pub = FakeEventPublisher()
    override_publisher(pub)
    return pub


def _bom_response(bom_id: str, product_id: str) -> dict:
    return {
        "id": bom_id,
        "product_id": product_id,
        "product_code": "P-001",
        "version": "1.0",
        "status": "approved",
        "items": [],
        "created_at": "2026-04-01T00:00:00Z",
        "updated_at": "2026-04-01T00:00:00Z",
    }


def _create_work_order(auth_client: TestClient, planned_qty: str = "100.0000") -> dict:
    payload = {
        "order_no": f"WO-{uuid4().hex[:8]}",
        "product_id": str(uuid4()),
        "bom_id": str(uuid4()),
        "routing_id": str(uuid4()),
        "planned_quantity": {"value": planned_qty, "uom": "pcs"},
        "planned_start": "2026-05-01T08:00:00Z",
        "planned_end": "2026-05-02T18:00:00Z",
    }
    r = auth_client.post("/mfg/work-orders", json=payload)
    assert r.status_code == 201
    return r.json()


def _release_work_order(auth_client: TestClient, wo: dict) -> None:
    """Release WO (requires BOM mock)."""
    respx.get(f"{PLM_BASE_URL}/plm/bom/{wo['bom_id']}").mock(
        return_value=Response(200, json=_bom_response(wo["bom_id"], wo["product_id"]))
    )
    r = auth_client.patch(
        f"/mfg/work-orders/{wo['id']}/status", json={"status": "released"}
    )
    assert r.status_code == 200
    # Move to in_progress so report-back makes sense
    r = auth_client.patch(
        f"/mfg/work-orders/{wo['id']}/status", json={"status": "in_progress"}
    )
    assert r.status_code == 200


@respx.mock
def test_create_and_report_job_ticket(
    auth_client: TestClient, _fake_publisher: FakeEventPublisher
) -> None:
    wo = _create_work_order(auth_client, "10.0000")
    _release_work_order(auth_client, wo)

    # Create ticket
    r = auth_client.post(
        "/mfg/job-tickets",
        json={"work_order_id": wo["id"], "ticket_no": "JT-0001"},
    )
    assert r.status_code == 201
    ticket = r.json()
    assert ticket["work_order_id"] == wo["id"]
    assert ticket["reported_at"] is None

    # Report
    r = auth_client.post(
        f"/mfg/job-tickets/{ticket['id']}/report",
        json={"completed_qty": "5.0000", "scrap_qty": "1.0000", "minutes": "30"},
    )
    assert r.status_code == 200
    data = r.json()
    assert Decimal(data["completed_qty"]) == Decimal("5.0000")
    assert data["reported_at"] is not None

    # Verify WO updated
    r = auth_client.get(f"/mfg/work-orders/{wo['id']}")
    wo_data = r.json()
    assert Decimal(wo_data["completed_quantity"]["value"]) == Decimal("5.0000")
    assert Decimal(wo_data["scrap_quantity"]["value"]) == Decimal("1.0000")

    # Not yet at planned qty → no event
    assert len(_fake_publisher.events) == 0


@respx.mock
def test_event_emitted_when_wo_completed(
    auth_client: TestClient, _fake_publisher: FakeEventPublisher
) -> None:
    wo = _create_work_order(auth_client, "10.0000")
    _release_work_order(auth_client, wo)

    # Create and report enough to reach planned_quantity
    r = auth_client.post(
        "/mfg/job-tickets",
        json={"work_order_id": wo["id"], "ticket_no": "JT-0001"},
    )
    ticket_id = r.json()["id"]
    r = auth_client.post(
        f"/mfg/job-tickets/{ticket_id}/report",
        json={"completed_qty": "10.0000", "scrap_qty": "0", "minutes": "60"},
    )
    assert r.status_code == 200

    # Event should be emitted
    assert len(_fake_publisher.events) == 1
    event = _fake_publisher.events[0]
    assert event.event_type == "work_order.completed"
    assert event.completed_quantity.value == Decimal("10.0000")
    assert event.actual_minutes == 60.0


@respx.mock
def test_double_report_rejected(auth_client: TestClient) -> None:
    wo = _create_work_order(auth_client)
    _release_work_order(auth_client, wo)

    r = auth_client.post(
        "/mfg/job-tickets",
        json={"work_order_id": wo["id"], "ticket_no": "JT-DUP"},
    )
    ticket_id = r.json()["id"]

    # First report OK
    r = auth_client.post(
        f"/mfg/job-tickets/{ticket_id}/report",
        json={"completed_qty": "5", "scrap_qty": "0", "minutes": "10"},
    )
    assert r.status_code == 200

    # Second report → 409
    r = auth_client.post(
        f"/mfg/job-tickets/{ticket_id}/report",
        json={"completed_qty": "5", "scrap_qty": "0", "minutes": "10"},
    )
    assert r.status_code == 409


@respx.mock
def test_list_job_tickets_by_work_order(auth_client: TestClient) -> None:
    wo = _create_work_order(auth_client)
    _release_work_order(auth_client, wo)

    auth_client.post(
        "/mfg/job-tickets",
        json={"work_order_id": wo["id"], "ticket_no": "JT-A"},
    )
    auth_client.post(
        "/mfg/job-tickets",
        json={"work_order_id": wo["id"], "ticket_no": "JT-B"},
    )

    r = auth_client.get(f"/mfg/job-tickets?work_order_id={wo['id']}")
    assert r.status_code == 200
    assert len(r.json()) == 2
