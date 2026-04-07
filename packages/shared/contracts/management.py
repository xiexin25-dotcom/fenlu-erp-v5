"""
Lane 4 · 管理决策 对外契约
==========================

本文件定义 Lane 4 (财务/HR/协同/BI) 暴露给其他 lane 的 DTO,
以及 BI 看板订阅的 KPI 定义。

工信部场景: 财务管理* / 人力资源 / 协同办公 / 决策支持
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, Money, TimestampMixin

# --------------------------------------------------------------------------- #
# 财务
# --------------------------------------------------------------------------- #


class APStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    WRITTEN_OFF = "written_off"


class APRecordDTO(BaseSchema, TimestampMixin):
    """应付账款,数据来源 Lane 3 的采购订单。"""

    id: UUID
    purchase_order_id: UUID
    supplier_id: UUID
    total_amount: Money
    paid_amount: Money
    balance: Money
    due_date: date
    status: APStatus


class ARRecordDTO(BaseSchema, TimestampMixin):
    """应收账款,数据来源 Lane 1 的销售订单。"""

    id: UUID
    sales_order_id: UUID
    customer_id: UUID
    total_amount: Money
    received_amount: Money
    balance: Money
    due_date: date
    status: APStatus


# --------------------------------------------------------------------------- #
# 人力资源
# --------------------------------------------------------------------------- #


class EmployeeSummary(BaseSchema, TimestampMixin):
    id: UUID
    employee_no: str
    name: str
    department_id: UUID
    position: str
    is_active: bool


# --------------------------------------------------------------------------- #
# 协同办公 · 审批流
# --------------------------------------------------------------------------- #


class ApprovalAction(StrEnum):
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    DELEGATE = "delegate"
    WITHDRAW = "withdraw"


class ApprovalStepDTO(BaseSchema):
    step_no: int
    approver_id: UUID
    action: ApprovalAction | None = None
    comment: str | None = None
    acted_at: str | None = None


class ApprovalRequest(BaseSchema):
    """任意 lane 都可以发起的审批请求。"""

    business_type: str = Field(..., description="如 purchase_order / leave / hazard_close")
    business_id: UUID
    initiator_id: UUID
    payload: dict[str, Any]


# --------------------------------------------------------------------------- #
# 决策支持 · KPI 定义
# --------------------------------------------------------------------------- #


class KPICategory(StrEnum):
    FINANCIAL = "financial"
    OPERATIONS = "operations"
    QUALITY = "quality"
    HR = "hr"
    SAFETY = "safety"
    ENERGY = "energy"


class KPIDefinitionDTO(BaseSchema):
    """KPI 元数据,前端 BI 看板按此渲染。"""

    code: str = Field(..., max_length=64)
    name: str
    category: KPICategory
    unit: str
    source_lane: str  # plm / mfg / scm / mgmt
    aggregation: str  # sum / avg / max / latest
    description: str | None = None


class KPIDataPointDTO(BaseSchema):
    kpi_code: str
    period: date
    value: float
    target: float | None = None
