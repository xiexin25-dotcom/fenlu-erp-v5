"""Tests for TASK-PLM-008: Quote → Contract → Order + SalesOrderConfirmedEvent."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


def _create_customer(auth_client: Any, code: str = "QO-C") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/customers",
        json={"code": code, "name": "Order Customer", "kind": "b2b"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_product(auth_client: Any, code: str = "QO-P") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/products",
        json={"code": code, "name": "Order Product", "category": "self_made", "uom": "pcs"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_quote(auth_client: Any, customer_id: str, quote_no: str = "QT-001") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/crm/quotes",
        json={"customer_id": customer_id, "quote_no": quote_no},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _add_quote_item(
    auth_client: Any, quote_id: str, product_id: str,
    quantity: str = "10.0000", unit_price: str = "100.0000",
) -> dict[str, Any]:
    r = auth_client.post(
        f"/plm/crm/quotes/{quote_id}/items",
        json={
            "product_id": product_id,
            "quantity": quantity,
            "uom": "pcs",
            "unit_price": unit_price,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _transition_quote(auth_client: Any, quote_id: str, target: str, **kwargs: Any) -> Any:
    body: dict[str, Any] = {"target_status": target, **kwargs}
    return auth_client.post(f"/plm/crm/quotes/{quote_id}/transition", json=body)


# ── Quote CRUD ────────────────────────────────────────────────────────────── #


class TestQuoteCRUD:
    def test_create_quote(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "QC-CR")
        quote = _create_quote(auth_client, cust["id"], "QT-CR-001")
        assert quote["quote_no"] == "QT-CR-001"
        assert quote["status"] == "draft"
        assert Decimal(quote["total_amount"]) == Decimal("0")
        assert quote["items"] == []

    def test_get_quote(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "QC-GET")
        quote = _create_quote(auth_client, cust["id"], "QT-GET")
        r = auth_client.get(f"/plm/crm/quotes/{quote['id']}")
        assert r.status_code == 200
        assert r.json()["quote_no"] == "QT-GET"

    def test_get_not_found(self, auth_client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000099"
        r = auth_client.get(f"/plm/crm/quotes/{fake}")
        assert r.status_code == 404

    def test_requires_auth(self, client: Any) -> None:
        fake = "00000000-0000-0000-0000-000000000001"
        r = client.post("/plm/crm/quotes", json={"customer_id": fake, "quote_no": "X"})
        assert r.status_code == 401


class TestQuoteItems:
    def test_add_item_and_total(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "QI-ADD")
        prod = _create_product(auth_client, "QI-P")
        quote = _create_quote(auth_client, cust["id"], "QT-ITEM")

        item = _add_quote_item(auth_client, quote["id"], prod["id"], "10.0000", "100.0000")
        assert Decimal(item["quantity"]) == Decimal("10.0000")
        assert Decimal(item["unit_price"]) == Decimal("100.0000")
        assert Decimal(item["line_total"]) == Decimal("1000.0000")

        # total_amount should be updated
        r = auth_client.get(f"/plm/crm/quotes/{quote['id']}")
        assert Decimal(r.json()["total_amount"]) == Decimal("1000.0000")

    def test_multiple_items_total(self, auth_client: Any) -> None:
        cust = _create_customer(auth_client, "QI-MULTI")
        p1 = _create_product(auth_client, "QI-P1")
        p2 = _create_product(auth_client, "QI-P2")
        quote = _create_quote(auth_client, cust["id"], "QT-MULTI")

        _add_quote_item(auth_client, quote["id"], p1["id"], "5.0000", "200.0000")  # 1000
        _add_quote_item(auth_client, quote["id"], p2["id"], "3.0000", "50.0000")   # 150

        r = auth_client.get(f"/plm/crm/quotes/{quote['id']}")
        assert Decimal(r.json()["total_amount"]) == Decimal("1150.0000")
        assert len(r.json()["items"]) == 2


# ── Quote transitions ─────────────────────────────────────────────────────── #


class TestQuoteTransitions:
    def test_happy_path_to_contracted(self, auth_client: Any) -> None:
        """draft → submitted → approved → contracted"""
        cust = _create_customer(auth_client, "QT-HP")
        quote = _create_quote(auth_client, cust["id"], "QT-HP-001")
        qid = quote["id"]

        for target in ("submitted", "approved", "contracted"):
            r = _transition_quote(auth_client, qid, target)
            assert r.status_code == 200, f"{target}: {r.text}"
            assert r.json()["status"] == target

    def test_invalid_transition(self, auth_client: Any) -> None:
        """draft 不能直接 approved。"""
        cust = _create_customer(auth_client, "QT-INV")
        quote = _create_quote(auth_client, cust["id"], "QT-INV-001")
        r = _transition_quote(auth_client, quote["id"], "approved")
        assert r.status_code == 422

    def test_reject_and_resubmit(self, auth_client: Any) -> None:
        """submitted → rejected → draft → submitted"""
        cust = _create_customer(auth_client, "QT-REJ")
        quote = _create_quote(auth_client, cust["id"], "QT-REJ-001")
        qid = quote["id"]

        _transition_quote(auth_client, qid, "submitted")
        r = _transition_quote(auth_client, qid, "rejected")
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

        r = _transition_quote(auth_client, qid, "draft")
        assert r.status_code == 200
        r = _transition_quote(auth_client, qid, "submitted")
        assert r.status_code == 200


# ── Full flow: Quote → Order + Event ──────────────────────────────────────── #


class TestQuoteToOrder:
    @pytest.fixture
    def mock_event_publisher(self) -> Any:
        """Mock Redis event publisher."""
        mock = AsyncMock(return_value="mock-stream-id")
        with patch(
            "packages.product_lifecycle.services.event_publisher.publish_event",
            mock,
        ) as m:
            yield m

    def _setup_contracted_quote(self, auth_client: Any) -> tuple[str, str]:
        """创建一个到 contracted 状态的 quote,返回 (quote_id, customer_id)。"""
        cust = _create_customer(auth_client, f"QTO-{id(self)}")
        prod = _create_product(auth_client, f"QTO-P-{id(self)}")
        quote = _create_quote(auth_client, cust["id"], f"QT-{id(self)}")
        _add_quote_item(auth_client, quote["id"], prod["id"], "5.0000", "200.0000")

        for target in ("submitted", "approved", "contracted"):
            r = _transition_quote(auth_client, quote["id"], target)
            assert r.status_code == 200, r.text

        return quote["id"], cust["id"]

    def test_ordered_creates_sales_order(self, auth_client: Any, mock_event_publisher: Any) -> None:
        """contracted → ordered 应自动创建 SalesOrder。"""
        qid, _ = self._setup_contracted_quote(auth_client)

        r = _transition_quote(auth_client, qid, "ordered", promised_delivery="2026-05-01T00:00:00Z")
        assert r.status_code == 200
        assert r.json()["status"] == "ordered"

    def test_order_has_lines(self, auth_client: Any, mock_event_publisher: Any) -> None:
        """创建的 SalesOrder 应包含从 Quote 复制的行项。"""
        qid, cid = self._setup_contracted_quote(auth_client)
        _transition_quote(auth_client, qid, "ordered")

        # 获取 quote 查看 quote_no → 推导 order_no
        quote_r = auth_client.get(f"/plm/crm/quotes/{qid}")
        quote_no = quote_r.json()["quote_no"]
        expected_order_no = quote_no.replace("QT-", "SO-", 1)

        # 通过搜索找到 order — 用 customer 360 或直接查
        # 由于我们没有 list orders API,直接用 DB 查找间接验证
        # mock_event_publisher 被调用说明 order 已创建并 confirmed
        mock_event_publisher.assert_called_once()
        event_data = mock_event_publisher.call_args[0][0]
        order_id = event_data["sales_order_id"]

        r = auth_client.get(f"/plm/crm/orders/{order_id}")
        assert r.status_code == 200
        order = r.json()
        assert order["status"] == "confirmed"
        assert Decimal(order["total_amount"]) == Decimal("1000.0000")
        assert len(order["lines"]) == 1
        assert Decimal(order["lines"][0]["quantity"]) == Decimal("5.0000")

    def test_event_emitted(self, auth_client: Any, mock_event_publisher: Any) -> None:
        """order confirm 应 emit SalesOrderConfirmedEvent。"""
        qid, cid = self._setup_contracted_quote(auth_client)
        _transition_quote(auth_client, qid, "ordered")

        mock_event_publisher.assert_called_once()
        event_data = mock_event_publisher.call_args[0][0]
        assert event_data["event_type"] == "sales_order.confirmed"
        assert event_data["source_lane"] == "plm"
        assert event_data["customer_id"] == cid
        assert "sales_order_id" in event_data
        assert "total_amount" in event_data

    def test_ordered_is_terminal(self, auth_client: Any, mock_event_publisher: Any) -> None:
        """ordered 是终态,不能再转换。"""
        qid, _ = self._setup_contracted_quote(auth_client)
        _transition_quote(auth_client, qid, "ordered")

        r = _transition_quote(auth_client, qid, "draft")
        assert r.status_code == 422
