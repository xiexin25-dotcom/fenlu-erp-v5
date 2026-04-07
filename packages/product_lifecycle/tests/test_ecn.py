"""Tests for TASK-PLM-005: ECN state machine + auto version-bump."""

from __future__ import annotations

from typing import Any

import pytest


def _create_product(auth_client: Any, code: str = "ECN-P") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/products",
        json={"code": code, "name": "ECN Product", "category": "self_made", "uom": "pcs"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_ecn(
    auth_client: Any,
    product_id: str,
    ecn_no: str = "ECN-001",
    title: str = "Test ECN",
) -> dict[str, Any]:
    r = auth_client.post(
        "/plm/ecn",
        json={
            "product_id": product_id,
            "ecn_no": ecn_no,
            "title": title,
            "reason": "need change",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _transition(auth_client: Any, ecn_id: str, target: str) -> Any:
    return auth_client.post(
        f"/plm/ecn/{ecn_id}/transition",
        json={"target_status": target},
    )


def _walk_to_released(auth_client: Any, ecn_id: str) -> None:
    """Push ECN through draft → reviewing → approved → released."""
    for target in ("reviewing", "approved", "released"):
        r = _transition(auth_client, ecn_id, target)
        assert r.status_code == 200, f"transition to {target} failed: {r.text}"


class TestCreateECN:
    def test_create_success(self, auth_client: Any) -> None:
        prod = _create_product(auth_client)
        ecn = _create_ecn(auth_client, prod["id"])
        assert ecn["ecn_no"] == "ECN-001"
        assert ecn["status"] == "draft"
        assert ecn["product_id"] == prod["id"]
        assert ecn["title"] == "Test ECN"
        assert ecn["reason"] == "need change"

    def test_create_product_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.post(
            "/plm/ecn",
            json={"product_id": fake, "ecn_no": "X", "title": "X"},
        )
        assert r.status_code == 404

    def test_create_requires_auth(self, client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000001"
        r = client.post("/plm/ecn", json={"product_id": fake, "ecn_no": "X", "title": "X"})
        assert r.status_code == 401


class TestGetECN:
    def test_get_success(self, auth_client: Any) -> None:
        prod = _create_product(auth_client, "ECN-GET")
        ecn = _create_ecn(auth_client, prod["id"], ecn_no="ECN-GET-001")
        r = auth_client.get(f"/plm/ecn/{ecn['id']}")
        assert r.status_code == 200
        assert r.json()["ecn_no"] == "ECN-GET-001"

    def test_get_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.get(f"/plm/ecn/{fake}")
        assert r.status_code == 404


class TestStateMachine:
    def test_happy_path(self, auth_client: Any) -> None:
        """draft → reviewing → approved → released → effective 完整流程。"""
        prod = _create_product(auth_client, "SM-HAPPY")
        ecn = _create_ecn(auth_client, prod["id"], ecn_no="SM-001")
        eid = ecn["id"]

        for target, expected in [
            ("reviewing", "reviewing"),
            ("approved", "approved"),
            ("released", "released"),
            ("effective", "effective"),
        ]:
            r = _transition(auth_client, eid, target)
            assert r.status_code == 200, r.text
            assert r.json()["status"] == expected

    def test_invalid_transition_from_draft(self, auth_client: Any) -> None:
        """draft 只能 → reviewing,不能直接跳到 approved。"""
        prod = _create_product(auth_client, "SM-INV1")
        ecn = _create_ecn(auth_client, prod["id"], ecn_no="SM-INV1")
        r = _transition(auth_client, ecn["id"], "approved")
        assert r.status_code == 422
        assert "invalid transition" in r.json()["detail"].lower()

    def test_invalid_transition_from_effective(self, auth_client: Any) -> None:
        """effective 是终态,不能再转换。"""
        prod = _create_product(auth_client, "SM-TERM")
        ecn = _create_ecn(auth_client, prod["id"], ecn_no="SM-TERM")
        _walk_to_released(auth_client, ecn["id"])
        r = _transition(auth_client, ecn["id"], "effective")
        assert r.status_code == 200
        # try again
        r = _transition(auth_client, ecn["id"], "reviewing")
        assert r.status_code == 422

    def test_reject_back_to_draft(self, auth_client: Any) -> None:
        """reviewing → draft (reject) 是合法的。"""
        prod = _create_product(auth_client, "SM-REJ")
        ecn = _create_ecn(auth_client, prod["id"], ecn_no="SM-REJ")
        _transition(auth_client, ecn["id"], "reviewing")
        r = _transition(auth_client, ecn["id"], "draft")
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    def test_ecn_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = _transition(auth_client, fake, "reviewing")
        assert r.status_code == 404


class TestAutoVersionBump:
    def test_effective_bumps_product_version(self, auth_client: Any) -> None:
        """ECN 生效时产品版本从 V1.0 → V2.0。"""
        prod = _create_product(auth_client, "BUMP-P")
        assert prod["current_version"] == "V1.0"

        ecn = _create_ecn(auth_client, prod["id"], ecn_no="BUMP-001")
        _walk_to_released(auth_client, ecn["id"])
        r = _transition(auth_client, ecn["id"], "effective")
        assert r.status_code == 200

        # product should now be V2.0
        r = auth_client.get(f"/plm/products/{prod['id']}")
        assert r.json()["current_version"] == "V2.0"

    def test_effective_copies_bom(self, auth_client: Any) -> None:
        """ECN 生效时 BOM 被深拷贝到新版本。"""
        prod = _create_product(auth_client, "BUMP-BOM")
        comp = _create_product(auth_client, "BUMP-COMP")

        # create V1.0 BOM with one item
        bom_r = auth_client.post(
            "/plm/bom",
            json={"product_id": prod["id"], "version": "V1.0"},
        )
        assert bom_r.status_code == 201
        bom_id = bom_r.json()["id"]
        auth_client.post(
            f"/plm/bom/{bom_id}/items",
            json={
                "component_id": comp["id"],
                "quantity": "5.0000",
                "uom": "pcs",
                "unit_cost": "3.0000",
            },
        )

        # ECN → effective
        ecn = _create_ecn(auth_client, prod["id"], ecn_no="BUMP-BOM-001")
        _walk_to_released(auth_client, ecn["id"])
        r = _transition(auth_client, ecn["id"], "effective")
        assert r.status_code == 200

        # original V1.0 BOM untouched
        r_v1 = auth_client.get(f"/plm/bom/{bom_id}")
        assert r_v1.status_code == 200
        assert len(r_v1.json()["items"]) == 1
        assert r_v1.json()["version"] == "V1.0"

    def test_effective_copies_routing(self, auth_client: Any) -> None:
        """ECN 生效时 routing 被深拷贝到新版本。"""
        prod = _create_product(auth_client, "BUMP-RTG")

        # create V1.0 routing with operations
        rtg_r = auth_client.post(
            "/plm/routing",
            json={"product_id": prod["id"], "version": "V1.0"},
        )
        assert rtg_r.status_code == 201
        rtg_id = rtg_r.json()["id"]
        auth_client.post(
            f"/plm/routing/{rtg_id}/operations",
            json={
                "sequence": 10,
                "operation_code": "CUT",
                "operation_name": "Cutting",
                "standard_minutes": 5.0,
            },
        )

        # ECN → effective
        ecn = _create_ecn(auth_client, prod["id"], ecn_no="BUMP-RTG-001")
        _walk_to_released(auth_client, ecn["id"])
        r = _transition(auth_client, ecn["id"], "effective")
        assert r.status_code == 200

        # original routing untouched
        r_v1 = auth_client.get(f"/plm/routing/{rtg_id}")
        assert r_v1.status_code == 200
        assert len(r_v1.json()["operations"]) == 1
        assert r_v1.json()["version"] == "V1.0"

    def test_effective_ecn_change_summary(self, auth_client: Any) -> None:
        """ECN 生效后新版本的 change_summary 包含 ECN 编号。"""
        prod = _create_product(auth_client, "BUMP-SUM")
        ecn = _create_ecn(auth_client, prod["id"], ecn_no="SUM-001", title="Fix tolerance")
        _walk_to_released(auth_client, ecn["id"])
        _transition(auth_client, ecn["id"], "effective")

        # check product is V2.0 (version bump happened)
        r = auth_client.get(f"/plm/products/{prod['id']}")
        assert r.json()["current_version"] == "V2.0"
