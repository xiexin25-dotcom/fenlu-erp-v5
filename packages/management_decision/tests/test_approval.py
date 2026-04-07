"""Tests for Approval flow engine (TASK-MGMT-005)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _get_user_id(auth_client: TestClient) -> str:
    """获取当前登录用户 ID (admin)。"""
    r = auth_client.get("/auth/me")
    assert r.status_code == 200
    return r.json()["id"]


def _create_definition(
    auth_client: TestClient,
    *,
    business_type: str = "purchase_order",
    approver_ids: list[str] | None = None,
) -> dict:
    """创建审批定义。默认 2-step 用当前用户做审批人。"""
    uid = _get_user_id(auth_client)
    if approver_ids is None:
        approver_ids = [uid, uid]  # 2 步都用 admin
    steps = [
        {"step_no": i + 1, "name": f"第{i + 1}步审批", "approver_id": aid}
        for i, aid in enumerate(approver_ids)
    ]
    r = auth_client.post(
        "/mgmt/approval/definitions",
        json={
            "business_type": business_type,
            "name": f"{business_type} 审批流",
            "steps_config": steps,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _submit(
    auth_client: TestClient,
    *,
    business_type: str = "purchase_order",
    business_id: str | None = None,
) -> dict:
    r = auth_client.post(
        "/mgmt/approval",
        json={
            "business_type": business_type,
            "business_id": business_id or str(uuid4()),
            "payload": {"amount": 10000, "desc": "test"},
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# Definition CRUD
# --------------------------------------------------------------------------- #


class TestApprovalDefinition:
    def test_create_definition(self, auth_client: TestClient) -> None:
        data = _create_definition(auth_client)
        assert data["business_type"] == "purchase_order"
        assert len(data["steps_config"]) == 2
        assert data["is_active"] is True

    def test_list_definitions(self, auth_client: TestClient) -> None:
        _create_definition(auth_client, business_type="po1")
        _create_definition(auth_client, business_type="po2")
        r = auth_client.get("/mgmt/approval/definitions")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_get_definition(self, auth_client: TestClient) -> None:
        defn = _create_definition(auth_client)
        r = auth_client.get(f"/mgmt/approval/definitions/{defn['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == defn["id"]

    def test_get_definition_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get(f"/mgmt/approval/definitions/{uuid4()}")
        assert r.status_code == 404


# --------------------------------------------------------------------------- #
# Submit
# --------------------------------------------------------------------------- #


class TestApprovalSubmit:
    def test_submit_creates_instance_and_steps(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        data = _submit(auth_client)
        assert data["status"] == "pending"
        assert data["current_step"] == 1
        assert data["total_steps"] == 2
        assert len(data["steps"]) == 2
        assert data["steps"][0]["status"] == "waiting"
        assert data["steps"][1]["status"] == "waiting"

    def test_submit_without_definition_422(self, auth_client: TestClient) -> None:
        r = auth_client.post(
            "/mgmt/approval",
            json={
                "business_type": "nonexistent",
                "business_id": str(uuid4()),
                "payload": {},
            },
        )
        assert r.status_code == 422
        assert "未找到" in r.json()["detail"]

    def test_submit_preserves_payload(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        data = _submit(auth_client)
        assert data["payload"]["amount"] == 10000


# --------------------------------------------------------------------------- #
# Linear N-step approve flow
# --------------------------------------------------------------------------- #


class TestApprovalFlow:
    def test_approve_step_1_advances(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        inst = _submit(auth_client)

        r = auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "approve", "comment": "同意"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["current_step"] == 2
        assert data["status"] == "pending"
        assert data["steps"][0]["status"] == "approved"
        assert data["steps"][0]["comment"] == "同意"
        assert data["steps"][1]["status"] == "waiting"

    def test_approve_all_steps_completes(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        inst = _submit(auth_client)

        # step 1
        auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "approve"},
        )
        # step 2
        r = auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "approve"},
        )
        data = r.json()
        assert data["status"] == "approved"
        assert data["completed_at"] is not None
        assert data["steps"][0]["status"] == "approved"
        assert data["steps"][1]["status"] == "approved"

    def test_reject_at_step_1(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        inst = _submit(auth_client)

        r = auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "reject", "comment": "金额太大"},
        )
        data = r.json()
        assert data["status"] == "rejected"
        assert data["completed_at"] is not None
        assert data["steps"][0]["status"] == "rejected"
        assert data["steps"][0]["comment"] == "金额太大"

    def test_reject_at_step_2(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        inst = _submit(auth_client)

        auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "approve"},
        )
        r = auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "reject"},
        )
        data = r.json()
        assert data["status"] == "rejected"
        assert data["steps"][0]["status"] == "approved"
        assert data["steps"][1]["status"] == "rejected"

    def test_3_step_approval(self, auth_client: TestClient) -> None:
        uid = _get_user_id(auth_client)
        _create_definition(
            auth_client,
            business_type="three_step",
            approver_ids=[uid, uid, uid],
        )
        inst = _submit(auth_client, business_type="three_step")
        assert inst["total_steps"] == 3

        for i in range(3):
            r = auth_client.post(
                f"/mgmt/approval/{inst['id']}/action",
                json={"action": "approve"},
            )
        assert r.json()["status"] == "approved"

    def test_withdraw(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        inst = _submit(auth_client)

        r = auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "withdraw"},
        )
        assert r.json()["status"] == "withdrawn"
        assert r.json()["completed_at"] is not None

    def test_action_on_completed_422(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        inst = _submit(auth_client)

        # reject
        auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "reject"},
        )
        # try approve on rejected
        r = auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "approve"},
        )
        assert r.status_code == 422
        assert "已结束" in r.json()["detail"]

    def test_wrong_approver_422(self, auth_client: TestClient) -> None:
        """使用 random UUID 作为审批人,当前用户不匹配 → 422。"""
        random_id = str(uuid4())
        uid = _get_user_id(auth_client)
        # step 1: admin (can approve), step 2: random (admin cannot approve)
        _create_definition(
            auth_client,
            business_type="restricted",
            approver_ids=[uid, random_id],
        )
        inst = _submit(auth_client, business_type="restricted")

        # step 1 OK
        auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "approve"},
        )
        # step 2 - wrong approver
        r = auth_client.post(
            f"/mgmt/approval/{inst['id']}/action",
            json={"action": "approve"},
        )
        assert r.status_code == 422
        assert "审批人" in r.json()["detail"]


# --------------------------------------------------------------------------- #
# Query
# --------------------------------------------------------------------------- #


class TestApprovalQuery:
    def test_list_instances(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        _submit(auth_client)
        _submit(auth_client)

        r = auth_client.get("/mgmt/approval")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_list_filter_by_status(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        inst1 = _submit(auth_client)
        _submit(auth_client)

        # approve inst1 fully
        auth_client.post(
            f"/mgmt/approval/{inst1['id']}/action", json={"action": "approve"}
        )
        auth_client.post(
            f"/mgmt/approval/{inst1['id']}/action", json={"action": "approve"}
        )

        r = auth_client.get("/mgmt/approval", params={"status": "pending"})
        assert len(r.json()) == 1

        r2 = auth_client.get("/mgmt/approval", params={"status": "approved"})
        assert len(r2.json()) == 1

    def test_get_instance(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        inst = _submit(auth_client)

        r = auth_client.get(f"/mgmt/approval/{inst['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == inst["id"]

    def test_get_instance_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get(f"/mgmt/approval/{uuid4()}")
        assert r.status_code == 404

    def test_pending_for_approver(self, auth_client: TestClient) -> None:
        _create_definition(auth_client)
        _submit(auth_client)

        r = auth_client.get("/mgmt/approval/pending")
        assert r.status_code == 200
        assert len(r.json()) == 1
