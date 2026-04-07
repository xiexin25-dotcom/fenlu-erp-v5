"""
SCM · 仓库 + 库位服务层
========================
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
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


class WarehouseService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ================================================================== #
    # Warehouse CRUD
    # ================================================================== #

    async def create_warehouse(
        self, tenant_id: UUID, data: WarehouseCreate,
    ) -> Warehouse:
        wh = Warehouse(
            tenant_id=tenant_id,
            code=data.code,
            name=data.name,
            address=data.address,
            manager_id=data.manager_id,
            remark=data.remark,
            sort_order=data.sort_order,
        )
        self._session.add(wh)
        await self._session.flush()
        return wh

    async def get_warehouse(
        self, tenant_id: UUID, wh_id: UUID,
    ) -> Warehouse | None:
        stmt = select(Warehouse).where(
            Warehouse.tenant_id == tenant_id,
            Warehouse.id == wh_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_warehouses(
        self, tenant_id: UUID, params: WarehouseListParams,
    ) -> tuple[list[Warehouse], int]:
        base = select(Warehouse).where(Warehouse.tenant_id == tenant_id)

        if params.is_active is not None:
            base = base.where(Warehouse.is_active == params.is_active)
        if params.search:
            pattern = f"%{params.search}%"
            base = base.where(
                or_(Warehouse.code.ilike(pattern), Warehouse.name.ilike(pattern)),
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        items_stmt = (
            base
            .order_by(Warehouse.sort_order, Warehouse.code)
            .offset((params.page - 1) * params.size)
            .limit(params.size)
        )
        rows = (await self._session.execute(items_stmt)).scalars().all()
        return list(rows), total

    async def update_warehouse(
        self, tenant_id: UUID, wh_id: UUID, data: WarehouseUpdate,
    ) -> Warehouse | None:
        wh = await self.get_warehouse(tenant_id, wh_id)
        if wh is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(wh, field, value)
        await self._session.flush()
        return wh

    # ================================================================== #
    # Location CRUD
    # ================================================================== #

    async def create_location(
        self, tenant_id: UUID, data: LocationCreate,
    ) -> Location:
        # 验证仓库存在
        wh = await self.get_warehouse(tenant_id, data.warehouse_id)
        if wh is None:
            raise ValueError(f"Warehouse {data.warehouse_id} not found")

        # 验证 parent 层级
        parent: Location | None = None
        if data.parent_id is not None:
            parent = await self.get_location(tenant_id, data.parent_id)
            if parent is None:
                raise ValueError(f"Parent location {data.parent_id} not found")
            if parent.warehouse_id != data.warehouse_id:
                raise ValueError("Parent location must belong to the same warehouse")

        validate_location_hierarchy(data.level, parent)

        loc = Location(
            tenant_id=tenant_id,
            warehouse_id=data.warehouse_id,
            code=data.code,
            name=data.name,
            level=data.level,
            parent_id=data.parent_id,
            sort_order=data.sort_order,
            capacity=data.capacity,
        )
        self._session.add(loc)
        await self._session.flush()
        return loc

    async def get_location(
        self, tenant_id: UUID, loc_id: UUID,
    ) -> Location | None:
        stmt = select(Location).where(
            Location.tenant_id == tenant_id,
            Location.id == loc_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_locations(
        self,
        tenant_id: UUID,
        warehouse_id: UUID,
        level: str | None = None,
        parent_id: UUID | None = None,
    ) -> list[Location]:
        stmt = select(Location).where(
            Location.tenant_id == tenant_id,
            Location.warehouse_id == warehouse_id,
        )
        if level is not None:
            stmt = stmt.where(Location.level == level)
        if parent_id is not None:
            stmt = stmt.where(Location.parent_id == parent_id)
        stmt = stmt.order_by(Location.sort_order, Location.code)
        return list((await self._session.execute(stmt)).scalars().all())

    async def update_location(
        self, tenant_id: UUID, loc_id: UUID, data: LocationUpdate,
    ) -> Location | None:
        loc = await self.get_location(tenant_id, loc_id)
        if loc is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(loc, field, value)
        await self._session.flush()
        return loc

    async def get_location_tree(
        self, tenant_id: UUID, warehouse_id: UUID,
    ) -> list[dict]:
        """返回仓库完整库位树 (zone → aisle → bin)。"""
        all_locs = await self.list_locations(tenant_id, warehouse_id)

        # Build tree from flat list
        by_id: dict[UUID, dict] = {}
        roots: list[dict] = []

        for loc in all_locs:
            node = {
                "id": loc.id,
                "code": loc.code,
                "name": loc.name,
                "level": loc.level,
                "parent_id": loc.parent_id,
                "is_active": loc.is_active,
                "sort_order": loc.sort_order,
                "capacity": loc.capacity,
                "children": [],
            }
            by_id[loc.id] = node

        for loc in all_locs:
            node = by_id[loc.id]
            if loc.parent_id is not None and loc.parent_id in by_id:
                by_id[loc.parent_id]["children"].append(node)
            else:
                roots.append(node)

        return roots
