"""TASK-MFG-010 · Energy meter + reading ingestion tests."""

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


def _create_meter(auth_client: TestClient) -> dict:
    r = auth_client.post(
        "/mfg/energy/meters",
        json={
            "code": f"EM-{uuid4().hex[:6]}",
            "name": "Main Power Meter",
            "energy_type": "electricity",
            "uom": "kWh",
            "location": "配电室",
        },
    )
    assert r.status_code == 201
    return r.json()


def test_create_meter(auth_client: TestClient) -> None:
    meter = _create_meter(auth_client)
    assert meter["energy_type"] == "electricity"
    assert meter["uom"] == "kWh"


def test_list_meters(auth_client: TestClient) -> None:
    _create_meter(auth_client)
    r = auth_client.get("/mfg/energy/meters")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_batch_ingest_readings(auth_client: TestClient) -> None:
    meter = _create_meter(auth_client)
    r = auth_client.post(
        "/mfg/energy/readings",
        json={
            "readings": [
                {
                    "meter_id": meter["id"],
                    "energy_type": "electricity",
                    "timestamp": "2026-05-01T08:00:00Z",
                    "reading": 10000.0,
                    "delta": 50.0,
                    "uom": "kWh",
                },
                {
                    "meter_id": meter["id"],
                    "energy_type": "electricity",
                    "timestamp": "2026-05-01T09:00:00Z",
                    "reading": 10050.0,
                    "delta": 50.0,
                    "uom": "kWh",
                },
            ]
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert len(data) == 2
    assert data[0]["delta"] == 50.0


@respx.mock
def test_unit_consumption(auth_client: TestClient) -> None:
    """Ingest readings + report job tickets → unit consumption."""
    meter = _create_meter(auth_client)
    product_id = str(uuid4())

    # Ingest 3 readings totaling 150 kWh
    auth_client.post(
        "/mfg/energy/readings",
        json={
            "readings": [
                {
                    "meter_id": meter["id"],
                    "energy_type": "electricity",
                    "timestamp": "2026-05-01T08:00:00Z",
                    "reading": 10000,
                    "delta": 50,
                    "uom": "kWh",
                },
                {
                    "meter_id": meter["id"],
                    "energy_type": "electricity",
                    "timestamp": "2026-05-01T09:00:00Z",
                    "reading": 10050,
                    "delta": 50,
                    "uom": "kWh",
                },
                {
                    "meter_id": meter["id"],
                    "energy_type": "electricity",
                    "timestamp": "2026-05-01T10:00:00Z",
                    "reading": 10100,
                    "delta": 50,
                    "uom": "kWh",
                },
            ]
        },
    )

    # Create a work order + report 100 units via job ticket
    bom_id = str(uuid4())
    wo_r = auth_client.post(
        "/mfg/work-orders",
        json={
            "order_no": f"WO-E-{uuid4().hex[:6]}",
            "product_id": product_id,
            "bom_id": bom_id,
            "routing_id": str(uuid4()),
            "planned_quantity": {"value": "100", "uom": "pcs"},
            "planned_start": "2026-05-01T08:00:00Z",
            "planned_end": "2026-05-02T18:00:00Z",
        },
    )
    wo = wo_r.json()

    # Release + in_progress
    respx.get(f"{PLM_BASE_URL}/plm/bom/{bom_id}").mock(
        return_value=Response(
            200,
            json={
                "id": bom_id,
                "product_id": product_id,
                "product_code": "P-001",
                "version": "1.0",
                "status": "approved",
                "items": [],
                "created_at": "2026-04-01T00:00:00Z",
                "updated_at": "2026-04-01T00:00:00Z",
            },
        )
    )
    auth_client.patch(f"/mfg/work-orders/{wo['id']}/status", json={"status": "released"})
    auth_client.patch(f"/mfg/work-orders/{wo['id']}/status", json={"status": "in_progress"})

    # Report 100 units
    jt = auth_client.post(
        "/mfg/job-tickets",
        json={"work_order_id": wo["id"], "ticket_no": "JT-E-001"},
    ).json()
    auth_client.post(
        f"/mfg/job-tickets/{jt['id']}/report",
        json={"completed_qty": "100", "scrap_qty": "0", "minutes": "60"},
    )

    # Query unit consumption
    r = auth_client.get(
        "/mfg/energy/unit-consumption",
        params={
            "product_id": product_id,
            "period": "30d",
            "energy_type": "electricity",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_consumption"] == 150.0
    assert data["output_quantity"]["value"] == "100.0000"
    # 150 kWh / 100 pcs = 1.5 kWh/pcs
    assert data["unit_consumption"] == pytest.approx(1.5, abs=0.01)


def test_unit_consumption_no_output(auth_client: TestClient) -> None:
    """No production → unit_consumption = 0."""
    _create_meter(auth_client)
    r = auth_client.get(
        "/mfg/energy/unit-consumption",
        params={
            "product_id": str(uuid4()),
            "period": "30d",
            "energy_type": "electricity",
        },
    )
    assert r.status_code == 200
    assert r.json()["unit_consumption"] == 0.0
