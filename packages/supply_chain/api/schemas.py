"""
SCM · 供应商 API 请求/响应 Schema
=================================
"""

from __future__ import annotations

from datetime import date
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
