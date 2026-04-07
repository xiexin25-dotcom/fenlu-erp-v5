"""TASK-MFG-011 · APS endpoint integration test."""

from __future__ import annotations

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


def _create_workstation(auth_client: TestClient) -> dict:
    r = auth_client.post(
        "/mfg/aps/workstations",
        json={
            "code": f"WS-{uuid4().hex[:6]}",
            "name": "CNC Station",
            "workshop_id": str(uuid4()),
            "capacity": 1,
        },
    )
    # If no dedicated endpoint, create via the general equipment approach
    # Actually we need a workstation CRUD — let me add a minimal one
    # For now, test via direct DB insert in conftest or add endpoint
    # Let's add a quick create endpoint
    assert r.status_code == 201
    return r.json()


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


@respx.mock
def test_aps_run(auth_client: TestClient) -> None:
    # Create workstation
    ws = _create_workstation(auth_client)

    # Create 2 work orders and release them
    wos = []
    for i in range(2):
        bom_id = str(uuid4())
        product_id = str(uuid4())
        r = auth_client.post(
            "/mfg/work-orders",
            json={
                "order_no": f"WO-APS-{i}",
                "product_id": product_id,
                "bom_id": bom_id,
                "routing_id": str(uuid4()),
                "planned_quantity": {"value": "50", "uom": "pcs"},
                "planned_start": "2026-05-01T08:00:00Z",
                "planned_end": f"2026-05-0{i + 2}T18:00:00Z",
            },
        )
        wo = r.json()
        wos.append(wo)

        respx.get(f"{PLM_BASE_URL}/plm/bom/{bom_id}").mock(
            return_value=Response(200, json=_bom_response(bom_id, product_id))
        )
        auth_client.patch(
            f"/mfg/work-orders/{wo['id']}/status", json={"status": "released"}
        )

    # Run APS
    r = auth_client.post(
        "/mfg/aps/run",
        json={
            "range_start": "2026-05-01T08:00:00Z",
            "range_end": "2026-05-10T18:00:00Z",
            "estimated_hours_per_order": 4.0,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_orders"] == 2
    assert data["total_workstations"] == 1
    assert len(data["slots"]) == 2
    # Sequential on 1 WS
    assert data["slots"][0]["workstation_id"] == ws["id"]
    assert data["slots"][1]["planned_start"] == data["slots"][0]["planned_end"]


def test_aps_no_workstations(auth_client: TestClient) -> None:
    r = auth_client.post(
        "/mfg/aps/run",
        json={
            "range_start": "2026-05-01T08:00:00Z",
            "range_end": "2026-05-10T18:00:00Z",
        },
    )
    assert r.status_code == 422
    assert "no workstations" in r.json()["detail"]


def test_aps_invalid_range(auth_client: TestClient) -> None:
    r = auth_client.post(
        "/mfg/aps/run",
        json={
            "range_start": "2026-05-10T08:00:00Z",
            "range_end": "2026-05-01T18:00:00Z",
        },
    )
    assert r.status_code == 422
