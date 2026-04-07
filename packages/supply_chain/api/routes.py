"""Lane 3 · 供应链 API 路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.db import get_session

from .schemas import (
    SupplierCreate,
    SupplierListParams,
    SupplierRatingCreate,
    SupplierRatingResponse,
    SupplierResponse,
    SupplierUpdate,
    TierChangeRequest,
    TierChangeResponse,
)
from packages.supply_chain.services.supplier_service import SupplierService

router = APIRouter(prefix="/scm", tags=["supply-chain"])

# TODO: 从 auth 中间件获取 tenant_id, 目前用 header 传入
_TENANT_HEADER = "X-Tenant-Id"


def _tenant_id(tenant_id: UUID = Query(..., alias="tenant_id")) -> UUID:
    return tenant_id


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "lane": "supply_chain"}


# --------------------------------------------------------------------------- #
# Supplier CRUD
# --------------------------------------------------------------------------- #


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    body: SupplierCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> SupplierResponse:
    svc = SupplierService(session)
    supplier = await svc.create_supplier(tenant_id, body)
    return SupplierResponse.model_validate(supplier)


@router.get("/suppliers", response_model=dict)
async def list_suppliers(
    tenant_id: UUID = Depends(_tenant_id),
    tier: str | None = None,
    is_online: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from packages.shared.contracts.supply_chain import SupplierTier

    params = SupplierListParams(
        tier=SupplierTier(tier) if tier else None,
        is_online=is_online,
        search=search,
        page=page,
        size=size,
    )
    svc = SupplierService(session)
    items, total = await svc.list_suppliers(tenant_id, params)
    return {
        "items": [SupplierResponse.model_validate(s) for s in items],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> SupplierResponse:
    svc = SupplierService(session)
    supplier = await svc.get_supplier(tenant_id, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return SupplierResponse.model_validate(supplier)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: UUID,
    body: SupplierUpdate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> SupplierResponse:
    svc = SupplierService(session)
    supplier = await svc.update_supplier(tenant_id, supplier_id, body)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return SupplierResponse.model_validate(supplier)


# --------------------------------------------------------------------------- #
# Tier transition (审批流)
# --------------------------------------------------------------------------- #


@router.post(
    "/suppliers/{supplier_id}/tier-change",
    response_model=TierChangeResponse,
    status_code=201,
)
async def request_tier_change(
    supplier_id: UUID,
    body: TierChangeRequest,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> TierChangeResponse:
    svc = SupplierService(session)
    try:
        change = await svc.request_tier_change(
            tenant_id, supplier_id, body.to_tier.value, body.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TierChangeResponse.model_validate(change)


@router.post("/suppliers/tier-change/{change_id}/callback")
async def tier_change_callback(
    change_id: UUID,
    approved: bool = Query(...),
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> TierChangeResponse:
    """Lane 4 审批完成后的回调端点。"""
    svc = SupplierService(session)
    change = await svc.complete_tier_change(tenant_id, change_id, approved)
    if change is None:
        raise HTTPException(status_code=404, detail="Tier change not found or already processed")
    return TierChangeResponse.model_validate(change)


# --------------------------------------------------------------------------- #
# Supplier Rating
# --------------------------------------------------------------------------- #


@router.post(
    "/suppliers/{supplier_id}/ratings",
    response_model=SupplierRatingResponse,
    status_code=201,
)
async def add_rating(
    supplier_id: UUID,
    body: SupplierRatingCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> SupplierRatingResponse:
    svc = SupplierService(session)
    try:
        rating = await svc.add_rating(tenant_id, supplier_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SupplierRatingResponse.model_validate(rating)


@router.get(
    "/suppliers/{supplier_id}/ratings",
    response_model=list[SupplierRatingResponse],
)
async def list_ratings(
    supplier_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> list[SupplierRatingResponse]:
    svc = SupplierService(session)
    ratings = await svc.list_ratings(tenant_id, supplier_id)
    return [SupplierRatingResponse.model_validate(r) for r in ratings]
