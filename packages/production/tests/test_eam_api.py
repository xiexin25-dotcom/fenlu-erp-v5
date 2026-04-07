"""TASK-MFG-007 · EAM (Equipment Asset Management) tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from packages.production.api.job_tickets import override_publisher
from packages.production.services.event_publisher import FakeEventPublisher


@pytest.fixture(autouse=True)
def _fake_publisher() -> FakeEventPublisher:
    pub = FakeEventPublisher()
    override_publisher(pub)
    return pub


def _create_equipment(auth_client: TestClient) -> dict:
    r = auth_client.post(
        "/mfg/equipment",
        json={
            "code": f"EQ-{uuid4().hex[:6]}",
            "name": "CNC Lathe #1",
            "workshop_id": str(uuid4()),
        },
    )
    assert r.status_code == 201
    return r.json()


def test_create_and_get_equipment(auth_client: TestClient) -> None:
    eq = _create_equipment(auth_client)
    assert eq["status"] == "idle"

    r = auth_client.get(f"/mfg/equipment/{eq['id']}")
    assert r.status_code == 200
    assert r.json()["code"] == eq["code"]


def test_list_equipment(auth_client: TestClient) -> None:
    _create_equipment(auth_client)
    _create_equipment(auth_client)
    r = auth_client.get("/mfg/equipment")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_fault_record_emits_event(
    auth_client: TestClient, _fake_publisher: FakeEventPublisher
) -> None:
    eq = _create_equipment(auth_client)

    r = auth_client.post(
        f"/mfg/equipment/{eq['id']}/faults",
        json={
            "fault_code": "F-001",
            "severity": "major",
            "description": "Spindle overheating",
            "started_at": "2026-05-01T10:00:00Z",
        },
    )
    assert r.status_code == 201
    fault = r.json()
    assert fault["fault_code"] == "F-001"

    # Equipment status should be updated to fault
    r = auth_client.get(f"/mfg/equipment/{eq['id']}")
    assert r.json()["status"] == "fault"

    # Event emitted
    assert len(_fake_publisher.events) == 1
    assert _fake_publisher.events[0].event_type == "equipment.fault"


def test_list_faults(auth_client: TestClient) -> None:
    eq = _create_equipment(auth_client)
    auth_client.post(
        f"/mfg/equipment/{eq['id']}/faults",
        json={
            "fault_code": "F-001",
            "severity": "minor",
            "started_at": "2026-05-01T10:00:00Z",
        },
    )
    r = auth_client.get(f"/mfg/equipment/{eq['id']}/faults")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_maintenance_plan_and_generate(auth_client: TestClient) -> None:
    eq = _create_equipment(auth_client)

    # Create plan with interval 1 day (so it's due immediately)
    r = auth_client.post(
        "/mfg/maintenance/plans",
        json={
            "equipment_id": eq["id"],
            "name": "Weekly lubrication",
            "interval_days": 1,
        },
    )
    assert r.status_code == 201
    plan = r.json()
    assert plan["last_generated"] is None

    # Trigger generation
    r = auth_client.post("/mfg/maintenance/generate")
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) >= 1
    assert any(log["equipment_id"] == eq["id"] for log in logs)

    # Trigger again — should NOT generate (last_generated = today, interval = 1)
    r = auth_client.post("/mfg/maintenance/generate")
    assert r.status_code == 200
    assert len(r.json()) == 0  # nothing new
