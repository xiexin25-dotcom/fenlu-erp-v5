"""
分路链式 V5.0 · 跨 lane 共享基础类型
====================================

所有 lane 的 schema 都必须 import 自此处的 BaseSchema 与公共枚举,
保证字段命名风格、时间戳格式、分页结构在 4 条线之间完全一致。

修改本文件 = 修改"宪法",必须发起 RFC 并 @ 全部 lane owner。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- #
# Base
# --------------------------------------------------------------------------- #


class BaseSchema(BaseModel):
    """所有跨 lane DTO 的根基类。"""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",  # 禁止未声明字段, 防止 lane 偷偷塞私货
    )


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime


class TenantMixin(BaseModel):
    tenant_id: UUID = Field(..., description="多租户隔离 ID")


# --------------------------------------------------------------------------- #
# 公共枚举
# --------------------------------------------------------------------------- #


class Lane(StrEnum):
    """4 条开发线标识,用于事件路由与审计。"""

    PRODUCT_LIFECYCLE = "plm"
    PRODUCTION = "mfg"
    SUPPLY_CHAIN = "scm"
    MANAGEMENT = "mgmt"


class Currency(StrEnum):
    CNY = "CNY"
    USD = "USD"


class UnitOfMeasure(StrEnum):
    PIECE = "pcs"
    KG = "kg"
    GRAM = "g"
    LITER = "L"
    METER = "m"
    HOUR = "h"
    KWH = "kWh"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    CLOSED = "closed"


# --------------------------------------------------------------------------- #
# 金额 / 数量包装
# --------------------------------------------------------------------------- #


class Money(BaseSchema):
    amount: Decimal = Field(..., max_digits=18, decimal_places=4)
    currency: Currency = Currency.CNY


class Quantity(BaseSchema):
    value: Decimal = Field(..., max_digits=18, decimal_places=4)
    uom: UnitOfMeasure


# --------------------------------------------------------------------------- #
# 分页 / 通用响应
# --------------------------------------------------------------------------- #

T = TypeVar("T")


class PageRequest(BaseSchema):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)
    order_by: str | None = None
    desc: bool = False


class Page(BaseSchema, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class ApiError(BaseSchema):
    code: str
    message: str
    details: dict[str, Any] | None = None
