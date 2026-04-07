"""
SCM · 盘点服务层
================

盘点确认时:
  1. 计算每行 variance = actual_quantity - system_quantity
  2. variance > 0 → adjustment_in (盘盈)
  3. variance < 0 → adjustment_out (盘亏)
  4. variance == 0 → 无操作
  所有调整通过 InventoryService.create_move() 保持不可变流水原则。
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    StockMoveCreate,
    StocktakeCreate,
)
from packages.supply_chain.models.inventory import Inventory, StockMove
from packages.supply_chain.models.stocktake import (
    Stocktake,
    StocktakeLine,
    validate_stocktake_transition,
)
from packages.supply_chain.services.inventory_service import InventoryService


class StocktakeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inv_svc = InventoryService(session)

    # ================================================================== #
    # Create
    # ================================================================== #

    async def create_stocktake(
        self, tenant_id: UUID, data: StocktakeCreate,
    ) -> Stocktake:
        st = Stocktake(
            tenant_id=tenant_id,
            stocktake_no=data.stocktake_no,
            warehouse_id=data.warehouse_id,
            stocktake_date=data.stocktake_date,
            remark=data.remark,
            status="draft",
        )

        for ln in data.lines:
            # 快照当前系统库存
            system_qty = await self._get_system_qty(
                tenant_id, ln.product_id, data.warehouse_id, ln.batch_no,
            )
            variance = ln.actual_quantity - system_qty
            st.lines.append(StocktakeLine(
                product_id=ln.product_id,
                batch_no=ln.batch_no,
                uom=ln.uom,
                system_quantity=system_qty,
                actual_quantity=ln.actual_quantity,
                variance=variance,
                remark=ln.remark,
            ))

        self._session.add(st)
        await self._session.flush()
        return st

    async def _get_system_qty(
        self, tenant_id: UUID, product_id: UUID, warehouse_id: UUID, batch_no: str,
    ) -> Decimal:
        inv = await self._inv_svc.get_inventory(tenant_id, product_id, warehouse_id, batch_no)
        return inv.on_hand if inv else Decimal(0)

    # ================================================================== #
    # Read
    # ================================================================== #

    async def get_stocktake(self, tenant_id: UUID, st_id: UUID) -> Stocktake | None:
        stmt = select(Stocktake).where(
            Stocktake.tenant_id == tenant_id,
            Stocktake.id == st_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_stocktakes(
        self, tenant_id: UUID, warehouse_id: UUID | None = None,
    ) -> list[Stocktake]:
        stmt = select(Stocktake).where(Stocktake.tenant_id == tenant_id)
        if warehouse_id is not None:
            stmt = stmt.where(Stocktake.warehouse_id == warehouse_id)
        stmt = stmt.order_by(Stocktake.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    # ================================================================== #
    # Confirm (核心: 产生 adjustment moves)
    # ================================================================== #

    async def confirm_stocktake(
        self, tenant_id: UUID, st_id: UUID,
    ) -> tuple[Stocktake, list[StockMove]]:
        """确认盘点: draft → confirmed, 按 variance 创建 adjustment moves。"""
        st = await self.get_stocktake(tenant_id, st_id)
        if st is None:
            raise ValueError(f"Stocktake {st_id} not found")

        validate_stocktake_transition(st.status, "confirmed")

        moves: list[StockMove] = []
        for line in st.lines:
            if line.variance == Decimal(0):
                continue

            if line.variance > Decimal(0):
                # 盘盈: actual > system → adjustment_in
                move_type = "adjustment_in"
                qty = line.variance
            else:
                # 盘亏: actual < system → adjustment_out
                move_type = "adjustment_out"
                qty = abs(line.variance)

            move, _ = await self._inv_svc.create_move(
                tenant_id,
                StockMoveCreate(
                    type=move_type,
                    product_id=line.product_id,
                    quantity=qty,
                    uom=line.uom,
                    warehouse_id=st.warehouse_id,
                    batch_no=line.batch_no,
                    reference_id=st.id,
                    remark=f"Stocktake adjustment: {st.stocktake_no}",
                ),
            )
            moves.append(move)

        st.status = "confirmed"
        await self._session.flush()
        return st, moves

    # ================================================================== #
    # Close / Cancel
    # ================================================================== #

    async def transition_stocktake(
        self, tenant_id: UUID, st_id: UUID, to_status: str,
    ) -> Stocktake:
        st = await self.get_stocktake(tenant_id, st_id)
        if st is None:
            raise ValueError(f"Stocktake {st_id} not found")
        validate_stocktake_transition(st.status, to_status)
        st.status = to_status
        await self._session.flush()
        return st
