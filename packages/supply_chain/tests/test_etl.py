"""Tests for TASK-SCM-008: V4→V5 ETL migration end-to-end + reconciliation."""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.migration.etl_loader import ETLLoader
from packages.supply_chain.migration.reconciliation import run_reconciliation
from packages.supply_chain.migration.transforms import (
    LegacyIdMap,
    map_status,
    map_tier,
    map_uom,
    to_utc,
)
from packages.supply_chain.migration.v4_sample_data import generate_all
from packages.supply_chain.models.inventory import Inventory, StockMove
from packages.supply_chain.models.purchase import PurchaseOrder, PurchaseOrderLine
from packages.supply_chain.models.stocktake import Stocktake, StocktakeLine
from packages.supply_chain.models.supplier import Supplier
from packages.supply_chain.models.warehouse import Location, Warehouse


@pytest_asyncio.fixture
async def tenant_id(db_session: AsyncSession):
    from packages.shared.models import Tenant

    t = Tenant(code="etl-test", name="ETL Test Co")
    db_session.add(t)
    await db_session.flush()
    return t.id


@pytest_asyncio.fixture
async def v4_data():
    return generate_all()


@pytest_asyncio.fixture
async def etl_report(db_session: AsyncSession, tenant_id, v4_data):
    loader = ETLLoader(db_session, tenant_id)
    return await loader.run(v4_data)


# ================================================================== #
# Transform unit tests
# ================================================================== #


class TestTransforms:
    def test_to_utc(self) -> None:
        result = to_utc("2025-03-01 09:00:00")
        assert result is not None
        assert result.hour == 1  # 09:00 CST = 01:00 UTC

    def test_to_utc_none(self) -> None:
        assert to_utc(None) is None
        assert to_utc("") is None

    def test_map_uom_chinese(self) -> None:
        assert map_uom("件") == "pcs"
        assert map_uom("千克") == "kg"
        assert map_uom("升") == "L"

    def test_map_uom_unknown(self) -> None:
        assert map_uom("unknown") == "pcs"  # fallback

    def test_map_status(self) -> None:
        assert map_status(0) == "draft"
        assert map_status(2) == "approved"
        assert map_status(5) == "closed"
        assert map_status("pending") == "submitted"

    def test_map_tier(self) -> None:
        assert map_tier(1) == "strategic"
        assert map_tier(4) == "blacklisted"
        assert map_tier(99) == "approved"  # fallback

    def test_legacy_id_map(self) -> None:
        m = LegacyIdMap()
        uid1 = m.get_or_create("table", 1)
        uid2 = m.get_or_create("table", 1)
        assert uid1 == uid2
        assert m.get("table", 999) is None
        with pytest.raises(ValueError, match="Missing"):
            m.require("table", 999)


# ================================================================== #
# ETL loader
# ================================================================== #


class TestETLLoader:
    @pytest.mark.asyncio
    async def test_etl_runs_without_errors(self, etl_report) -> None:
        assert etl_report.total_errors == 0

    @pytest.mark.asyncio
    async def test_etl_row_counts(self, etl_report, v4_data) -> None:
        for stats in etl_report.stats:
            assert stats.v4_count == stats.v5_count, (
                f"{stats.table}: V4={stats.v4_count} != V5={stats.v5_count}, errors={stats.errors}"
            )

    @pytest.mark.asyncio
    async def test_suppliers_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(Supplier))).scalar_one()
        assert count == 3

    @pytest.mark.asyncio
    async def test_supplier_tier_mapped(self, db_session, etl_report) -> None:
        sups = (await db_session.execute(
            select(Supplier).order_by(Supplier.code)
        )).scalars().all()
        assert sups[0].tier == "strategic"   # level=1
        assert sups[1].tier == "preferred"   # level=2
        assert sups[2].tier == "blacklisted" # level=4

    @pytest.mark.asyncio
    async def test_supplier_inactive_mapped(self, db_session, etl_report) -> None:
        sup3 = (await db_session.execute(
            select(Supplier).where(Supplier.code == "SUP-003")
        )).scalar_one()
        assert sup3.is_online is False

    @pytest.mark.asyncio
    async def test_warehouses_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(Warehouse))).scalar_one()
        assert count == 2

    @pytest.mark.asyncio
    async def test_locations_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(Location))).scalar_one()
        assert count == 3

    @pytest.mark.asyncio
    async def test_location_hierarchy(self, db_session, etl_report) -> None:
        locs = (await db_session.execute(
            select(Location).order_by(Location.code)
        )).scalars().all()
        # A-A01 (aisle) should have parent Z-A (zone)
        aisle = next(l for l in locs if l.code == "A-A01")
        zone = next(l for l in locs if l.code == "Z-A")
        assert aisle.parent_id == zone.id
        assert aisle.level == "aisle"
        assert zone.level == "zone"

    @pytest.mark.asyncio
    async def test_purchase_orders_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(PurchaseOrder))).scalar_one()
        assert count == 3

    @pytest.mark.asyncio
    async def test_po_status_mapped(self, db_session, etl_report) -> None:
        pos = (await db_session.execute(
            select(PurchaseOrder).order_by(PurchaseOrder.order_no)
        )).scalars().all()
        assert pos[0].status == "approved"  # status=2
        assert pos[1].status == "closed"    # status=5
        assert pos[2].status == "draft"     # status=0

    @pytest.mark.asyncio
    async def test_po_lines_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(PurchaseOrderLine))).scalar_one()
        assert count == 3

    @pytest.mark.asyncio
    async def test_po_total_amount_preserved(self, db_session, etl_report) -> None:
        total = (await db_session.execute(
            select(func.sum(PurchaseOrder.total_amount))
        )).scalar_one()
        expected = Decimal("25000.00") + Decimal("8600.50") + Decimal("1200.00")
        assert Decimal(str(total)) == expected

    @pytest.mark.asyncio
    async def test_inventory_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(Inventory))).scalar_one()
        assert count == 2

    @pytest.mark.asyncio
    async def test_inventory_quantities(self, db_session, etl_report) -> None:
        invs = (await db_session.execute(select(Inventory))).scalars().all()
        inv_map = {inv.batch_no: inv for inv in invs}
        assert inv_map["B2025-001"].on_hand == Decimal("800")
        assert inv_map["B2025-001"].reserved == Decimal("100")
        assert inv_map["B2025-002"].on_hand == Decimal("500")
        assert inv_map["B2025-002"].in_transit == Decimal("50")

    @pytest.mark.asyncio
    async def test_stock_moves_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(StockMove))).scalar_one()
        assert count == 3  # 2 in + 1 out

    @pytest.mark.asyncio
    async def test_stock_move_types(self, db_session, etl_report) -> None:
        moves = (await db_session.execute(
            select(StockMove).order_by(StockMove.move_no)
        )).scalars().all()
        types = {m.move_no: m.type for m in moves}
        assert types["IN-2025-001"] == "purchase_receipt"
        assert types["IN-2025-002"] == "purchase_receipt"
        assert types["OUT-2025-001"] == "production_issue"

    @pytest.mark.asyncio
    async def test_stocktakes_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(Stocktake))).scalar_one()
        assert count == 1

    @pytest.mark.asyncio
    async def test_stocktake_lines_loaded(self, db_session, etl_report) -> None:
        count = (await db_session.execute(select(func.count()).select_from(StocktakeLine))).scalar_one()
        assert count == 1

    @pytest.mark.asyncio
    async def test_stocktake_variance(self, db_session, etl_report) -> None:
        line = (await db_session.execute(select(StocktakeLine))).scalar_one()
        assert line.system_quantity == Decimal("750")
        assert line.actual_quantity == Decimal("748")
        assert line.variance == Decimal("-2")

    @pytest.mark.asyncio
    async def test_utc_conversion(self, db_session, etl_report) -> None:
        sup = (await db_session.execute(
            select(Supplier).where(Supplier.code == "SUP-001")
        )).scalar_one()
        # 2024-01-15 08:30:00 CST → 2024-01-15 00:30:00 UTC
        assert sup.created_at.hour == 0
        assert sup.created_at.minute == 30

    @pytest.mark.asyncio
    async def test_legacy_id_map_populated(self, etl_report) -> None:
        m = etl_report.legacy_id_map
        # All 3 suppliers should be mapped
        assert m.get("t_supplier", 1) is not None
        assert m.get("t_supplier", 2) is not None
        assert m.get("t_supplier", 3) is not None
        # Warehouses
        assert m.get("t_warehouse", 1) is not None
        assert m.get("t_warehouse", 2) is not None


# ================================================================== #
# Reconciliation
# ================================================================== #


class TestReconciliation:
    @pytest.mark.asyncio
    async def test_reconciliation_all_pass(
        self, db_session, etl_report, v4_data,
    ) -> None:
        report = await run_reconciliation(db_session, etl_report, v4_data)
        for check in report.checks:
            assert check.passed, f"FAILED: {check.name} — {check.detail}"
        assert report.all_passed

    @pytest.mark.asyncio
    async def test_reconciliation_report_markdown(
        self, db_session, etl_report, v4_data,
    ) -> None:
        report = await run_reconciliation(db_session, etl_report, v4_data)
        md = report.to_markdown()
        assert "# V4 → V5 Reconciliation Report" in md
        assert "ALL PASSED" in md
        assert "Row count" in md
        assert "Amount" in md
        assert "Inventory" in md

    @pytest.mark.asyncio
    async def test_reconciliation_check_count(
        self, db_session, etl_report, v4_data,
    ) -> None:
        report = await run_reconciliation(db_session, etl_report, v4_data)
        # 6 row count checks + 1 move count + amount + inventory + flow + 2 FK + 1 orphan STL + ETL errors
        assert len(report.checks) >= 12
