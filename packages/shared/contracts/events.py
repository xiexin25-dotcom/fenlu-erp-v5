"""
跨 Lane 异步事件总线 (Redis Streams)
====================================

同步调用走 REST,异步事件走 Redis Streams。
所有事件必须在此声明,禁止 lane 内私自定义。

Stream 命名约定: {lane}-events  (如 mfg-events / scm-events)
消费者组:        bi-consumer / audit-consumer / notif-consumer
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, Lane, Money, Quantity


class EventType(StrEnum):
    # Lane 1 · 产品生命周期
    PRODUCT_RELEASED = "product.released"
    BOM_VERSIONED = "bom.versioned"
    SALES_ORDER_CONFIRMED = "sales_order.confirmed"
    SERVICE_TICKET_CLOSED = "service_ticket.closed"

    # Lane 2 · 生产
    WORK_ORDER_RELEASED = "work_order.released"
    WORK_ORDER_COMPLETED = "work_order.completed"
    QC_FAILED = "qc.failed"
    EQUIPMENT_FAULT = "equipment.fault"
    OEE_CALCULATED = "oee.calculated"
    HAZARD_REPORTED = "hazard.reported"
    ENERGY_THRESHOLD_BREACHED = "energy.threshold_breached"

    # Lane 3 · 供应链
    PURCHASE_ORDER_APPROVED = "po.approved"
    GOODS_RECEIVED = "goods.received"
    INVENTORY_BELOW_SAFETY = "inventory.below_safety"

    # Lane 4 · 管理
    AP_OVERDUE = "ap.overdue"
    APPROVAL_REQUESTED = "approval.requested"


class BaseEvent(BaseSchema):
    """所有事件的基类。"""

    event_id: UUID
    event_type: EventType
    source_lane: Lane
    occurred_at: datetime
    tenant_id: UUID
    actor_id: UUID | None = None
    correlation_id: UUID | None = Field(None, description="跨 lane 链路追踪 ID,从源头一直传到 BI")


# --------------------------------------------------------------------------- #
# 具体事件 payload (示例,完整版每个 EventType 都要有)
# --------------------------------------------------------------------------- #


class WorkOrderCompletedEvent(BaseEvent):
    work_order_id: UUID
    product_id: UUID
    completed_quantity: Quantity
    scrap_quantity: Quantity
    actual_minutes: float


class QCFailedEvent(BaseEvent):
    inspection_id: UUID
    product_id: UUID
    work_order_id: UUID | None
    defect_count: int
    sample_size: int


class EquipmentFaultEvent(BaseEvent):
    equipment_id: UUID
    fault_code: str
    severity: str  # minor/major/critical


class EnergyThresholdBreachedEvent(BaseEvent):
    meter_id: UUID
    energy_type: str
    threshold: float
    actual: float


class PurchaseOrderApprovedEvent(BaseEvent):
    purchase_order_id: UUID
    supplier_id: UUID
    total_amount: Money


class SalesOrderConfirmedEvent(BaseEvent):
    sales_order_id: UUID
    customer_id: UUID
    total_amount: Money
