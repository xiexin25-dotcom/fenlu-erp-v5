"""
SCM · 采购链服务层
==================

PR → RFQ → PO → Receipt 全链路,含状态转换强制校验。
PO 审批时 emit PurchaseOrderApprovedEvent 到 scm-events。
BOM-driven purchase: Lane 1 → explode BOM → 按供应商分组 → 创建 PR。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.contracts.product_lifecycle import BOMDTO
from packages.supply_chain.api.schemas import (
    POCreate,
    PRCreate,
    PRLineCreate,
    ReceiptCreate,
    RFQCreate,
    RFQLineUpdate,
)
from packages.supply_chain.models.purchase import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseReceipt,
    PurchaseReceiptLine,
    PurchaseRequest,
    PurchaseRequestLine,
    RFQ,
    RFQLine,
    validate_transition,
)
from packages.supply_chain.models.supplier_product import SupplierProduct
from packages.supply_chain.services.bom_client import BOMClient, HttpBOMClient
from packages.supply_chain.services.event_publisher import (
    EventPublisher,
    RedisEventPublisher,
)


class PurchaseService:
    def __init__(
        self,
        session: AsyncSession,
        event_publisher: EventPublisher | None = None,
        bom_client: BOMClient | None = None,
    ) -> None:
        self._session = session
        self._events = event_publisher or RedisEventPublisher()
        self._bom_client = bom_client or HttpBOMClient()

    # ================================================================== #
    # Purchase Request
    # ================================================================== #

    async def create_pr(self, tenant_id: UUID, data: PRCreate) -> PurchaseRequest:
        pr = PurchaseRequest(
            tenant_id=tenant_id,
            request_no=data.request_no,
            needed_by=data.needed_by,
            department_id=data.department_id,
            remark=data.remark,
            status="draft",
        )
        for ln in data.lines:
            pr.lines.append(PurchaseRequestLine(
                product_id=ln.product_id,
                quantity=ln.quantity,
                uom=ln.uom,
                remark=ln.remark,
            ))
        self._session.add(pr)
        await self._session.flush()
        return pr

    async def get_pr(self, tenant_id: UUID, pr_id: UUID) -> PurchaseRequest | None:
        stmt = select(PurchaseRequest).where(
            PurchaseRequest.tenant_id == tenant_id,
            PurchaseRequest.id == pr_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def transition_pr(
        self, tenant_id: UUID, pr_id: UUID, to_status: str,
    ) -> PurchaseRequest:
        pr = await self.get_pr(tenant_id, pr_id)
        if pr is None:
            raise ValueError(f"PurchaseRequest {pr_id} not found")
        validate_transition("purchase_request", pr.status, to_status)
        pr.status = to_status
        await self._session.flush()
        return pr

    # ================================================================== #
    # RFQ
    # ================================================================== #

    async def create_rfq(self, tenant_id: UUID, data: RFQCreate) -> RFQ:
        rfq = RFQ(
            tenant_id=tenant_id,
            rfq_no=data.rfq_no,
            supplier_id=data.supplier_id,
            request_id=data.request_id,
            valid_until=data.valid_until,
            remark=data.remark,
            status="draft",
        )
        for ln in data.lines:
            rfq.lines.append(RFQLine(
                product_id=ln.product_id,
                quantity=ln.quantity,
                uom=ln.uom,
            ))
        self._session.add(rfq)
        await self._session.flush()
        return rfq

    async def get_rfq(self, tenant_id: UUID, rfq_id: UUID) -> RFQ | None:
        stmt = select(RFQ).where(RFQ.tenant_id == tenant_id, RFQ.id == rfq_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def transition_rfq(
        self, tenant_id: UUID, rfq_id: UUID, to_status: str,
    ) -> RFQ:
        rfq = await self.get_rfq(tenant_id, rfq_id)
        if rfq is None:
            raise ValueError(f"RFQ {rfq_id} not found")
        validate_transition("rfq", rfq.status, to_status)
        rfq.status = to_status
        await self._session.flush()
        return rfq

    async def update_rfq_line_price(
        self, tenant_id: UUID, rfq_id: UUID, line_id: UUID, data: RFQLineUpdate,
    ) -> RFQLine:
        rfq = await self.get_rfq(tenant_id, rfq_id)
        if rfq is None:
            raise ValueError(f"RFQ {rfq_id} not found")
        for ln in rfq.lines:
            if ln.id == line_id:
                if data.quoted_unit_price is not None:
                    ln.quoted_unit_price = data.quoted_unit_price
                await self._session.flush()
                return ln
        raise ValueError(f"RFQ line {line_id} not found")

    # ================================================================== #
    # Purchase Order
    # ================================================================== #

    async def create_po(self, tenant_id: UUID, data: POCreate) -> PurchaseOrder:
        po = PurchaseOrder(
            tenant_id=tenant_id,
            order_no=data.order_no,
            supplier_id=data.supplier_id,
            rfq_id=data.rfq_id,
            expected_arrival=data.expected_arrival,
            currency=data.currency,
            payment_terms=data.payment_terms,
            remark=data.remark,
            status="draft",
        )
        total = Decimal(0)
        for ln in data.lines:
            line_total = ln.quantity * ln.unit_price
            total += line_total
            po.lines.append(PurchaseOrderLine(
                product_id=ln.product_id,
                quantity=ln.quantity,
                uom=ln.uom,
                unit_price=ln.unit_price,
                currency=ln.currency,
                line_total=line_total,
            ))
        po.total_amount = total
        self._session.add(po)
        await self._session.flush()
        return po

    async def get_po(self, tenant_id: UUID, po_id: UUID) -> PurchaseOrder | None:
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.id == po_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def transition_po(
        self, tenant_id: UUID, po_id: UUID, to_status: str,
    ) -> PurchaseOrder:
        po = await self.get_po(tenant_id, po_id)
        if po is None:
            raise ValueError(f"PurchaseOrder {po_id} not found")
        validate_transition("purchase_order", po.status, to_status)
        po.status = to_status
        await self._session.flush()

        # PO approved → emit event to scm-events
        if to_status == "approved":
            await self._emit_po_approved(po)

        return po

    async def _emit_po_approved(self, po: PurchaseOrder) -> None:
        await self._events.publish(
            "po.approved",
            {
                "purchase_order_id": str(po.id),
                "order_no": po.order_no,
                "supplier_id": str(po.supplier_id),
                "total_amount": str(po.total_amount),
                "currency": po.currency,
                "tenant_id": str(po.tenant_id),
            },
        )

    # ================================================================== #
    # Purchase Receipt
    # ================================================================== #

    async def create_receipt(self, tenant_id: UUID, data: ReceiptCreate) -> PurchaseReceipt:
        # 验证 PO 存在且已审批
        po = await self.get_po(tenant_id, data.order_id)
        if po is None:
            raise ValueError(f"PurchaseOrder {data.order_id} not found")
        if po.status != "approved":
            raise ValueError(f"PurchaseOrder must be approved to receive (current: {po.status})")

        receipt = PurchaseReceipt(
            tenant_id=tenant_id,
            receipt_no=data.receipt_no,
            order_id=data.order_id,
            supplier_id=data.supplier_id,
            warehouse_id=data.warehouse_id,
            received_at=data.received_at,
            remark=data.remark,
            status="draft",
        )
        for ln in data.lines:
            receipt.lines.append(PurchaseReceiptLine(
                product_id=ln.product_id,
                ordered_quantity=ln.ordered_quantity,
                received_quantity=ln.received_quantity,
                rejected_quantity=ln.rejected_quantity,
                uom=ln.uom,
                batch_no=ln.batch_no,
            ))
        self._session.add(receipt)
        await self._session.flush()
        return receipt

    async def get_receipt(self, tenant_id: UUID, receipt_id: UUID) -> PurchaseReceipt | None:
        stmt = select(PurchaseReceipt).where(
            PurchaseReceipt.tenant_id == tenant_id,
            PurchaseReceipt.id == receipt_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def transition_receipt(
        self, tenant_id: UUID, receipt_id: UUID, to_status: str,
    ) -> PurchaseReceipt:
        receipt = await self.get_receipt(tenant_id, receipt_id)
        if receipt is None:
            raise ValueError(f"PurchaseReceipt {receipt_id} not found")
        validate_transition("purchase_receipt", receipt.status, to_status)
        receipt.status = to_status

        # confirmed → 回写 PO 行已收数量
        if to_status == "confirmed":
            await self._update_po_received(receipt)

        await self._session.flush()
        return receipt

    async def _update_po_received(self, receipt: PurchaseReceipt) -> None:
        """确认收货后,累加 PO 行的 received_quantity。"""
        po = await self.get_po(receipt.tenant_id, receipt.order_id)
        if po is None:
            return
        po_line_map = {ln.product_id: ln for ln in po.lines}
        for rln in receipt.lines:
            po_ln = po_line_map.get(rln.product_id)
            if po_ln:
                po_ln.received_quantity += rln.received_quantity

        # 检查是否全部收齐 → 自动关闭 PO
        all_received = all(
            ln.received_quantity >= ln.quantity for ln in po.lines
        )
        if all_received:
            po.status = "closed"

    # ================================================================== #
    # SupplierProduct helpers
    # ================================================================== #

    async def create_supplier_product(
        self, tenant_id: UUID, data: "SupplierProductCreate",
    ) -> SupplierProduct:
        from packages.supply_chain.api.schemas import SupplierProductCreate as _SPC  # noqa: F811
        sp = SupplierProduct(
            tenant_id=tenant_id,
            supplier_id=data.supplier_id,
            product_id=data.product_id,
            is_preferred=data.is_preferred,
            lead_days=data.lead_days,
            min_order_qty=data.min_order_qty,
            uom=data.uom,
            reference_price=data.reference_price,
            currency=data.currency,
        )
        self._session.add(sp)
        await self._session.flush()
        return sp

    async def get_preferred_suppliers(
        self, tenant_id: UUID, product_ids: list[UUID],
    ) -> dict[UUID, SupplierProduct]:
        """返回每个 product_id 的首选供应商映射。优先 is_preferred=True。"""
        if not product_ids:
            return {}
        stmt = (
            select(SupplierProduct)
            .where(
                SupplierProduct.tenant_id == tenant_id,
                SupplierProduct.product_id.in_(product_ids),
            )
            .order_by(SupplierProduct.is_preferred.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()

        # 每个 product_id 取第一个 (is_preferred 优先排在前面)
        result: dict[UUID, SupplierProduct] = {}
        for sp in rows:
            if sp.product_id not in result:
                result[sp.product_id] = sp
        return result

    # ================================================================== #
    # BOM-driven purchase (TASK-SCM-004)
    # ================================================================== #

    async def purchase_from_bom(
        self,
        tenant_id: UUID,
        bom_id: UUID,
        target_quantity: Decimal,
        target_uom: str,
        needed_by: datetime,
        requested_by: UUID,
    ) -> tuple[list[PurchaseRequest], list[UUID]]:
        """
        BOM 反算采购:
        1. 从 Lane 1 获取 BOM
        2. 计算每个组件净需求 = component_qty * target_qty * (1 + scrap_rate)
        3. 查 SupplierProduct 找首选供应商
        4. 按供应商分组,每组创建一个 PR

        Returns: (创建的 PR 列表, 未匹配供应商的 product_id 列表)
        """
        # 1. Fetch BOM from Lane 1
        bom = await self._bom_client.get_bom(bom_id)
        if bom is None:
            raise ValueError(f"BOM {bom_id} not found (Lane 1 unreachable or BOM does not exist)")
        if not bom.items:
            raise ValueError(f"BOM {bom_id} has no items")

        # 2. Calculate required quantities per component
        requirements: list[tuple[UUID, Decimal, str]] = []  # (product_id, qty, uom)
        for item in bom.items:
            gross_qty = item.quantity.value * target_quantity * (1 + Decimal(str(item.scrap_rate)))
            requirements.append((item.component_id, gross_qty, item.quantity.uom.value))

        # 3. Find preferred suppliers
        product_ids = [r[0] for r in requirements]
        supplier_map = await self.get_preferred_suppliers(tenant_id, product_ids)

        # 4. Group by supplier
        # supplier_id → [(product_id, qty, uom)]
        grouped: dict[UUID, list[tuple[UUID, Decimal, str]]] = defaultdict(list)
        unmapped: list[UUID] = []

        for product_id, qty, uom in requirements:
            sp = supplier_map.get(product_id)
            if sp is None:
                unmapped.append(product_id)
            else:
                grouped[sp.supplier_id].append((product_id, qty, uom))

        # 5. Create one PR per supplier
        prs: list[PurchaseRequest] = []
        pr_seq = 1
        for supplier_id, items in grouped.items():
            pr_no = f"PR-BOM-{str(bom_id)[:8]}-{pr_seq:02d}"
            lines = [
                PRLineCreate(product_id=pid, quantity=qty, uom=uom)
                for pid, qty, uom in items
            ]
            pr = await self.create_pr(
                tenant_id,
                PRCreate(
                    request_no=pr_no,
                    needed_by=needed_by,
                    remark=f"BOM-driven: bom={bom_id}, target_qty={target_quantity}",
                    lines=lines,
                ),
            )
            pr.requested_by = requested_by
            await self._session.flush()
            prs.append(pr)
            pr_seq += 1

        return prs, unmapped
