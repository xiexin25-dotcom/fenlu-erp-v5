"""TASK-MFG-003 · BOM integration tests (respx mock)."""

from __future__ import annotations

from uuid import uuid4

import pytest
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


def _bom_response(bom_id: str, product_id: str) -> dict:
    """Minimal BOMDTO-shaped response."""
    return {
        "id": bom_id,
        "product_id": product_id,
        "product_code": "PROD-001",
        "version": "1.0",
        "status": "approved",
        "items": [],
        "created_at": "2026-04-01T00:00:00Z",
        "updated_at": "2026-04-01T00:00:00Z",
    }


@respx.mock
def test_release_with_valid_bom(auth_client: TestClient) -> None:
    payload = _create_payload()
    r = auth_client.post("/mfg/work-orders", json=payload)
    assert r.status_code == 201
    wo = r.json()

    # Mock PLM returning a valid BOM
    bom_id = wo["bom_id"]
    respx.get(f"{PLM_BASE_URL}/plm/bom/{bom_id}").mock(
        return_value=Response(200, json=_bom_response(bom_id, wo["product_id"]))
    )

    r = auth_client.patch(
        f"/mfg/work-orders/{wo['id']}/status",
        json={"status": "released"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "released"


@respx.mock
def test_release_with_missing_bom_returns_422(auth_client: TestClient) -> None:
    payload = _create_payload()
    r = auth_client.post("/mfg/work-orders", json=payload)
    wo = r.json()

    bom_id = wo["bom_id"]
    respx.get(f"{PLM_BASE_URL}/plm/bom/{bom_id}").mock(
        return_value=Response(404, json={"detail": "not found"})
    )

    r = auth_client.patch(
        f"/mfg/work-orders/{wo['id']}/status",
        json={"status": "released"},
    )
    assert r.status_code == 422
    assert "BOM" in r.json()["detail"]
