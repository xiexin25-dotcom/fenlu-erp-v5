"""Tests for TASK-SCM-006: Inventory + StockMove, GET /scm/inventory, POST /scm/issue."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    InventoryListParams,
    StockMoveCreate,
    WarehouseCreate,
)
from packages.supply_chain.services.inventory_service import InventoryService
from packages.supply_chain.services.warehouse_service import WarehouseService

PRODUCT_A = uuid4()
PRODUCT_B = uuid4()


@pytest_asyncio.fixture
async def tenant_id(db_session: AsyncSession):
    from packages.shared.models import Tenant

    t = Tenant(code="inv-test", name="Inventory Test Co")
    db_session.add(t)
    await db_session.flush()
    return t.id


@pytest_asyncio.fixture
async def warehouse_id(db_session: AsyncSession, tenant_id):
    svc = WarehouseService(db_session)
    wh = await svc.create_warehouse(tenant_id, WarehouseCreate(code="WH-INV", name="Inventory WH"))
    return wh.id


@pytest_asyncio.fixture
async def warehouse2_id(db_session: AsyncSession, tenant_id):
    svc = WarehouseService(db_session)
    wh = await svc.create_warehouse(tenant_id, WarehouseCreate(code="WH-INV2", name="Inventory WH 2"))
    return wh.id


@pytest_asyncio.fixture
async def svc(db_session: AsyncSession) -> InventoryService:
    return InventoryService(db_session)


@pytest_asyncio.fixture
async def stocked_inventory(svc: InventoryService, tenant_id, warehouse_id):
    """Pre-stock PRODUCT_A with 500 pcs."""
    await svc.create_move(tenant_id, StockMoveCreate(
        type="purchase_receipt",
        product_id=PRODUCT_A,
        quantity=Decimal("500"),
        warehouse_id=warehouse_id,
    ))
    return tenant_id, warehouse_id


# ================================================================== #
# StockMove → Inventory integration
# ================================================================== #


class TestStockMove:
    @pytest.mark.asyncio
    async def test_purchase_receipt_increases_on_hand(
        self, svc: InventoryService, tenant_id, warehouse_id,
    ) -> None:
        move, inv = await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt",
            product_id=PRODUCT_A,
            quantity=Decimal("100"),
            warehouse_id=warehouse_id,
        ))
        assert move.type == "purchase_receipt"
        assert inv.on_hand == Decimal("100")
        assert inv.available == Decimal("100")

    @pytest.mark.asyncio
    async def test_multiple_receipts_accumulate(
        self, svc: InventoryService, tenant_id, warehouse_id,
    ) -> None:
        await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt",
            product_id=PRODUCT_A,
            quantity=Decimal("100"),
            warehouse_id=warehouse_id,
        ))
        _, inv = await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt",
            product_id=PRODUCT_A,
            quantity=Decimal("200"),
            warehouse_id=warehouse_id,
        ))
        assert inv.on_hand == Decimal("300")

    @pytest.mark.asyncio
    async def test_production_issue_decreases_on_hand(
        self, svc: InventoryService, stocked_inventory,
    ) -> None:
        tenant_id, warehouse_id = stocked_inventory
        _, inv = await svc.create_move(tenant_id, StockMoveCreate(
            type="production_issue",
            product_id=PRODUCT_A,
            quantity=Decimal("150"),
            warehouse_id=warehouse_id,
        ))
        assert inv.on_hand == Decimal("350")

    @pytest.mark.asyncio
    async def test_insufficient_stock_raises(
        self, svc: InventoryService, stocked_inventory,
    ) -> None:
        tenant_id, warehouse_id = stocked_inventory
        with pytest.raises(ValueError, match="Insufficient stock"):
            await svc.create_move(tenant_id, StockMoveCreate(
                type="production_issue",
                product_id=PRODUCT_A,
                quantity=Decimal("999"),
                warehouse_id=warehouse_id,
            ))

    @pytest.mark.asyncio
    async def test_sales_issue(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, warehouse_id = stocked_inventory
        _, inv = await svc.create_move(tenant_id, StockMoveCreate(
            type="sales_issue",
            product_id=PRODUCT_A,
            quantity=Decimal("100"),
            warehouse_id=warehouse_id,
        ))
        assert inv.on_hand == Decimal("400")

    @pytest.mark.asyncio
    async def test_scrap(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, warehouse_id = stocked_inventory
        _, inv = await svc.create_move(tenant_id, StockMoveCreate(
            type="scrap",
            product_id=PRODUCT_A,
            quantity=Decimal("50"),
            warehouse_id=warehouse_id,
        ))
        assert inv.on_hand == Decimal("450")

    @pytest.mark.asyncio
    async def test_adjustment_in(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, warehouse_id = stocked_inventory
        _, inv = await svc.create_move(tenant_id, StockMoveCreate(
            type="adjustment_in",
            product_id=PRODUCT_A,
            quantity=Decimal("25"),
            warehouse_id=warehouse_id,
        ))
        assert inv.on_hand == Decimal("525")

    @pytest.mark.asyncio
    async def test_adjustment_out(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, warehouse_id = stocked_inventory
        _, inv = await svc.create_move(tenant_id, StockMoveCreate(
            type="adjustment_out",
            product_id=PRODUCT_A,
            quantity=Decimal("25"),
            warehouse_id=warehouse_id,
        ))
        assert inv.on_hand == Decimal("475")

    @pytest.mark.asyncio
    async def test_transfer_decreases_source(
        self, svc: InventoryService, stocked_inventory,
    ) -> None:
        tenant_id, warehouse_id = stocked_inventory
        _, inv = await svc.create_move(tenant_id, StockMoveCreate(
            type="transfer",
            product_id=PRODUCT_A,
            quantity=Decimal("100"),
            warehouse_id=warehouse_id,
        ))
        assert inv.on_hand == Decimal("400")

    @pytest.mark.asyncio
    async def test_batch_isolation(
        self, svc: InventoryService, tenant_id, warehouse_id,
    ) -> None:
        """Different batches are tracked separately."""
        await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt",
            product_id=PRODUCT_A,
            quantity=Decimal("100"),
            warehouse_id=warehouse_id,
            batch_no="BATCH-001",
        ))
        await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt",
            product_id=PRODUCT_A,
            quantity=Decimal("200"),
            warehouse_id=warehouse_id,
            batch_no="BATCH-002",
        ))
        inv1 = await svc.get_inventory(tenant_id, PRODUCT_A, warehouse_id, "BATCH-001")
        inv2 = await svc.get_inventory(tenant_id, PRODUCT_A, warehouse_id, "BATCH-002")
        assert inv1 is not None and inv1.on_hand == Decimal("100")
        assert inv2 is not None and inv2.on_hand == Decimal("200")

    @pytest.mark.asyncio
    async def test_unknown_move_type(self, svc: InventoryService, tenant_id, warehouse_id) -> None:
        with pytest.raises(ValueError, match="Unknown stock move type"):
            await svc.create_move(tenant_id, StockMoveCreate(
                type="invalid_type",
                product_id=PRODUCT_A,
                quantity=Decimal("10"),
                warehouse_id=warehouse_id,
            ))


# ================================================================== #
# Inventory queries
# ================================================================== #


class TestInventoryQuery:
    @pytest.mark.asyncio
    async def test_list_inventory_all(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, _ = stocked_inventory
        items, total = await svc.list_inventory(tenant_id, InventoryListParams())
        assert total == 1
        assert items[0].product_id == PRODUCT_A

    @pytest.mark.asyncio
    async def test_list_filter_by_product(
        self, svc: InventoryService, stocked_inventory, warehouse_id,
    ) -> None:
        tenant_id, _ = stocked_inventory
        # Add another product
        await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt",
            product_id=PRODUCT_B,
            quantity=Decimal("50"),
            warehouse_id=warehouse_id,
        ))

        items, total = await svc.list_inventory(
            tenant_id, InventoryListParams(product_id=PRODUCT_A),
        )
        assert total == 1
        assert items[0].product_id == PRODUCT_A

    @pytest.mark.asyncio
    async def test_list_filter_by_warehouse(
        self, svc: InventoryService, tenant_id, warehouse_id, warehouse2_id,
    ) -> None:
        await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt", product_id=PRODUCT_A,
            quantity=Decimal("100"), warehouse_id=warehouse_id,
        ))
        await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt", product_id=PRODUCT_A,
            quantity=Decimal("200"), warehouse_id=warehouse2_id,
        ))

        items, total = await svc.list_inventory(
            tenant_id, InventoryListParams(warehouse_id=warehouse_id),
        )
        assert total == 1
        assert items[0].on_hand == Decimal("100")

    @pytest.mark.asyncio
    async def test_list_filter_by_batch(
        self, svc: InventoryService, tenant_id, warehouse_id,
    ) -> None:
        await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt", product_id=PRODUCT_A,
            quantity=Decimal("100"), warehouse_id=warehouse_id, batch_no="B1",
        ))
        await svc.create_move(tenant_id, StockMoveCreate(
            type="purchase_receipt", product_id=PRODUCT_A,
            quantity=Decimal("200"), warehouse_id=warehouse_id, batch_no="B2",
        ))

        items, total = await svc.list_inventory(
            tenant_id, InventoryListParams(batch_no="B1"),
        )
        assert total == 1
        assert items[0].on_hand == Decimal("100")

    @pytest.mark.asyncio
    async def test_available_equals_on_hand_minus_reserved(
        self, svc: InventoryService, stocked_inventory,
    ) -> None:
        tenant_id, warehouse_id = stocked_inventory
        inv = await svc.get_inventory(tenant_id, PRODUCT_A, warehouse_id)
        assert inv is not None
        assert inv.available == inv.on_hand - inv.reserved


# ================================================================== #
# Issue (Lane 2 领料)
# ================================================================== #


class TestMaterialIssue:
    @pytest.mark.asyncio
    async def test_issue_material(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, warehouse_id = stocked_inventory
        work_order = uuid4()
        move, inv = await svc.issue_material(
            tenant_id, PRODUCT_A, Decimal("100"), "pcs", warehouse_id,
            work_order_id=work_order,
        )
        assert move.type == "production_issue"
        assert move.reference_id == work_order
        assert inv.on_hand == Decimal("400")

    @pytest.mark.asyncio
    async def test_issue_insufficient(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, warehouse_id = stocked_inventory
        with pytest.raises(ValueError, match="Insufficient"):
            await svc.issue_material(
                tenant_id, PRODUCT_A, Decimal("999"), "pcs", warehouse_id,
            )

    @pytest.mark.asyncio
    async def test_issue_nonexistent_product(
        self, svc: InventoryService, tenant_id, warehouse_id,
    ) -> None:
        """Issuing a product with no inventory should fail."""
        with pytest.raises(ValueError, match="Insufficient"):
            await svc.issue_material(
                tenant_id, uuid4(), Decimal("10"), "pcs", warehouse_id,
            )


# ================================================================== #
# Reserve / Unreserve
# ================================================================== #


class TestReservation:
    @pytest.mark.asyncio
    async def test_reserve(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, warehouse_id = stocked_inventory
        inv = await svc.reserve(tenant_id, PRODUCT_A, warehouse_id, Decimal("200"))
        assert inv.reserved == Decimal("200")
        assert inv.available == Decimal("300")

    @pytest.mark.asyncio
    async def test_reserve_exceeds_available(
        self, svc: InventoryService, stocked_inventory,
    ) -> None:
        tenant_id, warehouse_id = stocked_inventory
        with pytest.raises(ValueError, match="Insufficient available"):
            await svc.reserve(tenant_id, PRODUCT_A, warehouse_id, Decimal("999"))

    @pytest.mark.asyncio
    async def test_unreserve(self, svc: InventoryService, stocked_inventory) -> None:
        tenant_id, warehouse_id = stocked_inventory
        await svc.reserve(tenant_id, PRODUCT_A, warehouse_id, Decimal("200"))
        inv = await svc.unreserve(tenant_id, PRODUCT_A, warehouse_id, Decimal("100"))
        assert inv.reserved == Decimal("100")
        assert inv.available == Decimal("400")

    @pytest.mark.asyncio
    async def test_unreserve_exceeds_reserved(
        self, svc: InventoryService, stocked_inventory,
    ) -> None:
        tenant_id, warehouse_id = stocked_inventory
        with pytest.raises(ValueError, match="Cannot unreserve"):
            await svc.unreserve(tenant_id, PRODUCT_A, warehouse_id, Decimal("10"))


# ================================================================== #
# Receive stock (purchase receipt helper)
# ================================================================== #


class TestReceiveStock:
    @pytest.mark.asyncio
    async def test_receive_stock(self, svc: InventoryService, tenant_id, warehouse_id) -> None:
        po_id = uuid4()
        move, inv = await svc.receive_stock(
            tenant_id, PRODUCT_A, Decimal("300"), "pcs", warehouse_id,
            reference_id=po_id,
        )
        assert move.type == "purchase_receipt"
        assert move.reference_id == po_id
        assert inv.on_hand == Decimal("300")

    @pytest.mark.asyncio
    async def test_receive_with_batch(self, svc: InventoryService, tenant_id, warehouse_id) -> None:
        move, inv = await svc.receive_stock(
            tenant_id, PRODUCT_A, Decimal("100"), "pcs", warehouse_id,
            batch_no="LOT-2026-04",
        )
        assert inv.batch_no == "LOT-2026-04"
        assert inv.on_hand == Decimal("100")
