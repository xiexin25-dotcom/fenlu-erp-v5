"""TASK-MFG-009 · Safety hazard closed-loop tests."""

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


def _create_hazard(auth_client: TestClient) -> dict:
    r = auth_client.post(
        "/mfg/safety/hazards",
        json={
            "hazard_no": f"HZ-{uuid4().hex[:6]}",
            "location": "车间 A-3 区",
            "level": "major",
            "description": "地面油污未清理",
        },
    )
    assert r.status_code == 201
    return r.json()


def test_create_hazard(
    auth_client: TestClient, _fake_publisher: FakeEventPublisher
) -> None:
    h = _create_hazard(auth_client)
    assert h["status"] == "reported"
    assert h["level"] == "major"
    # HazardReportedEvent emitted
    assert len(_fake_publisher.events) == 1
    assert _fake_publisher.events[0].event_type == "hazard.reported"


def test_full_transition_chain(auth_client: TestClient) -> None:
    h = _create_hazard(auth_client)
    hid = h["id"]

    for target in ("assigned", "rectifying", "verified", "closed"):
        r = auth_client.patch(
            f"/mfg/safety/hazards/{hid}/transition",
            json={"status": target, "remark": f"transition to {target}"},
        )
        assert r.status_code == 200, f"to {target}: {r.text}"
        assert r.json()["status"] == target

    # verified sets rectified_at
    data = auth_client.get(f"/mfg/safety/hazards/{hid}").json()
    assert data["rectified_at"] is not None
    assert data["closed_at"] is not None


def test_forbidden_transition(auth_client: TestClient) -> None:
    h = _create_hazard(auth_client)
    # reported → closed is not allowed
    r = auth_client.patch(
        f"/mfg/safety/hazards/{h['id']}/transition",
        json={"status": "closed"},
    )
    assert r.status_code == 422
    assert "cannot transition" in r.json()["detail"]


def test_audit_log(auth_client: TestClient) -> None:
    h = _create_hazard(auth_client)
    hid = h["id"]

    # Do two transitions
    auth_client.patch(
        f"/mfg/safety/hazards/{hid}/transition",
        json={"status": "assigned", "remark": "指派给张三"},
    )
    auth_client.patch(
        f"/mfg/safety/hazards/{hid}/transition",
        json={"status": "rectifying"},
    )

    r = auth_client.get(f"/mfg/safety/hazards/{hid}/audit-log")
    assert r.status_code == 200
    logs = r.json()
    # 1 creation log + 2 transitions = 3
    assert len(logs) == 3
    assert logs[0]["from_status"] == ""
    assert logs[0]["to_status"] == "reported"
    assert logs[1]["from_status"] == "reported"
    assert logs[1]["to_status"] == "assigned"
    assert logs[1]["remark"] == "指派给张三"
    assert logs[2]["to_status"] == "rectifying"


def test_list_hazards_filter_by_status(auth_client: TestClient) -> None:
    _create_hazard(auth_client)
    r = auth_client.get("/mfg/safety/hazards?status=reported")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    r = auth_client.get("/mfg/safety/hazards?status=closed")
    assert r.status_code == 200
    assert len(r.json()) == 0
