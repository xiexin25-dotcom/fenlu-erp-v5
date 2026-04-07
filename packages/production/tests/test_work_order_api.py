"""TASK-MFG-002 · WorkOrder CRUD endpoint tests."""

from __future__ import annotations

from uuid import uuid4

import respx
from fastapi.testclient import TestClient
from httpx import Response

from packages.production.services.bom_client import PLM_BASE_URL


def _create_payload() -> dict:
    return {
        "order_no": f"WO-{uuid4().hex[:8]}",
        "product_id": str(uuid4()),
        "bom_id": str(uuid4()),
        "routing_id": str(uuid4()),
        "planned_quantity": {"value": "100.0000", "uom": "pcs"},
        "planned_start": "2026-05-01T08:00:00Z",
        "planned_end": "2026-05-02T18:00:00Z",
    }


def _mock_bom_ok(bom_id: str, product_id: str) -> None:
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


def test_create_work_order(auth_client: TestClient) -> None:
    payload = _create_payload()
    r = auth_client.post("/mfg/work-orders", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["order_no"] == payload["order_no"]
    assert data["status"] == "planned"
    assert data["planned_quantity"]["value"] == "100.0000"
    assert data["completed_quantity"]["value"] == "0.0000"


def test_list_work_orders(auth_client: TestClient) -> None:
    # create two
    auth_client.post("/mfg/work-orders", json=_create_payload())
    auth_client.post("/mfg/work-orders", json=_create_payload())
    r = auth_client.get("/mfg/work-orders")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_get_work_order(auth_client: TestClient) -> None:
    r1 = auth_client.post("/mfg/work-orders", json=_create_payload())
    wo_id = r1.json()["id"]
    r2 = auth_client.get(f"/mfg/work-orders/{wo_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == wo_id


@respx.mock
def test_status_transition_happy_path(auth_client: TestClient) -> None:
    payload = _create_payload()
    r = auth_client.post("/mfg/work-orders", json=payload)
    wo = r.json()
    wo_id = wo["id"]

    # Mock BOM for the planned→released transition
    _mock_bom_ok(wo["bom_id"], wo["product_id"])

    for target in ("released", "in_progress", "completed", "closed"):
        r = auth_client.patch(
            f"/mfg/work-orders/{wo_id}/status",
            json={"status": target},
        )
        assert r.status_code == 200, f"transition to {target} failed: {r.text}"
        assert r.json()["status"] == target


def test_forbidden_status_transition(auth_client: TestClient) -> None:
    r = auth_client.post("/mfg/work-orders", json=_create_payload())
    wo_id = r.json()["id"]
    # planned → completed is not allowed (must go through released, in_progress first)
    r = auth_client.patch(
        f"/mfg/work-orders/{wo_id}/status",
        json={"status": "completed"},
    )
    assert r.status_code == 422
    assert "cannot transition" in r.json()["detail"]


def test_requires_auth(client: TestClient) -> None:
    r = client.get("/mfg/work-orders")
    assert r.status_code == 401


def test_get_nonexistent_returns_404(auth_client: TestClient) -> None:
    r = auth_client.get(f"/mfg/work-orders/{uuid4()}")
    assert r.status_code == 404
