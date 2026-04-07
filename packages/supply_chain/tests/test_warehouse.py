"""Tests for TASK-SCM-005: Multi-warehouse + locations (4-level hierarchy)."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    LocationCreate,
    LocationUpdate,
    WarehouseCreate,
    WarehouseListParams,
    WarehouseUpdate,
)
from packages.supply_chain.models.warehouse import (
    Location,
    Warehouse,
    validate_location_hierarchy,
)
from packages.supply_chain.services.warehouse_service import WarehouseService


@pytest_asyncio.fixture
async def tenant_id(db_session: AsyncSession):
    from packages.shared.models import Tenant

    t = Tenant(code="wh-test", name="Warehouse Test Co")
    db_session.add(t)
    await db_session.flush()
    return t.id


@pytest_asyncio.fixture
async def svc(db_session: AsyncSession) -> WarehouseService:
    return WarehouseService(db_session)


@pytest_asyncio.fixture
async def warehouse(svc: WarehouseService, tenant_id) -> Warehouse:
    return await svc.create_warehouse(tenant_id, WarehouseCreate(code="WH-01", name="Main Warehouse"))


# ================================================================== #
# Warehouse CRUD
# ================================================================== #


class TestWarehouse:
    @pytest.mark.asyncio
    async def test_create_warehouse(self, svc: WarehouseService, tenant_id) -> None:
        wh = await svc.create_warehouse(tenant_id, WarehouseCreate(
            code="WH-A", name="Alpha Warehouse", address="Building A",
        ))
        assert wh.code == "WH-A"
        assert wh.name == "Alpha Warehouse"
        assert wh.is_active is True

    @pytest.mark.asyncio
    async def test_get_warehouse(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        found = await svc.get_warehouse(tenant_id, warehouse.id)
        assert found is not None
        assert found.code == "WH-01"

    @pytest.mark.asyncio
    async def test_get_warehouse_wrong_tenant(self, svc: WarehouseService, warehouse) -> None:
        found = await svc.get_warehouse(uuid4(), warehouse.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_list_warehouses(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        items, total = await svc.list_warehouses(tenant_id, WarehouseListParams())
        assert total == 1
        assert items[0].code == "WH-01"

    @pytest.mark.asyncio
    async def test_list_filter_active(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        items, total = await svc.list_warehouses(
            tenant_id, WarehouseListParams(is_active=True),
        )
        assert total == 1

        items, total = await svc.list_warehouses(
            tenant_id, WarehouseListParams(is_active=False),
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_search(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        items, total = await svc.list_warehouses(
            tenant_id, WarehouseListParams(search="main"),
        )
        assert total == 1

        items, total = await svc.list_warehouses(
            tenant_id, WarehouseListParams(search="xxx"),
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_update_warehouse(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        updated = await svc.update_warehouse(
            tenant_id, warehouse.id, WarehouseUpdate(name="Updated WH"),
        )
        assert updated is not None
        assert updated.name == "Updated WH"

    @pytest.mark.asyncio
    async def test_update_not_found(self, svc: WarehouseService, tenant_id) -> None:
        result = await svc.update_warehouse(
            tenant_id, uuid4(), WarehouseUpdate(name="X"),
        )
        assert result is None


# ================================================================== #
# Location hierarchy validation
# ================================================================== #


class _FakeLocation:
    """Lightweight stand-in for hierarchy validation (avoids SA instrumentation)."""

    def __init__(self, level: str) -> None:
        self.level = level


class TestLocationHierarchyValidation:
    def test_zone_no_parent(self) -> None:
        validate_location_hierarchy("zone", None)

    def test_zone_with_parent_fails(self) -> None:
        with pytest.raises(ValueError, match="must not have a parent"):
            validate_location_hierarchy("zone", _FakeLocation("zone"))  # type: ignore[arg-type]

    def test_aisle_needs_zone_parent(self) -> None:
        validate_location_hierarchy("aisle", _FakeLocation("zone"))  # type: ignore[arg-type]

    def test_aisle_wrong_parent(self) -> None:
        with pytest.raises(ValueError, match="requires parent level 'zone'"):
            validate_location_hierarchy("aisle", _FakeLocation("bin"))  # type: ignore[arg-type]

    def test_aisle_no_parent_fails(self) -> None:
        with pytest.raises(ValueError, match="requires a parent"):
            validate_location_hierarchy("aisle", None)

    def test_bin_needs_aisle_parent(self) -> None:
        validate_location_hierarchy("bin", _FakeLocation("aisle"))  # type: ignore[arg-type]

    def test_bin_wrong_parent(self) -> None:
        with pytest.raises(ValueError, match="requires parent level 'aisle'"):
            validate_location_hierarchy("bin", _FakeLocation("zone"))  # type: ignore[arg-type]


# ================================================================== #
# Location CRUD (via service, hitting DB)
# ================================================================== #


class TestLocation:
    @pytest.mark.asyncio
    async def test_create_zone(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        assert zone.level == "zone"
        assert zone.parent_id is None

    @pytest.mark.asyncio
    async def test_create_aisle_under_zone(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        aisle = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="A-01", name="Aisle 1",
            level="aisle", parent_id=zone.id,
        ))
        assert aisle.level == "aisle"
        assert aisle.parent_id == zone.id

    @pytest.mark.asyncio
    async def test_create_bin_under_aisle(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        aisle = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="A-01", name="Aisle 1",
            level="aisle", parent_id=zone.id,
        ))
        bin_ = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="B-01-01", name="Bin 1-1",
            level="bin", parent_id=aisle.id, capacity=500,
        ))
        assert bin_.level == "bin"
        assert bin_.parent_id == aisle.id
        assert bin_.capacity == 500

    @pytest.mark.asyncio
    async def test_zone_with_parent_fails(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        with pytest.raises(ValueError, match="must not have a parent"):
            await svc.create_location(tenant_id, LocationCreate(
                warehouse_id=warehouse.id, code="Z-02", name="Zone B",
                level="zone", parent_id=zone.id,
            ))

    @pytest.mark.asyncio
    async def test_aisle_without_parent_fails(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        with pytest.raises(ValueError, match="requires a parent"):
            await svc.create_location(tenant_id, LocationCreate(
                warehouse_id=warehouse.id, code="A-01", name="Aisle 1", level="aisle",
            ))

    @pytest.mark.asyncio
    async def test_bin_under_zone_fails(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        with pytest.raises(ValueError, match="requires parent level 'aisle'"):
            await svc.create_location(tenant_id, LocationCreate(
                warehouse_id=warehouse.id, code="B-01", name="Bin 1",
                level="bin", parent_id=zone.id,
            ))

    @pytest.mark.asyncio
    async def test_parent_cross_warehouse_fails(
        self, svc: WarehouseService, tenant_id, warehouse,
    ) -> None:
        wh2 = await svc.create_warehouse(tenant_id, WarehouseCreate(code="WH-02", name="WH 2"))
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        with pytest.raises(ValueError, match="same warehouse"):
            await svc.create_location(tenant_id, LocationCreate(
                warehouse_id=wh2.id, code="A-01", name="Aisle",
                level="aisle", parent_id=zone.id,
            ))

    @pytest.mark.asyncio
    async def test_warehouse_not_found(self, svc: WarehouseService, tenant_id) -> None:
        with pytest.raises(ValueError, match="Warehouse.*not found"):
            await svc.create_location(tenant_id, LocationCreate(
                warehouse_id=uuid4(), code="Z-01", name="Zone", level="zone",
            ))

    @pytest.mark.asyncio
    async def test_parent_not_found(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        with pytest.raises(ValueError, match="Parent.*not found"):
            await svc.create_location(tenant_id, LocationCreate(
                warehouse_id=warehouse.id, code="A-01", name="Aisle",
                level="aisle", parent_id=uuid4(),
            ))

    @pytest.mark.asyncio
    async def test_list_locations(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-02", name="Zone B", level="zone",
        ))
        locs = await svc.list_locations(tenant_id, warehouse.id)
        assert len(locs) == 2

    @pytest.mark.asyncio
    async def test_list_locations_filter_level(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="A-01", name="Aisle 1",
            level="aisle", parent_id=zone.id,
        ))
        zones = await svc.list_locations(tenant_id, warehouse.id, level="zone")
        assert len(zones) == 1
        aisles = await svc.list_locations(tenant_id, warehouse.id, level="aisle")
        assert len(aisles) == 1

    @pytest.mark.asyncio
    async def test_list_locations_filter_parent(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="A-01", name="Aisle 1",
            level="aisle", parent_id=zone.id,
        ))
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="A-02", name="Aisle 2",
            level="aisle", parent_id=zone.id,
        ))
        children = await svc.list_locations(tenant_id, warehouse.id, parent_id=zone.id)
        assert len(children) == 2

    @pytest.mark.asyncio
    async def test_update_location(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        updated = await svc.update_location(
            tenant_id, zone.id, LocationUpdate(name="Zone Alpha", capacity=1000),
        )
        assert updated is not None
        assert updated.name == "Zone Alpha"
        assert updated.capacity == 1000


# ================================================================== #
# Location tree
# ================================================================== #


class TestLocationTree:
    @pytest.mark.asyncio
    async def test_full_tree(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        zone = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        aisle = await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="A-01", name="Aisle 1",
            level="aisle", parent_id=zone.id,
        ))
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="B-01-01", name="Bin 1-1",
            level="bin", parent_id=aisle.id,
        ))
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="B-01-02", name="Bin 1-2",
            level="bin", parent_id=aisle.id,
        ))

        tree = await svc.get_location_tree(tenant_id, warehouse.id)
        assert len(tree) == 1  # 1 root zone
        assert tree[0]["code"] == "Z-01"
        assert len(tree[0]["children"]) == 1  # 1 aisle
        assert tree[0]["children"][0]["code"] == "A-01"
        assert len(tree[0]["children"][0]["children"]) == 2  # 2 bins

    @pytest.mark.asyncio
    async def test_empty_warehouse_tree(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        tree = await svc.get_location_tree(tenant_id, warehouse.id)
        assert tree == []

    @pytest.mark.asyncio
    async def test_multi_zone_tree(self, svc: WarehouseService, tenant_id, warehouse) -> None:
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-01", name="Zone A", level="zone",
        ))
        await svc.create_location(tenant_id, LocationCreate(
            warehouse_id=warehouse.id, code="Z-02", name="Zone B", level="zone",
        ))
        tree = await svc.get_location_tree(tenant_id, warehouse.id)
        assert len(tree) == 2
