"""Tests for TASK-SCM-004: BOM-driven purchase with mocked Lane 1."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    SupplierCreate,
    SupplierProductCreate,
)
from packages.supply_chain.services.bom_client import InMemoryBOMClient
from packages.supply_chain.services.event_publisher import InMemoryPublisher
from packages.supply_chain.services.purchase_service import PurchaseService
from packages.supply_chain.services.supplier_service import SupplierService

# Fixed UUIDs for test reproducibility
BOM_ID = uuid4()
PRODUCT_A = uuid4()  # component: bolts
PRODUCT_B = uuid4()  # component: nuts
PRODUCT_C = uuid4()  # component: no supplier mapped
FINISHED_PRODUCT = uuid4()


def _make_bom_data() -> dict:
    """Simulate a Lane 1 BOMDTO response."""
    return {
        "id": str(BOM_ID),
        "product_id": str(FINISHED_PRODUCT),
        "product_code": "FP-001",
        "version": "1.0",
        "status": "approved",
        "items": [
            {
                "component_id": str(PRODUCT_A),
                "component_code": "BOLT-M8",
                "component_name": "M8 Bolt",
                "quantity": {"value": "10.0000", "uom": "pcs"},
                "scrap_rate": 0.05,
                "is_optional": False,
            },
            {
                "component_id": str(PRODUCT_B),
                "component_code": "NUT-M8",
                "component_name": "M8 Nut",
                "quantity": {"value": "10.0000", "uom": "pcs"},
                "scrap_rate": 0.02,
                "is_optional": False,
            },
            {
                "component_id": str(PRODUCT_C),
                "component_code": "WASHER-M8",
                "component_name": "M8 Washer",
                "quantity": {"value": "20.0000", "uom": "pcs"},
                "scrap_rate": 0.0,
                "is_optional": False,
            },
        ],
        "total_cost": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest_asyncio.fixture
async def tenant_id(db_session: AsyncSession):
    from packages.shared.models import Tenant

    t = Tenant(code="bom-test", name="BOM Test Co")
    db_session.add(t)
    await db_session.flush()
    return t.id


@pytest_asyncio.fixture
async def bom_client():
    client = InMemoryBOMClient()
    client.register_bom(_make_bom_data())
    return client


@pytest_asyncio.fixture
async def publisher():
    return InMemoryPublisher()


@pytest_asyncio.fixture
async def supplier_ids(db_session: AsyncSession, tenant_id):
    """Create two suppliers: S1 (preferred for PRODUCT_A), S2 (preferred for PRODUCT_B)."""
    sup_svc = SupplierService(db_session)
    s1 = await sup_svc.create_supplier(tenant_id, SupplierCreate(code="S-BOM-01", name="Bolt Supplier"))
    s2 = await sup_svc.create_supplier(tenant_id, SupplierCreate(code="S-BOM-02", name="Nut Supplier"))
    return s1.id, s2.id


@pytest_asyncio.fixture
async def svc(db_session: AsyncSession, publisher, bom_client):
    return PurchaseService(db_session, event_publisher=publisher, bom_client=bom_client)


@pytest_asyncio.fixture
async def setup_asl(svc: PurchaseService, tenant_id, supplier_ids):
    """Set up Approved Supplier List: S1→PRODUCT_A, S2→PRODUCT_B. PRODUCT_C unmapped."""
    s1_id, s2_id = supplier_ids
    await svc.create_supplier_product(tenant_id, SupplierProductCreate(
        supplier_id=s1_id, product_id=PRODUCT_A, is_preferred=True,
    ))
    await svc.create_supplier_product(tenant_id, SupplierProductCreate(
        supplier_id=s2_id, product_id=PRODUCT_B, is_preferred=True,
    ))
    return s1_id, s2_id


class TestBOMPurchase:
    @pytest.mark.asyncio
    async def test_purchase_from_bom_creates_prs(
        self, svc: PurchaseService, tenant_id, setup_asl,
    ) -> None:
        s1_id, s2_id = setup_asl
        prs, unmapped = await svc.purchase_from_bom(
            tenant_id=tenant_id,
            bom_id=BOM_ID,
            target_quantity=Decimal("100"),
            target_uom="pcs",
            needed_by=datetime(2026, 5, 1, tzinfo=timezone.utc),
            requested_by=uuid4(),
        )

        # 2 PRs (one per supplier), 1 unmapped product
        assert len(prs) == 2
        assert len(unmapped) == 1
        assert PRODUCT_C in unmapped

        # Each PR should be draft status
        for pr in prs:
            assert pr.status == "draft"
            assert "BOM-driven" in (pr.remark or "")

    @pytest.mark.asyncio
    async def test_bom_quantities_include_scrap(
        self, svc: PurchaseService, tenant_id, setup_asl,
    ) -> None:
        prs, _ = await svc.purchase_from_bom(
            tenant_id=tenant_id,
            bom_id=BOM_ID,
            target_quantity=Decimal("100"),
            target_uom="pcs",
            needed_by=datetime(2026, 5, 1, tzinfo=timezone.utc),
            requested_by=uuid4(),
        )

        # Find PRs and check quantities
        all_lines = []
        for pr in prs:
            all_lines.extend(pr.lines)

        line_map = {ln.product_id: ln.quantity for ln in all_lines}

        # PRODUCT_A: 10 * 100 * (1 + 0.05) = 1050
        assert line_map[PRODUCT_A] == Decimal("1050.0000")

        # PRODUCT_B: 10 * 100 * (1 + 0.02) = 1020
        assert line_map[PRODUCT_B] == Decimal("1020.0000")

    @pytest.mark.asyncio
    async def test_bom_grouping_by_supplier(
        self, svc: PurchaseService, tenant_id, setup_asl, supplier_ids,
    ) -> None:
        """Each PR should contain only lines for one supplier."""
        s1_id, s2_id = supplier_ids
        prs, _ = await svc.purchase_from_bom(
            tenant_id=tenant_id,
            bom_id=BOM_ID,
            target_quantity=Decimal("50"),
            target_uom="pcs",
            needed_by=datetime(2026, 6, 1, tzinfo=timezone.utc),
            requested_by=uuid4(),
        )

        # Exactly 2 PRs, one with PRODUCT_A, one with PRODUCT_B
        pr_products = [
            {ln.product_id for ln in pr.lines}
            for pr in prs
        ]
        assert {PRODUCT_A} in pr_products
        assert {PRODUCT_B} in pr_products

    @pytest.mark.asyncio
    async def test_bom_not_found(self, svc: PurchaseService, tenant_id) -> None:
        with pytest.raises(ValueError, match="not found"):
            await svc.purchase_from_bom(
                tenant_id=tenant_id,
                bom_id=uuid4(),  # nonexistent
                target_quantity=Decimal("10"),
                target_uom="pcs",
                needed_by=datetime(2026, 5, 1, tzinfo=timezone.utc),
                requested_by=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_all_products_unmapped(
        self, svc: PurchaseService, tenant_id, bom_client,
    ) -> None:
        """No supplier mappings → 0 PRs, all unmapped."""
        prs, unmapped = await svc.purchase_from_bom(
            tenant_id=tenant_id,
            bom_id=BOM_ID,
            target_quantity=Decimal("10"),
            target_uom="pcs",
            needed_by=datetime(2026, 5, 1, tzinfo=timezone.utc),
            requested_by=uuid4(),
        )
        assert len(prs) == 0
        assert len(unmapped) == 3

    @pytest.mark.asyncio
    async def test_same_supplier_multiple_products(
        self, svc: PurchaseService, tenant_id, supplier_ids,
    ) -> None:
        """Both products mapped to same supplier → single PR with 2 lines."""
        s1_id, _ = supplier_ids
        await svc.create_supplier_product(tenant_id, SupplierProductCreate(
            supplier_id=s1_id, product_id=PRODUCT_A, is_preferred=True,
        ))
        await svc.create_supplier_product(tenant_id, SupplierProductCreate(
            supplier_id=s1_id, product_id=PRODUCT_B, is_preferred=True,
        ))

        prs, unmapped = await svc.purchase_from_bom(
            tenant_id=tenant_id,
            bom_id=BOM_ID,
            target_quantity=Decimal("10"),
            target_uom="pcs",
            needed_by=datetime(2026, 5, 1, tzinfo=timezone.utc),
            requested_by=uuid4(),
        )

        assert len(prs) == 1
        assert len(prs[0].lines) == 2
        assert len(unmapped) == 1  # PRODUCT_C still unmapped


class TestSupplierProduct:
    @pytest.mark.asyncio
    async def test_create_supplier_product(
        self, svc: PurchaseService, tenant_id, supplier_ids,
    ) -> None:
        s1_id, _ = supplier_ids
        sp = await svc.create_supplier_product(tenant_id, SupplierProductCreate(
            supplier_id=s1_id,
            product_id=uuid4(),
            is_preferred=True,
            lead_days=14,
            reference_price=Decimal("25.50"),
        ))
        assert sp.is_preferred is True
        assert sp.lead_days == 14
        assert sp.reference_price == Decimal("25.50")

    @pytest.mark.asyncio
    async def test_preferred_supplier_lookup(
        self, svc: PurchaseService, tenant_id, supplier_ids,
    ) -> None:
        s1_id, s2_id = supplier_ids
        pid = uuid4()
        # S2 not preferred, S1 preferred
        await svc.create_supplier_product(tenant_id, SupplierProductCreate(
            supplier_id=s2_id, product_id=pid, is_preferred=False,
        ))
        await svc.create_supplier_product(tenant_id, SupplierProductCreate(
            supplier_id=s1_id, product_id=pid, is_preferred=True,
        ))

        result = await svc.get_preferred_suppliers(tenant_id, [pid])
        assert pid in result
        assert result[pid].supplier_id == s1_id  # preferred wins
