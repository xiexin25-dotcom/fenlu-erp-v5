"""TASK-MFG-008 · OEE endpoint integration test."""

from __future__ import annotations

from datetime import date
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


def test_oee_endpoint_no_data(auth_client: TestClient) -> None:
    """Equipment exists but no production data → OEE = 0."""
    eq = auth_client.post(
        "/mfg/equipment",
        json={
            "code": "EQ-OEE-1",
            "name": "Test Machine",
            "workshop_id": str(uuid4()),
        },
    ).json()

    r = auth_client.get(
        f"/mfg/equipment/{eq['id']}/oee",
        params={"target_date": str(date.today())},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["equipment_id"] == eq["id"]
    assert data["oee"] == 0.0
    assert data["availability"] == 1.0  # no faults → full availability


def test_oee_endpoint_with_fault(auth_client: TestClient) -> None:
    """Equipment with a fault record → availability < 1."""
    eq = auth_client.post(
        "/mfg/equipment",
        json={
            "code": "EQ-OEE-2",
            "name": "Test Machine 2",
            "workshop_id": str(uuid4()),
        },
    ).json()

    today = str(date.today())
    # Add a 2-hour fault today
    auth_client.post(
        f"/mfg/equipment/{eq['id']}/faults",
        json={
            "fault_code": "F-OEE",
            "severity": "major",
            "started_at": f"{today}T02:00:00Z",
            "ended_at": f"{today}T04:00:00Z",
        },
    )

    r = auth_client.get(
        f"/mfg/equipment/{eq['id']}/oee",
        params={"target_date": today},
    )
    assert r.status_code == 200
    data = r.json()
    # 120 min downtime out of 480 → availability = 360/480 = 0.75
    assert data["availability"] == pytest.approx(0.75, abs=0.01)


def test_oee_not_found(auth_client: TestClient) -> None:
    r = auth_client.get(f"/mfg/equipment/{uuid4()}/oee")
    assert r.status_code == 404
