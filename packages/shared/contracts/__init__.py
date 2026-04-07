"""
分路链式 V5.0 · 跨 Lane 共享契约
================================

这是 4 条 worktree 之间唯一允许的耦合点。

import 规则:
    from packages.shared.contracts.base import BaseSchema, Money, Quantity
    from packages.shared.contracts.product_lifecycle import BOMDTO
    from packages.shared.contracts.production import WorkOrderDTO
    from packages.shared.contracts.events import EventType, WorkOrderCompletedEvent
"""

from .base import (
    ApiError,
    BaseSchema,
    Currency,
    DocumentStatus,
    Lane,
    Money,
    Page,
    PageRequest,
    Quantity,
    TenantMixin,
    TimestampMixin,
    UnitOfMeasure,
)

__all__ = [
    "ApiError",
    "BaseSchema",
    "Currency",
    "DocumentStatus",
    "Lane",
    "Money",
    "Page",
    "PageRequest",
    "Quantity",
    "TenantMixin",
    "TimestampMixin",
    "UnitOfMeasure",
]
