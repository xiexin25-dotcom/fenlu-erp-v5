"""Tests for TASK-PLM-006: Customer 360 model."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


def _create_customer(auth_client: Any, code: str = "CUST-001", name: str = "Acme Corp") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/customers",
        json={"code": code, "name": name, "kind": "b2b", "rating": "A"},
    )
    assert r.status_code == 201, r.text
    return r.json()


class TestCustomerCRUD:
    def test_create_customer(self, auth_client: Any) -> None:
        data = _create_customer(auth_client)
        assert data["code"] == "CUST-001"
        assert data["name"] == "Acme Corp"
        assert data["kind"] == "b2b"
        assert data["rating"] == "A"
        assert data["is_online"] is False

    def test_create_requires_auth(self, client: Any) -> None:
        r = client.post("/plm/customers", json={"code": "X", "name": "X", "kind": "b2b"})
        assert r.status_code == 401

    def test_get_customer(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "GET-C")
        r = auth_client.get(f"/plm/customers/{cust['id']}")
        assert r.status_code == 200
        assert r.json()["code"] == "GET-C"

    def test_get_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.get(f"/plm/customers/{fake}")
        assert r.status_code == 404


class TestContact:
    def test_add_contact(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "CONT-C")
        r = auth_client.post(
            f"/plm/customers/{cust['id']}/contacts",
            json={"name": "John Doe", "title": "CTO", "phone": "1234567890", "is_primary": True},
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == "John Doe"
        assert data["is_primary"] is True

    def test_contacts_in_customer(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "CONT-IN")
        auth_client.post(
            f"/plm/customers/{cust['id']}/contacts",
            json={"name": "Alice"},
        )
        auth_client.post(
            f"/plm/customers/{cust['id']}/contacts",
            json={"name": "Bob"},
        )
        r = auth_client.get(f"/plm/customers/{cust['id']}")
        assert r.status_code == 200
        assert len(r.json()["contacts"]) == 2


class TestCustomer360:
    def _seed_crm_data(
        self,
        db_session: AsyncSession,
        tenant_id: Any,
        customer_id: Any,
    ) -> None:
        """Directly insert CRM records into DB for 360 aggregation test."""
        import asyncio

        from packages.product_lifecycle.models import Lead, Opportunity, SalesOrder, ServiceTicket

        async def _insert() -> None:
            # 2 leads
            for i in range(2):
                db_session.add(Lead(
                    tenant_id=tenant_id, customer_id=customer_id,
                    title=f"Lead {i}", source="web",
                ))
            # 3 opportunities
            for i in range(3):
                db_session.add(Opportunity(
                    tenant_id=tenant_id, customer_id=customer_id,
                    title=f"Opp {i}",
                ))
            # 1 order
            db_session.add(SalesOrder(
                tenant_id=tenant_id, customer_id=customer_id,
                order_no="SO-001", total_amount=Decimal("1000"),
            ))
            # 2 tickets
            for i in range(2):
                db_session.add(ServiceTicket(
                    tenant_id=tenant_id, customer_id=customer_id,
                    ticket_no=f"TK-{i:03d}",
                ))
            await db_session.flush()

        # Run in current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context via TestClient
            # Use a synchronous approach via the session directly
            pass
        # Since TestClient runs sync, we need a different approach
        # Just use the sync insert pattern via auth_client

    def test_360_empty(self, auth_client: Any) -> None:
        """客户无关联数据时,counts 全为 0,activities 为空。"""
        cust = _create_customer(auth_client, "360-EMPTY")
        r = auth_client.get(f"/plm/customers/{cust['id']}/360")
        assert r.status_code == 200
        data = r.json()
        assert data["customer"]["code"] == "360-EMPTY"
        assert data["counts"]["leads"] == 0
        assert data["counts"]["opportunities"] == 0
        assert data["counts"]["orders"] == 0
        assert data["counts"]["tickets"] == 0
        assert data["recent_activities"] == []

    def test_360_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.get(f"/plm/customers/{fake}/360")
        assert r.status_code == 404

    def test_360_with_data(self, auth_client: Any, db_session: AsyncSession, seed_admin: dict[str, Any]) -> None:
        """有关联数据时验证 counts 和 recent_activities。"""
        import asyncio
        from uuid import UUID as _UUID

        from packages.product_lifecycle.models import Lead, Opportunity, SalesOrder, ServiceTicket

        cust = _create_customer(auth_client, "360-DATA")
        cid = _UUID(cust["id"])
        tid = seed_admin["tenant_id"]

        # Insert CRM data directly
        async def _seed() -> None:
            for i in range(2):
                db_session.add(Lead(tenant_id=tid, customer_id=cid, title=f"Lead {i}"))
            for i in range(3):
                db_session.add(Opportunity(tenant_id=tid, customer_id=cid, title=f"Opp {i}"))
            db_session.add(SalesOrder(
                tenant_id=tid, customer_id=cid, order_no="SO-360",
                total_amount=Decimal("5000"),
            ))
            db_session.add(ServiceTicket(tenant_id=tid, customer_id=cid, ticket_no="TK-360"))
            await db_session.flush()

        asyncio.get_event_loop().run_until_complete(_seed())

        r = auth_client.get(f"/plm/customers/{cid}/360")
        assert r.status_code == 200
        data = r.json()
        assert data["counts"]["leads"] == 2
        assert data["counts"]["opportunities"] == 3
        assert data["counts"]["orders"] == 1
        assert data["counts"]["tickets"] == 1
        assert len(data["recent_activities"]) == 7  # 2+3+1+1
        # 每条 activity 都有 type, id, title, status, created_at
        for act in data["recent_activities"]:
            assert "type" in act
            assert "id" in act
            assert "title" in act
            assert "status" in act
            assert "created_at" in act

    def test_360_recent_limit(self, auth_client: Any, db_session: AsyncSession, seed_admin: dict[str, Any]) -> None:
        """recent_activities 最多返回 10 条。"""
        import asyncio
        from uuid import UUID as _UUID

        from packages.product_lifecycle.models import Lead

        cust = _create_customer(auth_client, "360-LIM")
        cid = _UUID(cust["id"])
        tid = seed_admin["tenant_id"]

        async def _seed() -> None:
            for i in range(15):
                db_session.add(Lead(tenant_id=tid, customer_id=cid, title=f"Lead {i}"))
            await db_session.flush()

        asyncio.get_event_loop().run_until_complete(_seed())

        r = auth_client.get(f"/plm/customers/{cid}/360")
        assert r.status_code == 200
        data = r.json()
        assert data["counts"]["leads"] == 15  # count 是完整的
        assert len(data["recent_activities"]) == 10  # 但 activities 限制 10

    def test_360_includes_contacts(self, auth_client: Any) -> None:
        """360 的 customer 对象应包含 contacts。"""
        cust = _create_customer(auth_client, "360-CON")
        auth_client.post(
            f"/plm/customers/{cust['id']}/contacts",
            json={"name": "Jane"},
        )
        r = auth_client.get(f"/plm/customers/{cust['id']}/360")
        assert r.status_code == 200
        assert len(r.json()["customer"]["contacts"]) == 1
        assert r.json()["customer"]["contacts"][0]["name"] == "Jane"
