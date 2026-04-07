"""
V4 → V5 ETL 加载器
====================

按 MAPPING.md 的执行顺序加载 V4 数据到 V5 模型。
支持内存数据 (dict) 或 CSV 文件作为输入。

用法:
    loader = ETLLoader(session, tenant_id)
    report = await loader.run(v4_data)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.models.inventory import Inventory, StockMove
from packages.supply_chain.models.purchase import (
    PurchaseOrder,
    PurchaseOrderLine,
)
from packages.supply_chain.models.stocktake import Stocktake, StocktakeLine
from packages.supply_chain.models.supplier import Supplier, SupplierRating
from packages.supply_chain.models.warehouse import Location, Warehouse

from .transforms import (
    LegacyIdMap,
    STOCK_IN_TYPE_MAP,
    STOCK_OUT_TYPE_MAP,
    date_to_utc,
    map_status,
    map_tier,
    map_uom,
    to_utc,
)


@dataclass
class ETLStats:
    """每个表的加载统计。"""
    table: str
    v4_count: int = 0
    v5_count: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ETLReport:
    """整个 ETL 运行的汇总报告。"""
    stats: list[ETLStats] = field(default_factory=list)
    legacy_id_map: LegacyIdMap = field(default_factory=LegacyIdMap)

    def add(self, s: ETLStats) -> None:
        self.stats.append(s)

    def get(self, table: str) -> ETLStats | None:
        return next((s for s in self.stats if s.table == table), None)

    @property
    def total_v4(self) -> int:
        return sum(s.v4_count for s in self.stats)

    @property
    def total_v5(self) -> int:
        return sum(s.v5_count for s in self.stats)

    @property
    def total_errors(self) -> int:
        return sum(len(s.errors) for s in self.stats)


def _int(val) -> int:
    return int(val) if val is not None and val != "" else 0


def _decimal(val) -> Decimal:
    if val is None or val == "":
        return Decimal(0)
    return Decimal(str(val))


def _int_or_none(val) -> int | None:
    if val is None or val == "" or val == "None":
        return None
    return int(val)


class ETLLoader:
    """V4 → V5 ETL 引擎。"""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._id_map = LegacyIdMap()
        # 用于 move_no 去重
        self._move_seq = 0

    async def run(self, v4_data: dict[str, list[dict]]) -> ETLReport:
        """按依赖顺序执行完整 ETL。"""
        report = ETLReport(legacy_id_map=self._id_map)

        # 按 MAPPING.md 执行顺序
        report.add(await self._load_warehouses(v4_data.get("t_warehouse", [])))
        report.add(await self._load_locations(v4_data.get("t_warehouse_location", [])))
        report.add(await self._load_suppliers(v4_data.get("t_supplier", [])))
        report.add(await self._load_purchase_orders(
            v4_data.get("t_purchase_order", []),
            v4_data.get("t_purchase_order_detail", []),
        ))
        report.add(await self._load_inventory(v4_data.get("t_inventory", [])))
        report.add(await self._load_stock_moves(
            v4_data.get("t_stock_in", []),
            v4_data.get("t_stock_out", []),
        ))
        report.add(await self._load_stocktakes(
            v4_data.get("t_stocktake", []),
            v4_data.get("t_stocktake_detail", []),
        ))

        await self._session.flush()
        return report

    # ------------------------------------------------------------------ #
    # 1. Warehouses
    # ------------------------------------------------------------------ #

    async def _load_warehouses(self, rows: list[dict]) -> ETLStats:
        stats = ETLStats(table="warehouses", v4_count=len(rows))
        for row in rows:
            try:
                wh = Warehouse(
                    id=self._id_map.get_or_create("t_warehouse", _int(row["id"])),
                    tenant_id=self._tenant_id,
                    code=row["warehouse_code"],
                    name=row["warehouse_name"],
                    address=row.get("address"),
                    is_active=bool(_int(row.get("is_active", 1))),
                    created_at=to_utc(row.get("create_time")) or datetime.utcnow(),
                    updated_at=to_utc(row.get("create_time")) or datetime.utcnow(),
                )
                self._session.add(wh)
                stats.v5_count += 1
            except Exception as e:
                stats.errors.append(f"Row {row.get('id')}: {e}")
        await self._session.flush()
        return stats

    # ------------------------------------------------------------------ #
    # 2. Locations
    # ------------------------------------------------------------------ #

    async def _load_locations(self, rows: list[dict]) -> ETLStats:
        stats = ETLStats(table="locations", v4_count=len(rows))
        # V4 可能只有 1-2 级, 映射: level 1 → zone, level 2 → aisle
        level_map = {1: "zone", 2: "aisle", 3: "bin"}
        for row in rows:
            try:
                v4_level = _int(row.get("level", 1))
                parent_legacy = _int_or_none(row.get("parent_id"))
                parent_uuid = self._id_map.get("t_warehouse_location", parent_legacy) if parent_legacy else None

                loc = Location(
                    id=self._id_map.get_or_create("t_warehouse_location", _int(row["id"])),
                    tenant_id=self._tenant_id,
                    warehouse_id=self._id_map.require("t_warehouse", _int(row["warehouse_id"])),
                    code=row["location_code"],
                    name=row["location_name"],
                    level=level_map.get(v4_level, "zone"),
                    parent_id=parent_uuid,
                    is_active=bool(_int(row.get("is_active", 1))),
                )
                self._session.add(loc)
                stats.v5_count += 1
            except Exception as e:
                stats.errors.append(f"Row {row.get('id')}: {e}")
        await self._session.flush()
        return stats

    # ------------------------------------------------------------------ #
    # 3. Suppliers
    # ------------------------------------------------------------------ #

    async def _load_suppliers(self, rows: list[dict]) -> ETLStats:
        stats = ETLStats(table="suppliers", v4_count=len(rows))
        for row in rows:
            try:
                sup = Supplier(
                    id=self._id_map.get_or_create("t_supplier", _int(row["id"])),
                    tenant_id=self._tenant_id,
                    code=row["supplier_code"],
                    name=row["supplier_name"],
                    tier=map_tier(_int(row["level"])),
                    rating_score=float(row.get("score", 0)),
                    is_online=bool(_int(row.get("is_active", 1))),
                    contact_name=row.get("contact_person"),
                    contact_phone=row.get("phone"),
                    address=row.get("address"),
                    created_at=to_utc(row.get("create_time")) or datetime.utcnow(),
                    updated_at=to_utc(row.get("update_time")) or datetime.utcnow(),
                )
                self._session.add(sup)
                stats.v5_count += 1
            except Exception as e:
                stats.errors.append(f"Row {row.get('id')}: {e}")
        await self._session.flush()
        return stats

    # ------------------------------------------------------------------ #
    # 6. Purchase Orders + Lines
    # ------------------------------------------------------------------ #

    async def _load_purchase_orders(
        self, po_rows: list[dict], line_rows: list[dict],
    ) -> ETLStats:
        stats = ETLStats(table="purchase_orders", v4_count=len(po_rows))
        # Group lines by order_id
        lines_by_order: dict[int, list[dict]] = {}
        for ln in line_rows:
            oid = _int(ln["order_id"])
            lines_by_order.setdefault(oid, []).append(ln)

        for row in po_rows:
            try:
                v4_id = _int(row["id"])
                po = PurchaseOrder(
                    id=self._id_map.get_or_create("t_purchase_order", v4_id),
                    tenant_id=self._tenant_id,
                    order_no=row["order_no"],
                    status=map_status(row["status"]),
                    supplier_id=self._id_map.require("t_supplier", _int(row["supplier_id"])),
                    total_amount=_decimal(row["total_amount"]),
                    currency=row.get("currency", "CNY"),
                    expected_arrival=date_to_utc(row.get("expected_date")),
                    created_at=to_utc(row.get("create_time")) or datetime.utcnow(),
                    updated_at=to_utc(row.get("update_time")) or datetime.utcnow(),
                )

                for ln in lines_by_order.get(v4_id, []):
                    # product_id: 用 material_id 做 legacy 映射
                    product_uuid = self._id_map.get_or_create("product", _int(ln["material_id"]))
                    po.lines.append(PurchaseOrderLine(
                        id=self._id_map.get_or_create("t_purchase_order_detail", _int(ln["id"])),
                        product_id=product_uuid,
                        quantity=_decimal(ln["quantity"]),
                        uom=map_uom(ln.get("unit", "件")),
                        unit_price=_decimal(ln["unit_price"]),
                        currency=row.get("currency", "CNY"),
                        line_total=_decimal(ln["amount"]),
                        received_quantity=_decimal(ln.get("received_qty", 0)),
                    ))

                self._session.add(po)
                stats.v5_count += 1
            except Exception as e:
                stats.errors.append(f"Row {row.get('id')}: {e}")
        await self._session.flush()
        return stats

    # ------------------------------------------------------------------ #
    # 8. Inventory
    # ------------------------------------------------------------------ #

    async def _load_inventory(self, rows: list[dict]) -> ETLStats:
        stats = ETLStats(table="inventory", v4_count=len(rows))
        for row in rows:
            try:
                product_uuid = self._id_map.get_or_create("product", _int(row["material_id"]))
                wh_uuid = self._id_map.require("t_warehouse", _int(row["warehouse_id"]))

                inv = Inventory(
                    id=self._id_map.get_or_create("t_inventory", _int(row["id"])),
                    tenant_id=self._tenant_id,
                    product_id=product_uuid,
                    warehouse_id=wh_uuid,
                    uom=map_uom(row.get("unit", "件")),
                    batch_no=row.get("batch_no", "") or "",
                    expiry_date=date_to_utc(row.get("expiry_date")),
                    on_hand=_decimal(row["quantity"]),
                    reserved=_decimal(row.get("locked_qty", 0)),
                    in_transit=_decimal(row.get("in_transit_qty", 0)),
                    updated_at=to_utc(row.get("update_time")) or datetime.utcnow(),
                )
                self._session.add(inv)
                stats.v5_count += 1
            except Exception as e:
                stats.errors.append(f"Row {row.get('id')}: {e}")
        await self._session.flush()
        return stats

    # ------------------------------------------------------------------ #
    # 9. Stock Moves (合并 in + out)
    # ------------------------------------------------------------------ #

    async def _load_stock_moves(
        self, in_rows: list[dict], out_rows: list[dict],
    ) -> ETLStats:
        total = len(in_rows) + len(out_rows)
        stats = ETLStats(table="stock_moves", v4_count=total)

        for row in in_rows:
            try:
                await self._load_one_move(row, direction="in")
                stats.v5_count += 1
            except Exception as e:
                stats.errors.append(f"stock_in row {row.get('id')}: {e}")

        for row in out_rows:
            try:
                await self._load_one_move(row, direction="out")
                stats.v5_count += 1
            except Exception as e:
                stats.errors.append(f"stock_out row {row.get('id')}: {e}")

        await self._session.flush()
        return stats

    async def _load_one_move(self, row: dict, direction: str) -> None:
        ref_type = row.get("ref_type", "")
        if direction == "in":
            move_type = STOCK_IN_TYPE_MAP.get(ref_type, "purchase_receipt")
            table = "t_stock_in"
        else:
            move_type = STOCK_OUT_TYPE_MAP.get(ref_type, "sales_issue")
            table = "t_stock_out"

        product_uuid = self._id_map.get_or_create("product", _int(row["material_id"]))
        wh_uuid = self._id_map.require("t_warehouse", _int(row["warehouse_id"]))

        self._move_seq += 1
        move = StockMove(
            id=self._id_map.get_or_create(table, _int(row["id"])),
            tenant_id=self._tenant_id,
            move_no=row.get("bill_no", f"MIG-{self._move_seq:06d}"),
            type=move_type,
            product_id=product_uuid,
            quantity=_decimal(row["quantity"]),
            uom=map_uom(row.get("unit", "件")),
            warehouse_id=wh_uuid,
            remark=row.get("remark", ""),
            created_at=to_utc(row.get("operate_time")) or datetime.utcnow(),
            updated_at=to_utc(row.get("operate_time")) or datetime.utcnow(),
        )
        self._session.add(move)

    # ------------------------------------------------------------------ #
    # 10. Stocktakes
    # ------------------------------------------------------------------ #

    async def _load_stocktakes(
        self, st_rows: list[dict], line_rows: list[dict],
    ) -> ETLStats:
        stats = ETLStats(table="stocktakes", v4_count=len(st_rows))
        lines_by_st: dict[int, list[dict]] = {}
        for ln in line_rows:
            sid = _int(ln["stocktake_id"])
            lines_by_st.setdefault(sid, []).append(ln)

        for row in st_rows:
            try:
                v4_id = _int(row["id"])
                st = Stocktake(
                    id=self._id_map.get_or_create("t_stocktake", v4_id),
                    tenant_id=self._tenant_id,
                    stocktake_no=row["stocktake_no"],
                    status=map_status(row.get("status", 0)),
                    warehouse_id=self._id_map.require("t_warehouse", _int(row["warehouse_id"])),
                    stocktake_date=date_to_utc(row.get("stocktake_date")),
                    created_at=to_utc(row.get("create_time")) or datetime.utcnow(),
                    updated_at=to_utc(row.get("create_time")) or datetime.utcnow(),
                )

                for ln in lines_by_st.get(v4_id, []):
                    product_uuid = self._id_map.get_or_create("product", _int(ln["material_id"]))
                    st.lines.append(StocktakeLine(
                        id=self._id_map.get_or_create("t_stocktake_detail", _int(ln["id"])),
                        product_id=product_uuid,
                        system_quantity=_decimal(ln["system_qty"]),
                        actual_quantity=_decimal(ln["actual_qty"]),
                        variance=_decimal(ln["variance_qty"]),
                        remark=ln.get("remark"),
                    ))

                self._session.add(st)
                stats.v5_count += 1
            except Exception as e:
                stats.errors.append(f"Row {row.get('id')}: {e}")
        await self._session.flush()
        return stats
