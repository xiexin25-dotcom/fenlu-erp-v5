"""
SCM · 供应商 API 请求/响应 Schema
=================================
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.shared.contracts.supply_chain import SupplierTier


# --------------------------------------------------------------------------- #
# Supplier
# --------------------------------------------------------------------------- #


class SupplierCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=128)
    tier: SupplierTier = SupplierTier.APPROVED
    contact_name: str | None = Field(None, max_length=64)
    contact_phone: str | None = Field(None, max_length=32)
    address: str | None = Field(None, max_length=256)
    remark: str | None = None


class SupplierUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, min_length=1, max_length=128)
    contact_name: str | None = Field(None, max_length=64)
    contact_phone: str | None = Field(None, max_length=32)
    address: str | None = Field(None, max_length=256)
    remark: str | None = None
    is_online: bool | None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    tier: SupplierTier
    rating_score: float
    is_online: bool
    contact_name: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    remark: str | None = None
    tenant_id: UUID


# --------------------------------------------------------------------------- #
# Tier change (审批)
# --------------------------------------------------------------------------- #


class TierChangeRequest(BaseModel):
    to_tier: SupplierTier
    reason: str | None = None


class TierChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID
    from_tier: str
    to_tier: str
    reason: str | None = None
    approval_status: str
    approval_id: UUID | None = None


# --------------------------------------------------------------------------- #
# Supplier Rating
# --------------------------------------------------------------------------- #


class SupplierRatingCreate(BaseModel):
    period_start: date
    period_end: date
    quality_score: float = Field(..., ge=0, le=100)
    delivery_score: float = Field(..., ge=0, le=100)
    price_score: float = Field(..., ge=0, le=100)
    service_score: float = Field(..., ge=0, le=100)
    total_score: float = Field(..., ge=0, le=100)


class SupplierRatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID
    period_start: date
    period_end: date
    quality_score: float
    delivery_score: float
    price_score: float
    service_score: float
    total_score: float


# --------------------------------------------------------------------------- #
# Query params
# --------------------------------------------------------------------------- #


class SupplierListParams(BaseModel):
    tier: SupplierTier | None = None
    is_online: bool | None = None
    search: str | None = Field(None, description="模糊搜索 code/name")
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)


# =========================================================================== #
# 采购申请 (Purchase Request)
# =========================================================================== #


class PRLineCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    uom: str = "pcs"
    remark: str | None = None


class PRLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: Decimal
    uom: str
    remark: str | None = None


class PRCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    request_no: str = Field(..., min_length=1, max_length=32)
    needed_by: datetime | None = None
    department_id: UUID | None = None
    remark: str | None = None
    lines: list[PRLineCreate] = Field(..., min_length=1)


class PRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_no: str
    status: str
    requested_by: UUID | None = None
    department_id: UUID | None = None
    needed_by: datetime | None = None
    remark: str | None = None
    lines: list[PRLineResponse] = []
    tenant_id: UUID


# =========================================================================== #
# 询价单 (RFQ)
# =========================================================================== #


class RFQLineCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    uom: str = "pcs"


class RFQLineUpdate(BaseModel):
    quoted_unit_price: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=4)


class RFQLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: Decimal
    uom: str
    quoted_unit_price: Decimal | None = None
    currency: str = "CNY"


class RFQCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    rfq_no: str = Field(..., min_length=1, max_length=32)
    supplier_id: UUID
    request_id: UUID | None = None
    valid_until: datetime | None = None
    remark: str | None = None
    lines: list[RFQLineCreate] = Field(..., min_length=1)


class RFQResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rfq_no: str
    status: str
    supplier_id: UUID
    request_id: UUID | None = None
    valid_until: datetime | None = None
    remark: str | None = None
    lines: list[RFQLineResponse] = []
    tenant_id: UUID


# =========================================================================== #
# 采购订单 (Purchase Order)
# =========================================================================== #


class POLineCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    uom: str = "pcs"
    unit_price: Decimal = Field(..., ge=0, max_digits=18, decimal_places=4)
    currency: str = "CNY"


class POLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: Decimal
    uom: str
    unit_price: Decimal
    currency: str
    line_total: Decimal
    received_quantity: Decimal


class POCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_no: str = Field(..., min_length=1, max_length=32)
    supplier_id: UUID
    rfq_id: UUID | None = None
    expected_arrival: datetime | None = None
    currency: str = "CNY"
    payment_terms: str | None = None
    remark: str | None = None
    lines: list[POLineCreate] = Field(..., min_length=1)


class POResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_no: str
    status: str
    supplier_id: UUID
    rfq_id: UUID | None = None
    total_amount: Decimal
    currency: str
    expected_arrival: datetime | None = None
    payment_terms: str | None = None
    remark: str | None = None
    lines: list[POLineResponse] = []
    tenant_id: UUID


# =========================================================================== #
# 收货单 (Purchase Receipt)
# =========================================================================== #


class ReceiptLineCreate(BaseModel):
    product_id: UUID
    ordered_quantity: Decimal = Field(..., ge=0, max_digits=18, decimal_places=4)
    received_quantity: Decimal = Field(..., ge=0, max_digits=18, decimal_places=4)
    rejected_quantity: Decimal = Field(0, ge=0, max_digits=18, decimal_places=4)
    uom: str = "pcs"
    batch_no: str | None = None


class ReceiptLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    ordered_quantity: Decimal
    received_quantity: Decimal
    rejected_quantity: Decimal
    uom: str
    batch_no: str | None = None


class ReceiptCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    receipt_no: str = Field(..., min_length=1, max_length=32)
    order_id: UUID
    supplier_id: UUID
    warehouse_id: UUID | None = None
    received_at: datetime | None = None
    remark: str | None = None
    lines: list[ReceiptLineCreate] = Field(..., min_length=1)


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    receipt_no: str
    status: str
    order_id: UUID
    supplier_id: UUID
    warehouse_id: UUID | None = None
    received_at: datetime | None = None
    remark: str | None = None
    lines: list[ReceiptLineResponse] = []
    tenant_id: UUID


# =========================================================================== #
# 通用状态变更
# =========================================================================== #


class StatusTransition(BaseModel):
    to_status: str
