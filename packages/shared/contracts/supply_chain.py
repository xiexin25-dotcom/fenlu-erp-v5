"""
Lane 3 · 供应链 对外契约
========================

本文件定义 Lane 3 (采购/仓储) 暴露给其他 lane 的 DTO。
工信部场景: 采购管理* / 仓储物流
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, DocumentStatus, Money, Quantity, TimestampMixin

# --------------------------------------------------------------------------- #
# 供应商
# --------------------------------------------------------------------------- #


class SupplierTier(StrEnum):
    STRATEGIC = "strategic"
    PREFERRED = "preferred"
    APPROVED = "approved"
    BLACKLISTED = "blacklisted"


class SupplierSummary(BaseSchema, TimestampMixin):
    id: UUID
    code: str
    name: str
    tier: SupplierTier
    rating_score: float = Field(..., ge=0, le=100)
    is_online: bool


# --------------------------------------------------------------------------- #
# 采购
# --------------------------------------------------------------------------- #


class PurchaseOrderLineDTO(BaseSchema):
    product_id: UUID
    quantity: Quantity
    unit_price: Money
    received_quantity: Quantity
    line_total: Money


class PurchaseOrderDTO(BaseSchema, TimestampMixin):
    """采购订单,Lane 4 据此挂应付。"""

    id: UUID
    order_no: str
    supplier_id: UUID
    status: DocumentStatus
    lines: list[PurchaseOrderLineDTO]
    total_amount: Money
    expected_arrival: datetime | None = None


class PurchaseRequestFromBOM(BaseSchema):
    """Lane 1 → Lane 3: BOM 反算的采购需求 (POST /scm/purchase-from-bom)。"""

    bom_id: UUID
    target_quantity: Quantity
    needed_by: datetime
    requested_by: UUID


# --------------------------------------------------------------------------- #
# 仓储
# --------------------------------------------------------------------------- #


class InventoryDTO(BaseSchema):
    """库存快照,Lane 1/2 都会查。"""

    product_id: UUID
    warehouse_id: UUID
    location_code: str | None = None
    on_hand: Quantity
    available: Quantity
    reserved: Quantity
    in_transit: Quantity
    batch_no: str | None = None
    expiry_date: datetime | None = None


class StockMoveType(StrEnum):
    PURCHASE_RECEIPT = "purchase_receipt"
    SALES_ISSUE = "sales_issue"
    PRODUCTION_ISSUE = "production_issue"  # Lane 2 领料
    PRODUCTION_RECEIPT = "production_receipt"  # Lane 2 入库
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    SCRAP = "scrap"


class StockMoveDTO(BaseSchema, TimestampMixin):
    id: UUID
    move_no: str
    type: StockMoveType
    product_id: UUID
    quantity: Quantity
    from_location: str | None = None
    to_location: str | None = None
    reference_id: UUID | None = Field(None, description="关联单据 (工单/采购单/销售单) ID")
