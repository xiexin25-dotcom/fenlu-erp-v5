"""TASK-MFG-005 · QC inspection endpoint tests."""

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


def _insp_payload(*, result: str = "pass", work_order_id: str | None = None) -> dict:
    d: dict = {
        "inspection_no": f"QC-{uuid4().hex[:8]}",
        "type": "ipqc",
        "product_id": str(uuid4()),
        "sample_size": 50,
        "defect_count": 3 if result == "fail" else 0,
        "result": result,
        "inspector_id": str(uuid4()),
    }
    if work_order_id:
        d["work_order_id"] = work_order_id
    return d


def test_create_inspection_pass(
    auth_client: TestClient, _fake_publisher: FakeEventPublisher
) -> None:
    r = auth_client.post("/mfg/qc/inspections", json=_insp_payload(result="pass"))
    assert r.status_code == 201
    data = r.json()
    assert data["result"] == "pass"
    assert data["defect_count"] == 0
    # No event for PASS
    assert len(_fake_publisher.events) == 0


def test_create_inspection_fail_emits_event(
    auth_client: TestClient, _fake_publisher: FakeEventPublisher
) -> None:
    r = auth_client.post("/mfg/qc/inspections", json=_insp_payload(result="fail"))
    assert r.status_code == 201
    data = r.json()
    assert data["result"] == "fail"
    # QCFailedEvent emitted
    assert len(_fake_publisher.events) == 1
    event = _fake_publisher.events[0]
    assert event.event_type == "qc.failed"
    assert event.defect_count == 3
    assert event.sample_size == 50


def test_list_inspections_by_work_order(auth_client: TestClient) -> None:
    wo_id = str(uuid4())
    auth_client.post("/mfg/qc/inspections", json=_insp_payload(work_order_id=wo_id))
    auth_client.post("/mfg/qc/inspections", json=_insp_payload(work_order_id=wo_id))
    auth_client.post("/mfg/qc/inspections", json=_insp_payload())  # different WO

    r = auth_client.get(f"/mfg/qc/inspections?work_order_id={wo_id}")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_inspections_all(auth_client: TestClient) -> None:
    auth_client.post("/mfg/qc/inspections", json=_insp_payload())
    r = auth_client.get("/mfg/qc/inspections")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_requires_auth(client: TestClient) -> None:
    r = client.post("/mfg/qc/inspections", json=_insp_payload())
    assert r.status_code == 401
