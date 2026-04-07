"""Tests for TASK-PLM-004: Routing & RoutingOperation."""

from __future__ import annotations

from typing import Any

import pytest


def _create_product(auth_client: Any, code: str = "RTG-P") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/products",
        json={"code": code, "name": "Routing Product", "category": "self_made", "uom": "pcs"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_routing(auth_client: Any, product_id: str, version: str = "V1.0") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/routing",
        json={"product_id": product_id, "version": version, "description": "test routing"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _add_op(
    auth_client: Any,
    routing_id: str,
    seq: int,
    code: str,
    name: str,
    std_min: float,
    setup_min: float = 0.0,
    ws_code: str | None = None,
) -> Any:
    body: dict[str, Any] = {
        "sequence": seq,
        "operation_code": code,
        "operation_name": name,
        "standard_minutes": std_min,
        "setup_minutes": setup_min,
    }
    if ws_code:
        body["workstation_code"] = ws_code
    return auth_client.post(f"/plm/routing/{routing_id}/operations", json=body)


class TestCreateRouting:
    def test_create_success(self, auth_client: Any) -> None:
        prod = _create_product(auth_client)
        rtg = _create_routing(auth_client, prod["id"])
        assert rtg["product_id"] == prod["id"]
        assert rtg["version"] == "V1.0"
        assert rtg["operations"] == []
        assert rtg["total_standard_minutes"] == 0.0
        assert rtg["description"] == "test routing"

    def test_create_requires_auth(self, client: Any) -> None:
        fake_id = "00000000-0000-0000-0000-000000000001"
        r = client.post("/plm/routing", json={"product_id": fake_id, "version": "V1.0"})
        assert r.status_code == 401


class TestAddOperation:
    def test_add_operation(self, auth_client: Any) -> None:
        prod = _create_product(auth_client, "OP-P")
        rtg = _create_routing(auth_client, prod["id"])

        r = _add_op(auth_client, rtg["id"], 10, "CUT", "Cutting", 5.0, ws_code="WS-01")
        assert r.status_code == 201, r.text
        op = r.json()
        assert op["sequence"] == 10
        assert op["operation_code"] == "CUT"
        assert op["operation_name"] == "Cutting"
        assert op["standard_minutes"] == 5.0
        assert op["setup_minutes"] == 0.0
        assert op["workstation_code"] == "WS-01"

    def test_add_operation_routing_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = _add_op(auth_client, fake, 10, "X", "X", 1.0)
        assert r.status_code == 404


class TestGetRouting:
    def test_get_with_operations(self, auth_client: Any) -> None:
        prod = _create_product(auth_client, "GET-RTG")
        rtg = _create_routing(auth_client, prod["id"])
        rid = rtg["id"]

        _add_op(auth_client, rid, 10, "CUT", "Cutting", 5.0, setup_min=2.0)
        _add_op(auth_client, rid, 20, "WELD", "Welding", 10.0, setup_min=3.0)
        _add_op(auth_client, rid, 30, "PAINT", "Painting", 8.0)

        r = auth_client.get(f"/plm/routing/{rid}")
        assert r.status_code == 200
        data = r.json()
        assert len(data["operations"]) == 3
        # total_standard_minutes = 5 + 10 + 8 = 23
        assert data["total_standard_minutes"] == 23.0
        # operations 应按 sequence 排序
        seqs = [op["sequence"] for op in data["operations"]]
        assert seqs == [10, 20, 30]

    def test_get_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.get(f"/plm/routing/{fake}")
        assert r.status_code == 404

    def test_get_matches_routing_dto_shape(self, auth_client: Any) -> None:
        """验证返回结构匹配 RoutingDTO 契约字段。"""
        prod = _create_product(auth_client, "DTO-RTG")
        rtg = _create_routing(auth_client, prod["id"])
        _add_op(auth_client, rtg["id"], 10, "OP1", "Op One", 7.5, setup_min=1.5, ws_code="WS-A")

        r = auth_client.get(f"/plm/routing/{rtg['id']}")
        data = r.json()

        # RoutingDTO fields
        assert "id" in data
        assert "product_id" in data
        assert "version" in data
        assert "operations" in data
        assert "total_standard_minutes" in data

        # RoutingOperationDTO fields
        op = data["operations"][0]
        assert "sequence" in op
        assert "operation_code" in op
        assert "operation_name" in op
        assert "workstation_code" in op
        assert "standard_minutes" in op
        assert "setup_minutes" in op

    def test_empty_routing_total_zero(self, auth_client: Any) -> None:
        """无工序的 routing,total_standard_minutes 应为 0。"""
        prod = _create_product(auth_client, "EMPTY-RTG")
        rtg = _create_routing(auth_client, prod["id"])

        r = auth_client.get(f"/plm/routing/{rtg['id']}")
        assert r.status_code == 200
        assert r.json()["total_standard_minutes"] == 0.0
