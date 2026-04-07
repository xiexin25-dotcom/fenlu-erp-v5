"""PLM API request/response schemas.

内部 API 用,不是跨 lane 契约(那些在 shared/contracts 里)。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.shared.contracts.base import DocumentStatus, Money, Quantity
from packages.shared.contracts.product_lifecycle import ProductCategory


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=200)
    category: ProductCategory
    uom: str = Field(..., max_length=16)
    description: str | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    category: str
    uom: str
    current_version: str
    is_active: bool
    description: str | None = None


class ProductVersionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    change_summary: str | None = None


class ProductVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    version: str
    change_summary: str | None = None
    is_current: bool


# ── BOM ───────────────────────────────────────────────────────────────────── #


class BOMCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: UUID
    version: str = Field(..., max_length=32)
    description: str | None = None


class BOMItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    component_id: UUID
    quantity: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    uom: str = Field(..., max_length=16)
    scrap_rate: Decimal = Field(Decimal("0"), ge=0, le=1, max_digits=5, decimal_places=4)
    unit_cost: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=4)
    is_optional: bool = False
    remark: str | None = None


class BOMItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    component_id: UUID
    component_code: str = ""
    component_name: str = ""
    quantity: Decimal
    uom: str
    scrap_rate: Decimal
    unit_cost: Decimal | None = None
    is_optional: bool
    remark: str | None = None


class BOMOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    product_code: str = ""
    version: str
    status: str
    description: str | None = None
    items: list[BOMItemOut] = []
    total_cost: Money | None = None
    created_at: datetime
    updated_at: datetime


# ── CAD Attachments ───────────────────────────────────────────────────────── #


class CadAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    version: str
    filename: str
    object_key: str
    content_type: str
    file_size: int
    checksum: str


# ── Routing ───────────────────────────────────────────────────────────────── #


class RoutingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: UUID
    version: str = Field(..., max_length=32)
    description: str | None = None


class RoutingOperationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sequence: int = Field(..., ge=1)
    operation_code: str = Field(..., max_length=64)
    operation_name: str = Field(..., max_length=200)
    workstation_code: str | None = Field(None, max_length=64)
    standard_minutes: float = Field(..., ge=0)
    setup_minutes: float = Field(0.0, ge=0)


class RoutingOperationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence: int
    operation_code: str
    operation_name: str
    workstation_code: str | None = None
    standard_minutes: float
    setup_minutes: float


class RoutingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    version: str
    description: str | None = None
    operations: list[RoutingOperationOut] = []
    total_standard_minutes: float = 0.0
    created_at: datetime
    updated_at: datetime


# ── ECN ───────────────────────────────────────────────────────────────────── #


class ECNCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: UUID
    ecn_no: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    reason: str | None = None
    description: str | None = None


class ECNTransition(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    target_status: str


class ECNOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    ecn_no: str
    status: str
    title: str
    reason: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime


# ── Customer / CRM ────────────────────────────────────────────────────────── #


class CustomerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    kind: str = Field(..., pattern=r"^(b2b|b2c)$")
    rating: str | None = Field(None, max_length=8)
    is_online: bool = False
    address: str | None = None


class ContactCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., max_length=128)
    title: str | None = Field(None, max_length=64)
    phone: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=255)
    is_primary: bool = False


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    title: str | None = None
    phone: str | None = None
    email: str | None = None
    is_primary: bool


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    kind: str
    rating: str | None = None
    is_online: bool
    address: str | None = None
    contacts: list[ContactOut] = []


class ActivityOut(BaseModel):
    type: str
    id: str
    title: str
    status: str
    created_at: str


class Customer360Out(BaseModel):
    customer: CustomerOut
    counts: dict[str, int]
    recent_activities: list[ActivityOut]


# ── Lead / Opportunity / Funnel ───────────────────────────────────────────── #


class LeadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: UUID
    title: str = Field(..., max_length=255)
    source: str | None = Field(None, max_length=64)


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    title: str
    source: str | None = None
    status: str


class LeadTransition(BaseModel):
    target_status: str


class OpportunityCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: UUID
    title: str = Field(..., max_length=255)
    expected_amount: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=4)
    expected_close: datetime | None = None


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    title: str
    stage: str
    expected_amount: Decimal | None = None
    expected_close: datetime | None = None


class OpportunityTransition(BaseModel):
    target_stage: str


class FunnelOut(BaseModel):
    leads: dict[str, int]
    opportunities: dict[str, int]
