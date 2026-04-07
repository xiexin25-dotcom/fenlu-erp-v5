"""Tests for Casbin enforcer (TASK-MGMT-006).

Tests cover:
- Policy CRUD via API
- Role assignment
- enforce() allow/deny
- Superuser bypass (existing behavior)
- Non-superuser denied without policy, allowed with policy
- Tenant isolation
- Policy reload
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.services.enforcer import (
    enforce,
    get_enforcer,
    load_policies_from_db,
    reset_enforcer,
)


@pytest.fixture(autouse=True)
def _reset_casbin() -> None:
    """每个测试重置 enforcer 避免串扰。"""
    reset_enforcer()


# --------------------------------------------------------------------------- #
# Enforcer unit tests (direct service layer)
# --------------------------------------------------------------------------- #


class TestEnforcerService:
    def test_enforce_empty_policy_denies(self) -> None:
        """空策略表 → 拒绝所有。"""
        get_enforcer()  # init
        assert enforce("user1", "tenant1", "mgmt.employee", "read") is False

    def test_enforce_with_direct_policy(self) -> None:
        """直接添加 policy → 允许匹配请求。"""
        e = get_enforcer()
        e.add_policy("user1", "tenant1", "mgmt.employee", "read")
        assert enforce("user1", "tenant1", "mgmt.employee", "read") is True
        assert enforce("user1", "tenant1", "mgmt.employee", "create") is False

    def test_enforce_wildcard_action(self) -> None:
        """action=* 匹配所有动作。"""
        e = get_enforcer()
        e.add_policy("user1", "tenant1", "mgmt.employee", "*")
        assert enforce("user1", "tenant1", "mgmt.employee", "read") is True
        assert enforce("user1", "tenant1", "mgmt.employee", "create") is True
        assert enforce("user1", "tenant1", "mgmt.journal", "read") is False

    def test_enforce_keymatch_resource(self) -> None:
        """keyMatch: mgmt.* 匹配 mgmt.xxx。"""
        e = get_enforcer()
        e.add_policy("user1", "tenant1", "mgmt.*", "*")
        assert enforce("user1", "tenant1", "mgmt.employee", "read") is True
        assert enforce("user1", "tenant1", "mgmt.journal", "create") is True

    def test_enforce_rbac_role(self) -> None:
        """RBAC: 用户通过角色继承获得权限。"""
        e = get_enforcer()
        # 角色策略
        e.add_policy("role:hr", "tenant1", "mgmt.employee", "*")
        e.add_policy("role:hr", "tenant1", "mgmt.payroll", "*")
        # 用户分配角色
        e.add_grouping_policy("user1", "role:hr", "tenant1")

        assert enforce("user1", "tenant1", "mgmt.employee", "read") is True
        assert enforce("user1", "tenant1", "mgmt.payroll", "create") is True
        assert enforce("user1", "tenant1", "mgmt.journal", "read") is False

    def test_enforce_tenant_isolation(self) -> None:
        """不同 tenant 策略互不影响。"""
        e = get_enforcer()
        e.add_policy("user1", "tenantA", "mgmt.employee", "read")

        assert enforce("user1", "tenantA", "mgmt.employee", "read") is True
        assert enforce("user1", "tenantB", "mgmt.employee", "read") is False

    def test_enforce_role_tenant_isolation(self) -> None:
        """角色分配也是 tenant 隔离的。"""
        e = get_enforcer()
        e.add_policy("role:admin", "tenantA", "mgmt.*", "*")
        e.add_grouping_policy("user1", "role:admin", "tenantA")

        assert enforce("user1", "tenantA", "mgmt.employee", "read") is True
        assert enforce("user1", "tenantB", "mgmt.employee", "read") is False


# --------------------------------------------------------------------------- #
# DB integration (load_policies_from_db)
# --------------------------------------------------------------------------- #


class TestEnforcerDBIntegration:
    @pytest.mark.asyncio
    async def test_load_from_db(self, db_session: AsyncSession) -> None:
        """往 casbin_rules 插入数据后 load,enforce 生效。"""
        from packages.management_decision.services.enforcer import add_policy

        await add_policy(
            db_session,
            ptype="p",
            v0="user1",
            v1="tenant1",
            v2="mgmt.employee",
            v3="read",
        )
        await db_session.commit()

        # Reset and reload from DB
        reset_enforcer()
        count = await load_policies_from_db(db_session)
        assert count >= 1
        assert enforce("user1", "tenant1", "mgmt.employee", "read") is True

    @pytest.mark.asyncio
    async def test_add_role_for_user(self, db_session: AsyncSession) -> None:
        from packages.management_decision.services.enforcer import (
            add_policy,
            add_role_for_user,
        )

        await add_policy(
            db_session, ptype="p", v0="role:hr", v1="t1", v2="mgmt.employee", v3="read"
        )
        await add_role_for_user(
            db_session, user_id="u1", role="role:hr", tenant_id="t1"
        )
        await db_session.commit()

        assert enforce("u1", "t1", "mgmt.employee", "read") is True


# --------------------------------------------------------------------------- #
# API integration tests
# --------------------------------------------------------------------------- #


class TestCasbinAPI:
    def test_add_policy_rule(self, auth_client: TestClient) -> None:
        r = auth_client.post(
            "/mgmt/policy/rules",
            json={
                "ptype": "p",
                "v0": "role:finance",
                "v1": "demo_tenant",
                "v2": "mgmt.journal",
                "v3": "create",
            },
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["ptype"] == "p"
        assert data["v0"] == "role:finance"

    def test_list_rules(self, auth_client: TestClient) -> None:
        auth_client.post(
            "/mgmt/policy/rules",
            json={"ptype": "p", "v0": "r1", "v1": "t1", "v2": "mgmt.a", "v3": "read"},
        )
        auth_client.post(
            "/mgmt/policy/rules",
            json={"ptype": "g", "v0": "u1", "v1": "r1", "v2": "t1"},
        )
        r = auth_client.get("/mgmt/policy/rules")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_assign_role(self, auth_client: TestClient) -> None:
        user_id = str(uuid4())
        tenant_id = str(uuid4())
        r = auth_client.post(
            "/mgmt/policy/role-assign",
            json={
                "user_id": user_id,
                "role": "role:admin",
                "tenant_id": tenant_id,
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["ptype"] == "g"
        assert data["v0"] == user_id
        assert data["v1"] == "role:admin"

    def test_reload_policies(self, auth_client: TestClient) -> None:
        # add a rule first
        auth_client.post(
            "/mgmt/policy/rules",
            json={"ptype": "p", "v0": "r1", "v1": "t1", "v2": "mgmt.x", "v3": "r"},
        )
        r = auth_client.post("/mgmt/policy/reload")
        assert r.status_code == 200
        assert r.json()["loaded"] >= 1


# --------------------------------------------------------------------------- #
# End-to-end: non-superuser blocked/allowed
# --------------------------------------------------------------------------- #


class TestRequirePermissionE2E:
    def test_superuser_bypasses_casbin(self, auth_client: TestClient) -> None:
        """Superuser (auth_client) 始终可以访问,无需任何策略。"""
        r = auth_client.get("/mgmt/finance/accounts")
        assert r.status_code == 200

    def test_non_superuser_denied_without_policy(
        self, client: TestClient, seed_admin: dict[str, Any], db_session: AsyncSession
    ) -> None:
        """创建一个 non-superuser,没有策略 → 403。"""
        from packages.shared.auth import hash_password
        from packages.shared.models import User

        import asyncio

        async def _setup() -> str:
            user = User(
                tenant_id=seed_admin["tenant_id"],
                username="normal_user",
                full_name="Normal",
                password_hash=hash_password("pass1234"),
                is_superuser=False,
            )
            db_session.add(user)
            await db_session.commit()
            return str(user.id)

        asyncio.get_event_loop().run_until_complete(_setup())

        # login as normal user
        r = client.post(
            "/auth/login",
            json={
                "tenant_code": seed_admin["tenant_code"],
                "username": "normal_user",
                "password": "pass1234",
            },
        )
        assert r.status_code == 200
        token = r.json()["access_token"]

        # try access → 403
        r2 = client.get(
            "/mgmt/finance/accounts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 403
