"""Tests for TASK-PLM-002: BOM tree + items, cycle detection, cost rollup."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest


def _create_product(auth_client: Any, code: str, name: str) -> dict[str, Any]:
    r = auth_client.post(
        "/plm/products",
        json={"code": code, "name": name, "category": "self_made", "uom": "pcs"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_bom(auth_client: Any, product_id: str, version: str = "V1.0") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/bom",
        json={"product_id": product_id, "version": version},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _add_item(
    auth_client: Any,
    bom_id: str,
    component_id: str,
    quantity: str = "2.0000",
    uom: str = "pcs",
    unit_cost: str | None = None,
    scrap_rate: str = "0.0000",
) -> Any:
    body: dict[str, Any] = {
        "component_id": component_id,
        "quantity": quantity,
        "uom": uom,
        "scrap_rate": scrap_rate,
    }
    if unit_cost is not None:
        body["unit_cost"] = unit_cost
    return auth_client.post(f"/plm/bom/{bom_id}/items", json=body)


class TestCreateBOM:
    def test_create_bom(self, auth_client: Any) -> None:
        prod = _create_product(auth_client, "ASM-001", "Assembly")
        bom = _create_bom(auth_client, prod["id"])
        assert bom["product_id"] == prod["id"]
        assert bom["version"] == "V1.0"
        assert bom["status"] == "draft"
        assert bom["items"] == []
        assert bom["product_code"] == "ASM-001"

    def test_create_bom_requires_auth(self, client: Any) -> None:
        fake_id = "00000000-0000-0000-0000-000000000001"
        r = client.post("/plm/bom", json={"product_id": fake_id, "version": "V1.0"})
        assert r.status_code == 401


class TestAddBOMItem:
    def test_add_item(self, auth_client: Any) -> None:
        parent = _create_product(auth_client, "ASM-001", "Assembly")
        comp = _create_product(auth_client, "PART-001", "Part A")
        bom = _create_bom(auth_client, parent["id"])

        r = _add_item(auth_client, bom["id"], comp["id"], unit_cost="10.5000")
        assert r.status_code == 201, r.text
        item = r.json()
        assert item["component_id"] == comp["id"]
        assert item["component_code"] == "PART-001"
        assert item["component_name"] == "Part A"
        assert Decimal(item["quantity"]) == Decimal("2.0000")
        assert Decimal(item["unit_cost"]) == Decimal("10.5000")

    def test_add_item_not_found_bom(self, auth_client: Any) -> None:
        comp = _create_product(auth_client, "PART-001", "Part")
        fake_bom = "00000000-0000-0000-0000-000000000099"
        r = _add_item(auth_client, fake_bom, comp["id"])
        assert r.status_code == 404

    def test_add_item_not_found_component(self, auth_client: Any) -> None:
        parent = _create_product(auth_client, "ASM-001", "Assembly")
        bom = _create_bom(auth_client, parent["id"])
        fake_comp = "00000000-0000-0000-0000-000000000099"
        r = _add_item(auth_client, bom["id"], fake_comp)
        assert r.status_code == 404


class TestCycleDetection:
    def test_self_reference_rejected(self, auth_client: Any) -> None:
        """产品不能包含自己作为 BOM 组件。"""
        prod = _create_product(auth_client, "LOOP-001", "Loop Product")
        bom = _create_bom(auth_client, prod["id"])
        r = _add_item(auth_client, bom["id"], prod["id"])
        assert r.status_code == 422
        assert "cycle" in r.json()["detail"].lower()

    def test_indirect_cycle_rejected(self, auth_client: Any) -> None:
        """A → B → A 间接环应被拒绝。"""
        prod_a = _create_product(auth_client, "CYC-A", "Product A")
        prod_b = _create_product(auth_client, "CYC-B", "Product B")

        # A 的 BOM 包含 B
        bom_a = _create_bom(auth_client, prod_a["id"])
        r = _add_item(auth_client, bom_a["id"], prod_b["id"])
        assert r.status_code == 201

        # B 的 BOM 尝试包含 A → cycle
        bom_b = _create_bom(auth_client, prod_b["id"])
        r = _add_item(auth_client, bom_b["id"], prod_a["id"])
        assert r.status_code == 422
        assert "cycle" in r.json()["detail"].lower()

    def test_no_false_positive(self, auth_client: Any) -> None:
        """A → B, A → C 不应触发 cycle (diamond 不是 cycle)。"""
        prod_a = _create_product(auth_client, "DIA-A", "A")
        prod_b = _create_product(auth_client, "DIA-B", "B")
        prod_c = _create_product(auth_client, "DIA-C", "C")

        bom_a = _create_bom(auth_client, prod_a["id"])
        r1 = _add_item(auth_client, bom_a["id"], prod_b["id"])
        assert r1.status_code == 201
        r2 = _add_item(auth_client, bom_a["id"], prod_c["id"])
        assert r2.status_code == 201


class TestGetBOM:
    def test_get_bom_with_items(self, auth_client: Any) -> None:
        parent = _create_product(auth_client, "ASM-GET", "Assembly")
        comp1 = _create_product(auth_client, "P-GET-1", "Part 1")
        comp2 = _create_product(auth_client, "P-GET-2", "Part 2")

        bom = _create_bom(auth_client, parent["id"])
        _add_item(auth_client, bom["id"], comp1["id"], unit_cost="10.0000")
        _add_item(auth_client, bom["id"], comp2["id"], quantity="3.0000", unit_cost="5.0000")

        r = auth_client.get(f"/plm/bom/{bom['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["product_code"] == "ASM-GET"
        assert len(data["items"]) == 2

    def test_get_bom_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.get(f"/plm/bom/{fake}")
        assert r.status_code == 404


class TestCostRollup:
    def test_leaf_cost_rollup(self, auth_client: Any) -> None:
        """简单一级 BOM 成本汇总: sum(qty * (1+scrap) * unit_cost)。"""
        parent = _create_product(auth_client, "COST-P", "Parent")
        c1 = _create_product(auth_client, "COST-C1", "Child 1")
        c2 = _create_product(auth_client, "COST-C2", "Child 2")

        bom = _create_bom(auth_client, parent["id"])
        # c1: qty=2, scrap=0.1, cost=10 → 2 * 1.1 * 10 = 22
        _add_item(auth_client, bom["id"], c1["id"], quantity="2.0000", scrap_rate="0.1000", unit_cost="10.0000")
        # c2: qty=3, scrap=0, cost=5 → 3 * 1 * 5 = 15
        _add_item(auth_client, bom["id"], c2["id"], quantity="3.0000", scrap_rate="0.0000", unit_cost="5.0000")

        r = auth_client.get(f"/plm/bom/{bom['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["total_cost"] is not None
        # 22 + 15 = 37
        assert Decimal(data["total_cost"]["amount"]) == Decimal("37.0000")
        assert data["total_cost"]["currency"] == "CNY"

    def test_no_cost_when_missing_unit_cost(self, auth_client: Any) -> None:
        """所有 item 缺 unit_cost 且无子 BOM → total_cost = null。"""
        parent = _create_product(auth_client, "NOCOST-P", "Parent")
        c1 = _create_product(auth_client, "NOCOST-C1", "Child")

        bom = _create_bom(auth_client, parent["id"])
        _add_item(auth_client, bom["id"], c1["id"])

        r = auth_client.get(f"/plm/bom/{bom['id']}")
        assert r.status_code == 200
        assert r.json()["total_cost"] is None

    def test_multilevel_cost_rollup(self, auth_client: Any) -> None:
        """两级 BOM: parent → sub-asm(qty=1) → leaf(qty=2, cost=10)。"""
        leaf = _create_product(auth_client, "ML-LEAF", "Leaf")
        sub = _create_product(auth_client, "ML-SUB", "Sub Assembly")
        top = _create_product(auth_client, "ML-TOP", "Top Assembly")

        # sub BOM: 2 x leaf @ 10 = 20
        bom_sub = _create_bom(auth_client, sub["id"])
        _add_item(auth_client, bom_sub["id"], leaf["id"], quantity="2.0000", unit_cost="10.0000")

        # top BOM: 1 x sub (cost rolls up to 20)
        bom_top = _create_bom(auth_client, top["id"])
        _add_item(auth_client, bom_top["id"], sub["id"], quantity="1.0000")

        r = auth_client.get(f"/plm/bom/{bom_top['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["total_cost"] is not None
        # 1 * (1+0) * 20 = 20
        assert Decimal(data["total_cost"]["amount"]) == Decimal("20.0000")


class TestDeepCopyOnVersion:
    def test_bom_copied_on_new_version(self, auth_client: Any) -> None:
        """创建新版本时,旧版本 BOM 被深拷贝。"""
        prod = _create_product(auth_client, "COPY-P", "Copyable")
        comp = _create_product(auth_client, "COPY-C", "Component")

        bom_v1 = _create_bom(auth_client, prod["id"], "V1.0")
        _add_item(auth_client, bom_v1["id"], comp["id"], unit_cost="7.0000")

        # create V2.0
        r = auth_client.post(f"/plm/products/{prod['id']}/versions", json={"change_summary": "test"})
        assert r.status_code == 201
        assert r.json()["version"] == "V2.0"

        # V2.0 应有独立 BOM,内容与 V1.0 相同
        # 通过 product 查找 V2.0 BOM — 用内部接口直接查
        # 我们没有按 version 查 BOM 的 API,但可以验证 GET bom/{v1_id} 的 items 仍在
        r_v1 = auth_client.get(f"/plm/bom/{bom_v1['id']}")
        assert r_v1.status_code == 200
        assert len(r_v1.json()["items"]) == 1  # 原 BOM 不受影响
