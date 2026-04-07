"""TASK-MFG-006 · SPC endpoint integration test."""

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


def test_spc_endpoint(auth_client: TestClient) -> None:
    product_id = str(uuid4())

    # Create several inspections for the same product
    for defects in [3, 5, 2, 4, 6]:
        auth_client.post(
            "/mfg/qc/inspections",
            json={
                "inspection_no": f"QC-{uuid4().hex[:8]}",
                "type": "ipqc",
                "product_id": product_id,
                "sample_size": 50,
                "defect_count": defects,
                "result": "pass" if defects < 5 else "fail",
                "inspector_id": str(uuid4()),
            },
        )

    r = auth_client.get(f"/mfg/qc/spc?product_id={product_id}&period=30d")
    assert r.status_code == 200
    data = r.json()
    assert data["total_inspected"] == 250
    assert data["total_defects"] == 20
    assert len(data["points"]) == 5
    # Each point should have ucl >= cl >= lcl
    for pt in data["points"]:
        assert pt["ucl"] >= pt["cl"]
        assert pt["cl"] >= pt["lcl"]
        assert pt["lcl"] >= 0


def test_spc_no_data_returns_404(auth_client: TestClient) -> None:
    r = auth_client.get(f"/mfg/qc/spc?product_id={uuid4()}&period=30d")
    assert r.status_code == 404


def test_spc_invalid_period(auth_client: TestClient) -> None:
    r = auth_client.get(f"/mfg/qc/spc?product_id={uuid4()}&period=abc")
    assert r.status_code == 422
