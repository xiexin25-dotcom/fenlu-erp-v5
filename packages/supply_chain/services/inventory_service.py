"""
SCM · 库存服务层
================

核心不变量: 所有库存变动必须通过 StockMove。
Inventory 行只能由本 service 内部的 _apply_move() 更新。

StockMoveType 对库存的影响:
  purchase_receipt    → on_hand +qty  (入库)
  production_receipt  → on_hand +qty  (生产入库)
  sales_issue         → on_hand -qty  (销售出库)
  production_issue    → on_hand -qty  (生产领料)
  transfer            → 源仓 -qty, 目标仓 +qty
  adjustment          → on_hand ±qty  (盘点调整, qty 可正可负在 move 层面始终>0, 方向由 type 子类区分)
  scrap               → on_hand -qty
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    InventoryListParams,
    StockMoveCreate,
)
from packages.supply_chain.models.inventory import Inventory, StockMove

# Move types that increase on_hand
_INBOUND_TYPES = {"purchase_receipt", "production_receipt", "adjustment_in"}
# Move types that decrease on_hand
_OUTBOUND_TYPES = {"sales_issue", "production_issue", "scrap", "adjustment_out"}


def _generate_move_no() -> str:
    return f"SM-{uuid4().hex[:12].upper()}"


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ================================================================== #
    # Inventory queries
    # ================================================================== #

    async def get_inventory(
        self, tenant_id: UUID, product_id: UUID, warehouse_id: UUID, batch_no: str = "",
    ) -> Inventory | None:
        stmt = select(Inventory).where(
            Inventory.tenant_id == tenant_id,
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id,
            Inventory.batch_no == batch_no,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_inventory(
        self, tenant_id: UUID, params: InventoryListParams,
    ) -> tuple[list[Inventory], int]:
        base = select(Inventory).where(Inventory.tenant_id == tenant_id)

        if params.product_id is not None:
            base = base.where(Inventory.product_id == params.product_id)
        if params.warehouse_id is not None:
            base = base.where(Inventory.warehouse_id == params.warehouse_id)
        if params.batch_no is not None:
            base = base.where(Inventory.batch_no == params.batch_no)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        items_stmt = (
            base
            .order_by(Inventory.product_id, Inventory.warehouse_id)
            .offset((params.page - 1) * params.size)
            .limit(params.size)
        )
        rows = (await self._session.execute(items_stmt)).scalars().all()
        return list(rows), total

    # ================================================================== #
    # Stock move (核心入口)
    # ================================================================== #

    async def create_move(
        self, tenant_id: UUID, data: StockMoveCreate,
    ) -> tuple[StockMove, Inventory]:
        """创建 StockMove 并更新 Inventory。返回 (move, 变更后的 inventory)。"""
        move = StockMove(
            tenant_id=tenant_id,
            move_no=_generate_move_no(),
            type=data.type,
            product_id=data.product_id,
            quantity=data.quantity,
            uom=data.uom,
            warehouse_id=data.warehouse_id,
            from_location=data.from_location,
            to_location=data.to_location,
            batch_no=data.batch_no,
            reference_id=data.reference_id,
            remark=data.remark,
        )
        self._session.add(move)
        inv = await self._apply_move(tenant_id, data)
        await self._session.flush()
        return move, inv

    async def _apply_move(
        self, tenant_id: UUID, data: StockMoveCreate,
    ) -> Inventory:
        """根据 move type 更新 Inventory 行。"""
        inv = await self._get_or_create_inventory(
            tenant_id, data.product_id, data.warehouse_id, data.batch_no, data.uom,
        )

        if data.type in _INBOUND_TYPES:
            inv.on_hand += data.quantity
        elif data.type in _OUTBOUND_TYPES:
            if inv.on_hand < data.quantity:
                raise ValueError(
                    f"Insufficient stock: on_hand={inv.on_hand}, requested={data.quantity} "
                    f"(product={data.product_id}, warehouse={data.warehouse_id}, batch={data.batch_no!r})"
                )
            inv.on_hand -= data.quantity
        elif data.type == "transfer":
            # transfer 只减源仓,目标仓由调用方创建另一个 inbound move
            if inv.on_hand < data.quantity:
                raise ValueError(
                    f"Insufficient stock for transfer: on_hand={inv.on_hand}, requested={data.quantity}"
                )
            inv.on_hand -= data.quantity
        elif data.type == "adjustment":
            # 通用调整: 正数入, 负数出 (quantity 在 schema 层强制 >0, 所以这里统一加)
            inv.on_hand += data.quantity
        else:
            raise ValueError(f"Unknown stock move type: {data.type}")

        return inv

    async def _get_or_create_inventory(
        self,
        tenant_id: UUID,
        product_id: UUID,
        warehouse_id: UUID,
        batch_no: str,
        uom: str,
    ) -> Inventory:
        inv = await self.get_inventory(tenant_id, product_id, warehouse_id, batch_no)
        if inv is None:
            inv = Inventory(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                batch_no=batch_no,
                uom=uom,
            )
            self._session.add(inv)
            await self._session.flush()
        return inv

    # ================================================================== #
    # 领料 (Lane 2 调用)
    # ================================================================== #

    async def issue_material(
        self,
        tenant_id: UUID,
        product_id: UUID,
        quantity: Decimal,
        uom: str,
        warehouse_id: UUID,
        batch_no: str = "",
        work_order_id: UUID | None = None,
    ) -> tuple[StockMove, Inventory]:
        """Lane 2 领料: 创建 production_issue move, 扣减 on_hand。"""
        data = StockMoveCreate(
            type="production_issue",
            product_id=product_id,
            quantity=quantity,
            uom=uom,
            warehouse_id=warehouse_id,
            batch_no=batch_no,
            reference_id=work_order_id,
            remark=f"Production issue for work_order={work_order_id}" if work_order_id else "Production issue",
        )
        return await self.create_move(tenant_id, data)

    # ================================================================== #
    # 采购入库 (Receipt confirm 后调用)
    # ================================================================== #

    async def receive_stock(
        self,
        tenant_id: UUID,
        product_id: UUID,
        quantity: Decimal,
        uom: str,
        warehouse_id: UUID,
        to_location: str | None = None,
        batch_no: str = "",
        reference_id: UUID | None = None,
    ) -> tuple[StockMove, Inventory]:
        """采购入库: 创建 purchase_receipt move, 增加 on_hand。"""
        data = StockMoveCreate(
            type="purchase_receipt",
            product_id=product_id,
            quantity=quantity,
            uom=uom,
            warehouse_id=warehouse_id,
            to_location=to_location,
            batch_no=batch_no,
            reference_id=reference_id,
            remark=f"Purchase receipt ref={reference_id}" if reference_id else "Purchase receipt",
        )
        return await self.create_move(tenant_id, data)

    # ================================================================== #
    # 预留 / 取消预留
    # ================================================================== #

    async def reserve(
        self, tenant_id: UUID, product_id: UUID, warehouse_id: UUID,
        quantity: Decimal, batch_no: str = "",
    ) -> Inventory:
        """预留库存 (不创建 StockMove, 只调整 reserved)。"""
        inv = await self.get_inventory(tenant_id, product_id, warehouse_id, batch_no)
        if inv is None:
            raise ValueError("Inventory record not found")
        if inv.available < quantity:
            raise ValueError(
                f"Insufficient available stock: available={inv.available}, requested={quantity}"
            )
        inv.reserved += quantity
        await self._session.flush()
        return inv

    async def unreserve(
        self, tenant_id: UUID, product_id: UUID, warehouse_id: UUID,
        quantity: Decimal, batch_no: str = "",
    ) -> Inventory:
        """取消预留。"""
        inv = await self.get_inventory(tenant_id, product_id, warehouse_id, batch_no)
        if inv is None:
            raise ValueError("Inventory record not found")
        if inv.reserved < quantity:
            raise ValueError(
                f"Cannot unreserve more than reserved: reserved={inv.reserved}, requested={quantity}"
            )
        inv.reserved -= quantity
        await self._session.flush()
        return inv
