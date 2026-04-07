"""Tests for SCM purchase chain: PR → RFQ → PO → Receipt."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    POCreate,
    POLineCreate,
    PRCreate,
    PRLineCreate,
    ReceiptCreate,
    ReceiptLineCreate,
    RFQCreate,
    RFQLineCreate,
    RFQLineUpdate,
    SupplierCreate,
)
from packages.supply_chain.models.purchase import validate_transition
from packages.supply_chain.services.event_publisher import InMemoryPublisher
from packages.supply_chain.services.purchase_service import PurchaseService
from packages.supply_chain.services.supplier_service import SupplierService


@pytest_asyncio.fixture
async def tenant_id(db_session: AsyncSession):
    from packages.shared.models import Tenant

    t = Tenant(code="test-pur", name="Test Purchase Co")
    db_session.add(t)
    await db_session.flush()
    return t.id


@pytest_asyncio.fixture
async def supplier_id(db_session: AsyncSession, tenant_id):
    svc = SupplierService(db_session)
    s = await svc.create_supplier(tenant_id, SupplierCreate(code="S-001", name="Test Supplier"))
    return s.id


@pytest_asyncio.fixture
async def publisher():
    return InMemoryPublisher()


@pytest_asyncio.fixture
async def svc(db_session: AsyncSession, publisher: InMemoryPublisher):
    return PurchaseService(db_session, event_publisher=publisher)


PRODUCT_ID = uuid4()


# ================================================================== #
# validate_transition
# ================================================================== #


class TestValidateTransition:
    def test_valid_pr_transition(self) -> None:
        validate_transition("purchase_request", "draft", "submitted")

    def test_invalid_pr_transition(self) -> None:
        with pytest.raises(ValueError, match="not allowed"):
            validate_transition("purchase_request", "draft", "approved")

    def test_valid_po_transition(self) -> None:
        validate_transition("purchase_order", "submitted", "approved")

    def test_terminal_state(self) -> None:
        with pytest.raises(ValueError, match="not allowed"):
            validate_transition("purchase_order", "closed", "draft")

    def test_rfq_transitions(self) -> None:
        validate_transition("rfq", "draft", "sent")
        validate_transition("rfq", "sent", "responded")
        validate_transition("rfq", "responded", "closed")

    def test_receipt_transitions(self) -> None:
        validate_transition("purchase_receipt", "draft", "confirmed")
        validate_transition("purchase_receipt", "confirmed", "closed")

    def test_rejected_can_go_back_to_draft(self) -> None:
        validate_transition("purchase_request", "rejected", "draft")
        validate_transition("purchase_order", "rejected", "draft")


# ================================================================== #
# Purchase Request
# ================================================================== #


class TestPurchaseRequest:
    @pytest.mark.asyncio
    async def test_create_pr(self, svc: PurchaseService, tenant_id) -> None:
        pr = await svc.create_pr(tenant_id, PRCreate(
            request_no="PR-001",
            lines=[PRLineCreate(product_id=PRODUCT_ID, quantity=Decimal("100"))],
        ))
        assert pr.request_no == "PR-001"
        assert pr.status == "draft"
        assert len(pr.lines) == 1
        assert pr.lines[0].quantity == Decimal("100")

    @pytest.mark.asyncio
    async def test_pr_lifecycle(self, svc: PurchaseService, tenant_id) -> None:
        pr = await svc.create_pr(tenant_id, PRCreate(
            request_no="PR-002",
            lines=[PRLineCreate(product_id=PRODUCT_ID, quantity=Decimal("50"))],
        ))
        pr = await svc.transition_pr(tenant_id, pr.id, "submitted")
        assert pr.status == "submitted"

        pr = await svc.transition_pr(tenant_id, pr.id, "approved")
        assert pr.status == "approved"

        pr = await svc.transition_pr(tenant_id, pr.id, "closed")
        assert pr.status == "closed"

    @pytest.mark.asyncio
    async def test_pr_invalid_transition(self, svc: PurchaseService, tenant_id) -> None:
        pr = await svc.create_pr(tenant_id, PRCreate(
            request_no="PR-003",
            lines=[PRLineCreate(product_id=PRODUCT_ID, quantity=Decimal("10"))],
        ))
        with pytest.raises(ValueError, match="not allowed"):
            await svc.transition_pr(tenant_id, pr.id, "closed")

    @pytest.mark.asyncio
    async def test_pr_not_found(self, svc: PurchaseService, tenant_id) -> None:
        with pytest.raises(ValueError, match="not found"):
            await svc.transition_pr(tenant_id, uuid4(), "submitted")


# ================================================================== #
# RFQ
# ================================================================== #


class TestRFQ:
    @pytest.mark.asyncio
    async def test_create_rfq(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        rfq = await svc.create_rfq(tenant_id, RFQCreate(
            rfq_no="RFQ-001",
            supplier_id=supplier_id,
            lines=[RFQLineCreate(product_id=PRODUCT_ID, quantity=Decimal("100"))],
        ))
        assert rfq.rfq_no == "RFQ-001"
        assert rfq.status == "draft"
        assert len(rfq.lines) == 1

    @pytest.mark.asyncio
    async def test_rfq_lifecycle(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        rfq = await svc.create_rfq(tenant_id, RFQCreate(
            rfq_no="RFQ-002",
            supplier_id=supplier_id,
            lines=[RFQLineCreate(product_id=PRODUCT_ID, quantity=Decimal("200"))],
        ))
        rfq = await svc.transition_rfq(tenant_id, rfq.id, "sent")
        assert rfq.status == "sent"

        rfq = await svc.transition_rfq(tenant_id, rfq.id, "responded")
        assert rfq.status == "responded"

        rfq = await svc.transition_rfq(tenant_id, rfq.id, "closed")
        assert rfq.status == "closed"

    @pytest.mark.asyncio
    async def test_update_rfq_line_price(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        rfq = await svc.create_rfq(tenant_id, RFQCreate(
            rfq_no="RFQ-003",
            supplier_id=supplier_id,
            lines=[RFQLineCreate(product_id=PRODUCT_ID, quantity=Decimal("50"))],
        ))
        line = rfq.lines[0]
        updated = await svc.update_rfq_line_price(
            tenant_id, rfq.id, line.id, RFQLineUpdate(quoted_unit_price=Decimal("12.50")),
        )
        assert updated.quoted_unit_price == Decimal("12.50")


# ================================================================== #
# Purchase Order
# ================================================================== #


class TestPurchaseOrder:
    @pytest.mark.asyncio
    async def test_create_po(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        po = await svc.create_po(tenant_id, POCreate(
            order_no="PO-001",
            supplier_id=supplier_id,
            lines=[POLineCreate(
                product_id=PRODUCT_ID,
                quantity=Decimal("100"),
                unit_price=Decimal("25.00"),
            )],
        ))
        assert po.order_no == "PO-001"
        assert po.status == "draft"
        assert po.total_amount == Decimal("2500.00")
        assert len(po.lines) == 1
        assert po.lines[0].line_total == Decimal("2500.00")

    @pytest.mark.asyncio
    async def test_po_multi_line_total(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        po = await svc.create_po(tenant_id, POCreate(
            order_no="PO-002",
            supplier_id=supplier_id,
            lines=[
                POLineCreate(product_id=PRODUCT_ID, quantity=Decimal("10"), unit_price=Decimal("100")),
                POLineCreate(product_id=uuid4(), quantity=Decimal("5"), unit_price=Decimal("200")),
            ],
        ))
        assert po.total_amount == Decimal("2000")

    @pytest.mark.asyncio
    async def test_po_approval_emits_event(
        self, svc: PurchaseService, tenant_id, supplier_id, publisher: InMemoryPublisher,
    ) -> None:
        po = await svc.create_po(tenant_id, POCreate(
            order_no="PO-003",
            supplier_id=supplier_id,
            lines=[POLineCreate(
                product_id=PRODUCT_ID,
                quantity=Decimal("10"),
                unit_price=Decimal("50"),
            )],
        ))
        await svc.transition_po(tenant_id, po.id, "submitted")
        await svc.transition_po(tenant_id, po.id, "approved")

        assert len(publisher.events) == 1
        event_type, payload = publisher.events[0]
        assert event_type == "po.approved"
        assert payload["purchase_order_id"] == str(po.id)
        assert payload["supplier_id"] == str(supplier_id)
        assert payload["total_amount"] == "500"

    @pytest.mark.asyncio
    async def test_po_invalid_transition(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        po = await svc.create_po(tenant_id, POCreate(
            order_no="PO-004",
            supplier_id=supplier_id,
            lines=[POLineCreate(
                product_id=PRODUCT_ID, quantity=Decimal("1"), unit_price=Decimal("10"),
            )],
        ))
        with pytest.raises(ValueError, match="not allowed"):
            await svc.transition_po(tenant_id, po.id, "approved")

    @pytest.mark.asyncio
    async def test_po_rejected_back_to_draft(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        po = await svc.create_po(tenant_id, POCreate(
            order_no="PO-005",
            supplier_id=supplier_id,
            lines=[POLineCreate(
                product_id=PRODUCT_ID, quantity=Decimal("1"), unit_price=Decimal("10"),
            )],
        ))
        await svc.transition_po(tenant_id, po.id, "submitted")
        await svc.transition_po(tenant_id, po.id, "rejected")
        po = await svc.transition_po(tenant_id, po.id, "draft")
        assert po.status == "draft"


# ================================================================== #
# Purchase Receipt
# ================================================================== #


class TestPurchaseReceipt:
    async def _approved_po(self, svc: PurchaseService, tenant_id, supplier_id, order_no: str = "PO-R01"):
        po = await svc.create_po(tenant_id, POCreate(
            order_no=order_no,
            supplier_id=supplier_id,
            lines=[POLineCreate(
                product_id=PRODUCT_ID, quantity=Decimal("100"), unit_price=Decimal("10"),
            )],
        ))
        await svc.transition_po(tenant_id, po.id, "submitted")
        await svc.transition_po(tenant_id, po.id, "approved")
        return po

    @pytest.mark.asyncio
    async def test_create_receipt(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        po = await self._approved_po(svc, tenant_id, supplier_id)
        receipt = await svc.create_receipt(tenant_id, ReceiptCreate(
            receipt_no="REC-001",
            order_id=po.id,
            supplier_id=supplier_id,
            lines=[ReceiptLineCreate(
                product_id=PRODUCT_ID,
                ordered_quantity=Decimal("100"),
                received_quantity=Decimal("100"),
            )],
        ))
        assert receipt.receipt_no == "REC-001"
        assert receipt.status == "draft"
        assert len(receipt.lines) == 1

    @pytest.mark.asyncio
    async def test_receipt_requires_approved_po(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        po = await svc.create_po(tenant_id, POCreate(
            order_no="PO-R02",
            supplier_id=supplier_id,
            lines=[POLineCreate(
                product_id=PRODUCT_ID, quantity=Decimal("10"), unit_price=Decimal("10"),
            )],
        ))
        with pytest.raises(ValueError, match="must be approved"):
            await svc.create_receipt(tenant_id, ReceiptCreate(
                receipt_no="REC-002",
                order_id=po.id,
                supplier_id=supplier_id,
                lines=[ReceiptLineCreate(
                    product_id=PRODUCT_ID,
                    ordered_quantity=Decimal("10"),
                    received_quantity=Decimal("10"),
                )],
            ))

    @pytest.mark.asyncio
    async def test_confirm_receipt_updates_po_received(
        self, svc: PurchaseService, tenant_id, supplier_id,
    ) -> None:
        po = await self._approved_po(svc, tenant_id, supplier_id, "PO-R03")
        receipt = await svc.create_receipt(tenant_id, ReceiptCreate(
            receipt_no="REC-003",
            order_id=po.id,
            supplier_id=supplier_id,
            lines=[ReceiptLineCreate(
                product_id=PRODUCT_ID,
                ordered_quantity=Decimal("100"),
                received_quantity=Decimal("60"),
            )],
        ))
        await svc.transition_receipt(tenant_id, receipt.id, "confirmed")

        po_refreshed = await svc.get_po(tenant_id, po.id)
        assert po_refreshed is not None
        assert po_refreshed.lines[0].received_quantity == Decimal("60")
        # PO not yet closed (60 < 100)
        assert po_refreshed.status == "approved"

    @pytest.mark.asyncio
    async def test_full_receipt_closes_po(
        self, svc: PurchaseService, tenant_id, supplier_id,
    ) -> None:
        po = await self._approved_po(svc, tenant_id, supplier_id, "PO-R04")
        receipt = await svc.create_receipt(tenant_id, ReceiptCreate(
            receipt_no="REC-004",
            order_id=po.id,
            supplier_id=supplier_id,
            lines=[ReceiptLineCreate(
                product_id=PRODUCT_ID,
                ordered_quantity=Decimal("100"),
                received_quantity=Decimal("100"),
            )],
        ))
        await svc.transition_receipt(tenant_id, receipt.id, "confirmed")

        po_refreshed = await svc.get_po(tenant_id, po.id)
        assert po_refreshed is not None
        assert po_refreshed.status == "closed"

    @pytest.mark.asyncio
    async def test_receipt_not_found_po(self, svc: PurchaseService, tenant_id, supplier_id) -> None:
        with pytest.raises(ValueError, match="not found"):
            await svc.create_receipt(tenant_id, ReceiptCreate(
                receipt_no="REC-005",
                order_id=uuid4(),
                supplier_id=supplier_id,
                lines=[ReceiptLineCreate(
                    product_id=PRODUCT_ID,
                    ordered_quantity=Decimal("10"),
                    received_quantity=Decimal("10"),
                )],
            ))


# ================================================================== #
# Full chain: PR → RFQ → PO → Receipt
# ================================================================== #


class TestFullChain:
    @pytest.mark.asyncio
    async def test_pr_to_receipt(
        self, svc: PurchaseService, tenant_id, supplier_id, publisher: InMemoryPublisher,
    ) -> None:
        # 1. Create and approve PR
        pr = await svc.create_pr(tenant_id, PRCreate(
            request_no="PR-FULL-01",
            lines=[PRLineCreate(product_id=PRODUCT_ID, quantity=Decimal("200"))],
        ))
        await svc.transition_pr(tenant_id, pr.id, "submitted")
        await svc.transition_pr(tenant_id, pr.id, "approved")

        # 2. Create RFQ, send, get response
        rfq = await svc.create_rfq(tenant_id, RFQCreate(
            rfq_no="RFQ-FULL-01",
            supplier_id=supplier_id,
            request_id=pr.id,
            lines=[RFQLineCreate(product_id=PRODUCT_ID, quantity=Decimal("200"))],
        ))
        await svc.transition_rfq(tenant_id, rfq.id, "sent")
        await svc.update_rfq_line_price(
            tenant_id, rfq.id, rfq.lines[0].id,
            RFQLineUpdate(quoted_unit_price=Decimal("15.00")),
        )
        await svc.transition_rfq(tenant_id, rfq.id, "responded")

        # 3. Create PO from RFQ, submit, approve
        po = await svc.create_po(tenant_id, POCreate(
            order_no="PO-FULL-01",
            supplier_id=supplier_id,
            rfq_id=rfq.id,
            lines=[POLineCreate(
                product_id=PRODUCT_ID,
                quantity=Decimal("200"),
                unit_price=Decimal("15.00"),
            )],
        ))
        await svc.transition_po(tenant_id, po.id, "submitted")
        await svc.transition_po(tenant_id, po.id, "approved")

        # Event emitted
        assert len(publisher.events) == 1
        assert publisher.events[0][0] == "po.approved"

        # 4. Receive goods
        receipt = await svc.create_receipt(tenant_id, ReceiptCreate(
            receipt_no="REC-FULL-01",
            order_id=po.id,
            supplier_id=supplier_id,
            lines=[ReceiptLineCreate(
                product_id=PRODUCT_ID,
                ordered_quantity=Decimal("200"),
                received_quantity=Decimal("200"),
            )],
        ))
        await svc.transition_receipt(tenant_id, receipt.id, "confirmed")

        # PO auto-closed
        po_final = await svc.get_po(tenant_id, po.id)
        assert po_final is not None
        assert po_final.status == "closed"

        # Close PR
        await svc.transition_pr(tenant_id, pr.id, "closed")
        pr_final = await svc.get_pr(tenant_id, pr.id)
        assert pr_final is not None
        assert pr_final.status == "closed"

        # Close RFQ
        await svc.transition_rfq(tenant_id, rfq.id, "closed")
        rfq_final = await svc.get_rfq(tenant_id, rfq.id)
        assert rfq_final is not None
        assert rfq_final.status == "closed"
