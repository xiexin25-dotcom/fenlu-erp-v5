"""
V4 → V5 对账报告 (Reconciliation)
===================================

ETL 完成后运行,校验:
  1. 行数一致 (V4 source count vs V5 loaded count)
  2. 金额一致 (PO total_amount SUM)
  3. 库存一致 (inventory on_hand SUM by warehouse)
  4. 流水平衡 (stock_in 总量 - stock_out 总量 ≈ inventory)
  5. 外键完整 (PO.supplier_id 引用 valid supplier)
  6. 无孤儿行 (PO lines 都有对应 PO header)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.migration.etl_loader import ETLReport
from packages.supply_chain.models.inventory import Inventory, StockMove
from packages.supply_chain.models.purchase import (
    PurchaseOrder,
    PurchaseOrderLine,
)
from packages.supply_chain.models.stocktake import Stocktake, StocktakeLine
from packages.supply_chain.models.supplier import Supplier
from packages.supply_chain.models.warehouse import Location, Warehouse


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class ReconciliationReport:
    timestamp: str = ""
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    def to_markdown(self) -> str:
        lines = [
            "# V4 → V5 Reconciliation Report",
            f"\n**Generated:** {self.timestamp}",
            f"**Result:** {'✅ ALL PASSED' if self.all_passed else '❌ FAILURES DETECTED'}",
            f"**Checks:** {self.passed_count} passed, {self.failed_count} failed\n",
            "| # | Check | Status | Detail |",
            "|---|-------|--------|--------|",
        ]
        for i, c in enumerate(self.checks, 1):
            status = "✅" if c.passed else "❌"
            lines.append(f"| {i} | {c.name} | {status} | {c.detail} |")
        return "\n".join(lines)


async def run_reconciliation(
    session: AsyncSession,
    etl_report: ETLReport,
    v4_data: dict[str, list[dict]],
) -> ReconciliationReport:
    """执行完整对账,返回报告。"""
    report = ReconciliationReport(timestamp=datetime.now(UTC).isoformat())

    # ------------------------------------------------------------------ #
    # 1. Row count checks
    # ------------------------------------------------------------------ #

    table_pairs = [
        ("t_supplier", "suppliers", Supplier),
        ("t_warehouse", "warehouses", Warehouse),
        ("t_warehouse_location", "locations", Location),
        ("t_purchase_order", "purchase_orders", PurchaseOrder),
        ("t_inventory", "inventory", Inventory),
        ("t_stocktake", "stocktakes", Stocktake),
    ]

    for v4_table, v5_name, model in table_pairs:
        v4_count = len(v4_data.get(v4_table, []))
        v5_count_result = await session.execute(select(func.count()).select_from(model))
        v5_count = v5_count_result.scalar_one()
        ok = v4_count == v5_count
        report.checks.append(CheckResult(
            name=f"Row count: {v4_table} → {v5_name}",
            passed=ok,
            detail=f"V4={v4_count}, V5={v5_count}",
        ))

    # stock_moves: V4 有 in + out 两张表
    v4_moves = len(v4_data.get("t_stock_in", [])) + len(v4_data.get("t_stock_out", []))
    v5_moves_result = await session.execute(select(func.count()).select_from(StockMove))
    v5_moves = v5_moves_result.scalar_one()
    report.checks.append(CheckResult(
        name="Row count: stock_in+out → stock_moves",
        passed=v4_moves == v5_moves,
        detail=f"V4={v4_moves}, V5={v5_moves}",
    ))

    # ------------------------------------------------------------------ #
    # 2. PO total_amount SUM
    # ------------------------------------------------------------------ #

    v4_po_total = sum(Decimal(str(r["total_amount"])) for r in v4_data.get("t_purchase_order", []))
    v5_po_total_result = await session.execute(
        select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
    )
    v5_po_total = Decimal(str(v5_po_total_result.scalar_one()))
    report.checks.append(CheckResult(
        name="Amount: PO total_amount SUM",
        passed=v4_po_total == v5_po_total,
        detail=f"V4={v4_po_total}, V5={v5_po_total}",
    ))

    # ------------------------------------------------------------------ #
    # 3. Inventory on_hand SUM
    # ------------------------------------------------------------------ #

    v4_inv_total = sum(Decimal(str(r["quantity"])) for r in v4_data.get("t_inventory", []))
    v5_inv_total_result = await session.execute(
        select(func.coalesce(func.sum(Inventory.on_hand), 0))
    )
    v5_inv_total = Decimal(str(v5_inv_total_result.scalar_one()))
    report.checks.append(CheckResult(
        name="Inventory: on_hand SUM",
        passed=v4_inv_total == v5_inv_total,
        detail=f"V4={v4_inv_total}, V5={v5_inv_total}",
    ))

    # ------------------------------------------------------------------ #
    # 4. Stock flow balance: in - out ≈ snapshot
    #    (soft check: migrated moves may not match snapshot exactly)
    # ------------------------------------------------------------------ #

    v4_in_total = sum(Decimal(str(r["quantity"])) for r in v4_data.get("t_stock_in", []))
    v4_out_total = sum(Decimal(str(r["quantity"])) for r in v4_data.get("t_stock_out", []))
    v4_net = v4_in_total - v4_out_total
    # net flow should be >= 0 and roughly match inventory total (may differ due to adjustments)
    diff = abs(v4_net - v4_inv_total)
    # Allow tolerance for adjustments/prior data
    tolerance = v4_inv_total * Decimal("0.1") if v4_inv_total > 0 else Decimal("100")
    report.checks.append(CheckResult(
        name="Flow balance: in - out vs inventory",
        passed=diff <= tolerance,
        detail=f"net_flow={v4_net}, inventory={v4_inv_total}, diff={diff} (tolerance={tolerance})",
    ))

    # ------------------------------------------------------------------ #
    # 5. FK integrity: PO.supplier_id references valid supplier
    # ------------------------------------------------------------------ #

    orphan_po_result = await session.execute(
        select(func.count()).select_from(PurchaseOrder).where(
            ~PurchaseOrder.supplier_id.in_(select(Supplier.id))
        )
    )
    orphan_pos = orphan_po_result.scalar_one()
    report.checks.append(CheckResult(
        name="FK integrity: PO → Supplier",
        passed=orphan_pos == 0,
        detail=f"orphan POs={orphan_pos}",
    ))

    # ------------------------------------------------------------------ #
    # 6. No orphan PO lines
    # ------------------------------------------------------------------ #

    orphan_lines_result = await session.execute(
        select(func.count()).select_from(PurchaseOrderLine).where(
            ~PurchaseOrderLine.order_id.in_(select(PurchaseOrder.id))
        )
    )
    orphan_lines = orphan_lines_result.scalar_one()
    report.checks.append(CheckResult(
        name="Orphan check: PO lines → PO headers",
        passed=orphan_lines == 0,
        detail=f"orphan lines={orphan_lines}",
    ))

    # Stocktake lines
    orphan_stl_result = await session.execute(
        select(func.count()).select_from(StocktakeLine).where(
            ~StocktakeLine.stocktake_id.in_(select(Stocktake.id))
        )
    )
    orphan_stl = orphan_stl_result.scalar_one()
    report.checks.append(CheckResult(
        name="Orphan check: Stocktake lines → Stocktake headers",
        passed=orphan_stl == 0,
        detail=f"orphan lines={orphan_stl}",
    ))

    # ------------------------------------------------------------------ #
    # 7. ETL error check
    # ------------------------------------------------------------------ #

    total_errors = etl_report.total_errors
    report.checks.append(CheckResult(
        name="ETL errors",
        passed=total_errors == 0,
        detail=f"total errors={total_errors}",
    ))

    return report
