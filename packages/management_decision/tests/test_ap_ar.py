"""Tests for AP / AR records (TASK-MGMT-002)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


# --------------------------------------------------------------------------- #
# AP
# --------------------------------------------------------------------------- #


class TestAPAPI:
    def _make_ap(self, auth_client: TestClient) -> dict:
        return auth_client.post(
            "/mgmt/finance/ap",
            json={
                "purchase_order_id": str(uuid4()),
                "supplier_id": str(uuid4()),
                "total_amount": "5000.0000",
                "due_date": "2026-05-01",
                "memo": "原材料采购",
            },
        ).json()

    def test_create_ap(self, auth_client: TestClient) -> None:
        r = auth_client.post(
            "/mgmt/finance/ap",
            json={
                "purchase_order_id": str(uuid4()),
                "supplier_id": str(uuid4()),
                "total_amount": "10000.0000",
                "due_date": "2026-05-15",
            },
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == "unpaid"
        assert float(data["paid_amount"]) == 0
        assert float(data["balance"]) == 10000

    def test_list_ap(self, auth_client: TestClient) -> None:
        self._make_ap(auth_client)
        self._make_ap(auth_client)
        r = auth_client.get("/mgmt/finance/ap")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_get_ap(self, auth_client: TestClient) -> None:
        ap = self._make_ap(auth_client)
        r = auth_client.get(f"/mgmt/finance/ap/{ap['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == ap["id"]

    def test_get_ap_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get(f"/mgmt/finance/ap/{uuid4()}")
        assert r.status_code == 404

    def test_update_ap_payment(self, auth_client: TestClient) -> None:
        ap = self._make_ap(auth_client)
        # partial payment
        r = auth_client.patch(
            f"/mgmt/finance/ap/{ap['id']}",
            json={"paid_amount": "2000.0000"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "partial"
        assert float(data["balance"]) == 3000

        # full payment
        r2 = auth_client.patch(
            f"/mgmt/finance/ap/{ap['id']}",
            json={"paid_amount": "5000.0000"},
        )
        assert r2.json()["status"] == "paid"
        assert float(r2.json()["balance"]) == 0

    def test_filter_ap_by_status(self, auth_client: TestClient) -> None:
        ap = self._make_ap(auth_client)
        self._make_ap(auth_client)
        # pay one
        auth_client.patch(
            f"/mgmt/finance/ap/{ap['id']}",
            json={"paid_amount": "5000.0000"},
        )
        r = auth_client.get("/mgmt/finance/ap", params={"status": "paid"})
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["status"] == "paid"


# --------------------------------------------------------------------------- #
# AR
# --------------------------------------------------------------------------- #


class TestARAPI:
    def _make_ar(self, auth_client: TestClient) -> dict:
        return auth_client.post(
            "/mgmt/finance/ar",
            json={
                "sales_order_id": str(uuid4()),
                "customer_id": str(uuid4()),
                "total_amount": "8000.0000",
                "due_date": "2026-05-10",
                "memo": "产品销售",
            },
        ).json()

    def test_create_ar(self, auth_client: TestClient) -> None:
        r = auth_client.post(
            "/mgmt/finance/ar",
            json={
                "sales_order_id": str(uuid4()),
                "customer_id": str(uuid4()),
                "total_amount": "20000.0000",
                "due_date": "2026-06-01",
            },
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == "unpaid"
        assert float(data["received_amount"]) == 0
        assert float(data["balance"]) == 20000

    def test_list_ar(self, auth_client: TestClient) -> None:
        self._make_ar(auth_client)
        self._make_ar(auth_client)
        r = auth_client.get("/mgmt/finance/ar")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_get_ar(self, auth_client: TestClient) -> None:
        ar = self._make_ar(auth_client)
        r = auth_client.get(f"/mgmt/finance/ar/{ar['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == ar["id"]

    def test_get_ar_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get(f"/mgmt/finance/ar/{uuid4()}")
        assert r.status_code == 404

    def test_update_ar_receipt(self, auth_client: TestClient) -> None:
        ar = self._make_ar(auth_client)
        # partial receipt
        r = auth_client.patch(
            f"/mgmt/finance/ar/{ar['id']}",
            json={"received_amount": "3000.0000"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "partial"
        assert float(data["balance"]) == 5000

        # full receipt
        r2 = auth_client.patch(
            f"/mgmt/finance/ar/{ar['id']}",
            json={"received_amount": "8000.0000"},
        )
        assert r2.json()["status"] == "paid"
        assert float(r2.json()["balance"]) == 0

    def test_filter_ar_by_status(self, auth_client: TestClient) -> None:
        ar = self._make_ar(auth_client)
        self._make_ar(auth_client)
        auth_client.patch(
            f"/mgmt/finance/ar/{ar['id']}",
            json={"received_amount": "8000.0000"},
        )
        r = auth_client.get("/mgmt/finance/ar", params={"status": "unpaid"})
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["status"] == "unpaid"
