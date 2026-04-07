"""Tests for TASK-PLM-001: Product master + version."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def product_payload() -> dict[str, str]:
    return {
        "code": "PRD-001",
        "name": "测试产品",
        "category": "self_made",
        "uom": "pcs",
        "description": "A test product",
    }


class TestCreateProduct:
    def test_create_success(
        self, auth_client: Any, product_payload: dict[str, str]
    ) -> None:
        r = auth_client.post("/plm/products", json=product_payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["code"] == "PRD-001"
        assert data["name"] == "测试产品"
        assert data["category"] == "self_made"
        assert data["uom"] == "pcs"
        assert data["current_version"] == "V1.0"
        assert data["is_active"] is True
        assert data["id"] is not None
        assert data["tenant_id"] is not None

    def test_create_requires_auth(self, client: Any, product_payload: dict[str, str]) -> None:
        r = client.post("/plm/products", json=product_payload)
        assert r.status_code == 401


class TestListProducts:
    def test_list_empty(self, auth_client: Any) -> None:
        r = auth_client.get("/plm/products")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_items(self, auth_client: Any, product_payload: dict[str, str]) -> None:
        auth_client.post("/plm/products", json=product_payload)
        auth_client.post(
            "/plm/products",
            json={**product_payload, "code": "PRD-002", "name": "产品二"},
        )

        r = auth_client.get("/plm/products")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_pagination(self, auth_client: Any, product_payload: dict[str, str]) -> None:
        for i in range(3):
            auth_client.post(
                "/plm/products",
                json={**product_payload, "code": f"PRD-{i:03d}"},
            )

        r = auth_client.get("/plm/products?page=1&size=2")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["size"] == 2


class TestGetProduct:
    def test_get_success(self, auth_client: Any, product_payload: dict[str, str]) -> None:
        create_r = auth_client.post("/plm/products", json=product_payload)
        pid = create_r.json()["id"]

        r = auth_client.get(f"/plm/products/{pid}")
        assert r.status_code == 200
        assert r.json()["code"] == "PRD-001"

    def test_get_not_found(self, auth_client: Any) -> None:
        fake_id = "00000000-0000-0000-0000-000000000001"
        r = auth_client.get(f"/plm/products/{fake_id}")
        assert r.status_code == 404


class TestCreateVersion:
    def test_create_version(self, auth_client: Any, product_payload: dict[str, str]) -> None:
        create_r = auth_client.post("/plm/products", json=product_payload)
        pid = create_r.json()["id"]

        r = auth_client.post(
            f"/plm/products/{pid}/versions",
            json={"change_summary": "BOM 更新"},
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["version"] == "V2.0"
        assert data["is_current"] is True
        assert data["change_summary"] == "BOM 更新"

        # product should now show V2.0
        product_r = auth_client.get(f"/plm/products/{pid}")
        assert product_r.json()["current_version"] == "V2.0"

    def test_create_multiple_versions(
        self, auth_client: Any, product_payload: dict[str, str]
    ) -> None:
        create_r = auth_client.post("/plm/products", json=product_payload)
        pid = create_r.json()["id"]

        auth_client.post(f"/plm/products/{pid}/versions", json={})
        r = auth_client.post(f"/plm/products/{pid}/versions", json={})
        assert r.status_code == 201
        assert r.json()["version"] == "V3.0"

        product_r = auth_client.get(f"/plm/products/{pid}")
        assert product_r.json()["current_version"] == "V3.0"

    def test_version_not_found_product(self, auth_client: Any) -> None:
        fake_id = "00000000-0000-0000-0000-000000000001"
        r = auth_client.post(f"/plm/products/{fake_id}/versions", json={})
        assert r.status_code == 404
