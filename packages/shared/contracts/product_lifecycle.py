"""
Lane 1 · 产品生命周期 对外契约
==============================

本文件定义 Lane 1 (PLM/CRM/售后) 暴露给其他 lane 的只读 DTO。
**其他 lane 不得直接 import 本 lane 的 SQLAlchemy 模型,只能依赖此处的 schema。**

工信部场景覆盖: 产品设计* / 工艺设计 / 营销管理* / 售后服务
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, DocumentStatus, Money, Quantity, TimestampMixin

# --------------------------------------------------------------------------- #
# PLM · 产品 / BOM / 工艺
# --------------------------------------------------------------------------- #


class ProductCategory(StrEnum):
    SELF_MADE = "self_made"  # 自产
    AGENT = "agent"  # 代理
    RAW_MATERIAL = "raw_material"  # 原辅料
    PACKAGING = "packaging"  # 周转物


class ProductSummary(BaseSchema, TimestampMixin):
    """供 Lane 2/3 查询的产品轻量视图。"""

    id: UUID
    code: str = Field(..., max_length=64)
    name: str
    category: ProductCategory
    uom: str
    current_version: str
    is_active: bool


class BOMItemDTO(BaseSchema):
    component_id: UUID
    component_code: str
    component_name: str
    quantity: Quantity
    scrap_rate: float = Field(0.0, ge=0, le=1)
    is_optional: bool = False


class BOMDTO(BaseSchema, TimestampMixin):
    """完整 BOM 树,Lane 2 排程 / Lane 3 采购 反算的输入。"""

    id: UUID
    product_id: UUID
    product_code: str
    version: str
    status: DocumentStatus
    items: list[BOMItemDTO]
    total_cost: Money | None = None


class RoutingOperationDTO(BaseSchema):
    sequence: int
    operation_code: str
    operation_name: str
    workstation_code: str | None = None
    standard_minutes: float = Field(..., ge=0)
    setup_minutes: float = Field(0.0, ge=0)


class RoutingDTO(BaseSchema, TimestampMixin):
    """工艺路线,供 Lane 2 APS 排程使用。"""

    id: UUID
    product_id: UUID
    version: str
    operations: list[RoutingOperationDTO]
    total_standard_minutes: float


# --------------------------------------------------------------------------- #
# CRM · 客户 / 商机 / 订单
# --------------------------------------------------------------------------- #


class CustomerKind(StrEnum):
    B2B = "b2b"
    B2C = "b2c"


class CustomerSummary(BaseSchema, TimestampMixin):
    id: UUID
    code: str
    name: str
    kind: CustomerKind
    rating: str | None = Field(None, description="A/B/C/D 信用评级")
    is_online: bool


class SalesOrderLineDTO(BaseSchema):
    product_id: UUID
    quantity: Quantity
    unit_price: Money
    line_total: Money


class SalesOrderDTO(BaseSchema, TimestampMixin):
    """销售订单,推送给 Lane 2 触发生产、Lane 4 计入应收。"""

    id: UUID
    order_no: str
    customer_id: UUID
    status: DocumentStatus
    lines: list[SalesOrderLineDTO]
    total_amount: Money
    promised_delivery: datetime | None = None


# --------------------------------------------------------------------------- #
# 售后
# --------------------------------------------------------------------------- #


class ServiceTicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ServiceTicketSummary(BaseSchema, TimestampMixin):
    id: UUID
    ticket_no: str
    customer_id: UUID
    product_id: UUID | None = None
    status: ServiceTicketStatus
    sla_due_at: datetime | None = None
    nps_score: int | None = Field(None, ge=0, le=10)
