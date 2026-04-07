"""Lane 3 · 供应链 API 路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.db import get_session

from .schemas import (
    POCreate,
    POResponse,
    PRCreate,
    PRResponse,
    ReceiptCreate,
    ReceiptResponse,
    RFQCreate,
    RFQLineUpdate,
    RFQResponse,
    StatusTransition,
    SupplierCreate,
    SupplierListParams,
    SupplierRatingCreate,
    SupplierRatingResponse,
    SupplierResponse,
    SupplierUpdate,
    TierChangeRequest,
    TierChangeResponse,
)
from packages.supply_chain.services.purchase_service import PurchaseService
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


# =========================================================================== #
# Purchase Request
# =========================================================================== #


@router.post("/purchase-requests", response_model=PRResponse, status_code=201)
async def create_pr(
    body: PRCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> PRResponse:
    svc = PurchaseService(session)
    pr = await svc.create_pr(tenant_id, body)
    return PRResponse.model_validate(pr)


@router.get("/purchase-requests/{pr_id}", response_model=PRResponse)
async def get_pr(
    pr_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> PRResponse:
    svc = PurchaseService(session)
    pr = await svc.get_pr(tenant_id, pr_id)
    if pr is None:
        raise HTTPException(status_code=404, detail="PurchaseRequest not found")
    return PRResponse.model_validate(pr)


@router.post("/purchase-requests/{pr_id}/transition", response_model=PRResponse)
async def transition_pr(
    pr_id: UUID,
    body: StatusTransition,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> PRResponse:
    svc = PurchaseService(session)
    try:
        pr = await svc.transition_pr(tenant_id, pr_id, body.to_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PRResponse.model_validate(pr)


# =========================================================================== #
# RFQ
# =========================================================================== #


@router.post("/rfqs", response_model=RFQResponse, status_code=201)
async def create_rfq(
    body: RFQCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> RFQResponse:
    svc = PurchaseService(session)
    rfq = await svc.create_rfq(tenant_id, body)
    return RFQResponse.model_validate(rfq)


@router.get("/rfqs/{rfq_id}", response_model=RFQResponse)
async def get_rfq(
    rfq_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> RFQResponse:
    svc = PurchaseService(session)
    rfq = await svc.get_rfq(tenant_id, rfq_id)
    if rfq is None:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return RFQResponse.model_validate(rfq)


@router.post("/rfqs/{rfq_id}/transition", response_model=RFQResponse)
async def transition_rfq(
    rfq_id: UUID,
    body: StatusTransition,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> RFQResponse:
    svc = PurchaseService(session)
    try:
        rfq = await svc.transition_rfq(tenant_id, rfq_id, body.to_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RFQResponse.model_validate(rfq)


@router.patch("/rfqs/{rfq_id}/lines/{line_id}", response_model=RFQResponse)
async def update_rfq_line(
    rfq_id: UUID,
    line_id: UUID,
    body: RFQLineUpdate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> RFQResponse:
    svc = PurchaseService(session)
    try:
        await svc.update_rfq_line_price(tenant_id, rfq_id, line_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    rfq = await svc.get_rfq(tenant_id, rfq_id)
    return RFQResponse.model_validate(rfq)


# =========================================================================== #
# Purchase Order
# =========================================================================== #


@router.post("/purchase-orders", response_model=POResponse, status_code=201)
async def create_po(
    body: POCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> POResponse:
    svc = PurchaseService(session)
    po = await svc.create_po(tenant_id, body)
    return POResponse.model_validate(po)


@router.get("/purchase-orders/{po_id}", response_model=POResponse)
async def get_po(
    po_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> POResponse:
    svc = PurchaseService(session)
    po = await svc.get_po(tenant_id, po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="PurchaseOrder not found")
    return POResponse.model_validate(po)


@router.post("/purchase-orders/{po_id}/transition", response_model=POResponse)
async def transition_po(
    po_id: UUID,
    body: StatusTransition,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> POResponse:
    svc = PurchaseService(session)
    try:
        po = await svc.transition_po(tenant_id, po_id, body.to_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return POResponse.model_validate(po)


# =========================================================================== #
# Purchase Receipt
# =========================================================================== #


@router.post("/purchase-receipts", response_model=ReceiptResponse, status_code=201)
async def create_receipt(
    body: ReceiptCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ReceiptResponse:
    svc = PurchaseService(session)
    try:
        receipt = await svc.create_receipt(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ReceiptResponse.model_validate(receipt)


@router.get("/purchase-receipts/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ReceiptResponse:
    svc = PurchaseService(session)
    receipt = await svc.get_receipt(tenant_id, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="PurchaseReceipt not found")
    return ReceiptResponse.model_validate(receipt)


@router.post("/purchase-receipts/{receipt_id}/transition", response_model=ReceiptResponse)
async def transition_receipt(
    receipt_id: UUID,
    body: StatusTransition,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ReceiptResponse:
    svc = PurchaseService(session)
    try:
        receipt = await svc.transition_receipt(tenant_id, receipt_id, body.to_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ReceiptResponse.model_validate(receipt)
