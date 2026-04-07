"""Tests for TASK-SCM-007: Stocktake flow with auto-adjustment StockMoves."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    StockMoveCreate,
    StocktakeCreate,
    StocktakeLineCreate,
    WarehouseCreate,
)
from packages.supply_chain.models.stocktake import validate_stocktake_transition
from packages.supply_chain.services.inventory_service import InventoryService
from packages.supply_chain.services.stocktake_service import StocktakeService
from packages.supply_chain.services.warehouse_service import WarehouseService

PRODUCT_A = uuid4()
PRODUCT_B = uuid4()


@pytest_asyncio.fixture
async def tenant_id(db_session: AsyncSession):
    from packages.shared.models import Tenant

    t = Tenant(code="st-test", name="Stocktake Test Co")
    db_session.add(t)
    await db_session.flush()
    return t.id


@pytest_asyncio.fixture
async def warehouse_id(db_session: AsyncSession, tenant_id):
    svc = WarehouseService(db_session)
    wh = await svc.create_warehouse(tenant_id, WarehouseCreate(code="WH-ST", name="Stocktake WH"))
    return wh.id


@pytest_asyncio.fixture
async def inv_svc(db_session: AsyncSession) -> InventoryService:
    return InventoryService(db_session)


@pytest_asyncio.fixture
async def svc(db_session: AsyncSession) -> StocktakeService:
    return StocktakeService(db_session)


@pytest_asyncio.fixture
async def stocked(inv_svc: InventoryService, tenant_id, warehouse_id):
    """Pre-stock: PRODUCT_A=500, PRODUCT_B=200."""
    await inv_svc.create_move(tenant_id, StockMoveCreate(
        type="purchase_receipt", product_id=PRODUCT_A,
        quantity=Decimal("500"), warehouse_id=warehouse_id,
    ))
    await inv_svc.create_move(tenant_id, StockMoveCreate(
        type="purchase_receipt", product_id=PRODUCT_B,
        quantity=Decimal("200"), warehouse_id=warehouse_id,
    ))


# ================================================================== #
# Transition validation
# ================================================================== #


class TestStocktakeTransition:
    def test_draft_to_confirmed(self) -> None:
        validate_stocktake_transition("draft", "confirmed")

    def test_draft_to_cancelled(self) -> None:
        validate_stocktake_transition("draft", "cancelled")

    def test_confirmed_to_closed(self) -> None:
        validate_stocktake_transition("confirmed", "closed")

    def test_invalid_draft_to_closed(self) -> None:
        with pytest.raises(ValueError, match="not allowed"):
            validate_stocktake_transition("draft", "closed")

    def test_cancelled_is_terminal(self) -> None:
        with pytest.raises(ValueError, match="not allowed"):
            validate_stocktake_transition("cancelled", "draft")


# ================================================================== #
# Stocktake CRUD
# ================================================================== #


class TestStocktakeCRUD:
    @pytest.mark.asyncio
    async def test_create_stocktake_snapshots_system_qty(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-001",
            warehouse_id=warehouse_id,
            lines=[
                StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("480")),
                StocktakeLineCreate(product_id=PRODUCT_B, actual_quantity=Decimal("200")),
            ],
        ))
        assert st.status == "draft"
        assert len(st.lines) == 2

        line_a = next(l for l in st.lines if l.product_id == PRODUCT_A)
        line_b = next(l for l in st.lines if l.product_id == PRODUCT_B)

        assert line_a.system_quantity == Decimal("500")
        assert line_a.actual_quantity == Decimal("480")
        assert line_a.variance == Decimal("-20")  # 盘亏

        assert line_b.system_quantity == Decimal("200")
        assert line_b.actual_quantity == Decimal("200")
        assert line_b.variance == Decimal("0")  # 无差异

    @pytest.mark.asyncio
    async def test_create_stocktake_no_existing_inventory(
        self, svc: StocktakeService, tenant_id, warehouse_id,
    ) -> None:
        """Product with no inventory → system_quantity = 0."""
        new_product = uuid4()
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-002",
            warehouse_id=warehouse_id,
            lines=[
                StocktakeLineCreate(product_id=new_product, actual_quantity=Decimal("10")),
            ],
        ))
        line = st.lines[0]
        assert line.system_quantity == Decimal("0")
        assert line.variance == Decimal("10")  # 盘盈

    @pytest.mark.asyncio
    async def test_get_stocktake(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-003",
            warehouse_id=warehouse_id,
            lines=[StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("500"))],
        ))
        found = await svc.get_stocktake(tenant_id, st.id)
        assert found is not None
        assert found.stocktake_no == "ST-003"

    @pytest.mark.asyncio
    async def test_list_stocktakes(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-004",
            warehouse_id=warehouse_id,
            lines=[StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("500"))],
        ))
        items = await svc.list_stocktakes(tenant_id)
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_list_filter_by_warehouse(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked, db_session,
    ) -> None:
        wh_svc = WarehouseService(db_session)
        wh2 = await wh_svc.create_warehouse(tenant_id, WarehouseCreate(code="WH-ST2", name="WH2"))
        await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-005",
            warehouse_id=warehouse_id,
            lines=[StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("500"))],
        ))
        items = await svc.list_stocktakes(tenant_id, warehouse_id=wh2.id)
        assert len(items) == 0


# ================================================================== #
# Confirm: auto-adjustment moves
# ================================================================== #


class TestStocktakeConfirm:
    @pytest.mark.asyncio
    async def test_confirm_creates_adjustment_moves(
        self, svc: StocktakeService, inv_svc: InventoryService,
        tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-C01",
            warehouse_id=warehouse_id,
            lines=[
                StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("480")),  # -20
                StocktakeLineCreate(product_id=PRODUCT_B, actual_quantity=Decimal("220")),  # +20
            ],
        ))

        st, moves = await svc.confirm_stocktake(tenant_id, st.id)
        assert st.status == "confirmed"
        assert len(moves) == 2

        # Check move types
        move_types = {m.type for m in moves}
        assert "adjustment_out" in move_types  # 盘亏
        assert "adjustment_in" in move_types   # 盘盈

        # Check inventory was updated
        inv_a = await inv_svc.get_inventory(tenant_id, PRODUCT_A, warehouse_id)
        inv_b = await inv_svc.get_inventory(tenant_id, PRODUCT_B, warehouse_id)
        assert inv_a is not None and inv_a.on_hand == Decimal("480")
        assert inv_b is not None and inv_b.on_hand == Decimal("220")

    @pytest.mark.asyncio
    async def test_confirm_no_variance_no_moves(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-C02",
            warehouse_id=warehouse_id,
            lines=[
                StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("500")),
                StocktakeLineCreate(product_id=PRODUCT_B, actual_quantity=Decimal("200")),
            ],
        ))

        st, moves = await svc.confirm_stocktake(tenant_id, st.id)
        assert st.status == "confirmed"
        assert len(moves) == 0  # no variance, no moves

    @pytest.mark.asyncio
    async def test_confirm_moves_reference_stocktake(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-C03",
            warehouse_id=warehouse_id,
            lines=[
                StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("510")),
            ],
        ))
        st, moves = await svc.confirm_stocktake(tenant_id, st.id)
        assert len(moves) == 1
        assert moves[0].reference_id == st.id

    @pytest.mark.asyncio
    async def test_confirm_already_confirmed_fails(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-C04",
            warehouse_id=warehouse_id,
            lines=[StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("500"))],
        ))
        await svc.confirm_stocktake(tenant_id, st.id)
        with pytest.raises(ValueError, match="not allowed"):
            await svc.confirm_stocktake(tenant_id, st.id)

    @pytest.mark.asyncio
    async def test_confirm_not_found(self, svc: StocktakeService, tenant_id) -> None:
        with pytest.raises(ValueError, match="not found"):
            await svc.confirm_stocktake(tenant_id, uuid4())

    @pytest.mark.asyncio
    async def test_confirm_new_product_creates_inventory(
        self, svc: StocktakeService, inv_svc: InventoryService,
        tenant_id, warehouse_id,
    ) -> None:
        """Confirming a stocktake for a product not in inventory creates it."""
        new_product = uuid4()
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-C05",
            warehouse_id=warehouse_id,
            lines=[StocktakeLineCreate(product_id=new_product, actual_quantity=Decimal("42"))],
        ))
        st, moves = await svc.confirm_stocktake(tenant_id, st.id)
        assert len(moves) == 1
        assert moves[0].type == "adjustment_in"

        inv = await inv_svc.get_inventory(tenant_id, new_product, warehouse_id)
        assert inv is not None
        assert inv.on_hand == Decimal("42")


# ================================================================== #
# Close / Cancel
# ================================================================== #


class TestStocktakeLifecycle:
    @pytest.mark.asyncio
    async def test_confirm_then_close(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-L01",
            warehouse_id=warehouse_id,
            lines=[StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("500"))],
        ))
        await svc.confirm_stocktake(tenant_id, st.id)
        st = await svc.transition_stocktake(tenant_id, st.id, "closed")
        assert st.status == "closed"

    @pytest.mark.asyncio
    async def test_cancel_draft(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-L02",
            warehouse_id=warehouse_id,
            lines=[StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("500"))],
        ))
        st = await svc.transition_stocktake(tenant_id, st.id, "cancelled")
        assert st.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cannot_close_draft(
        self, svc: StocktakeService, tenant_id, warehouse_id, stocked,
    ) -> None:
        st = await svc.create_stocktake(tenant_id, StocktakeCreate(
            stocktake_no="ST-L03",
            warehouse_id=warehouse_id,
            lines=[StocktakeLineCreate(product_id=PRODUCT_A, actual_quantity=Decimal("500"))],
        ))
        with pytest.raises(ValueError, match="not allowed"):
            await svc.transition_stocktake(tenant_id, st.id, "closed")
