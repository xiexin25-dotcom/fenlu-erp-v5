"""PLM API request/response schemas.

内部 API 用,不是跨 lane 契约(那些在 shared/contracts 里)。
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
