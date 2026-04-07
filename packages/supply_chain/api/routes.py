"""Lane 3 · 供应链 API 路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.db import get_session

from .schemas import (
    BOMPurchaseResponse,
    InventoryListParams,
    InventoryResponse,
    LocationCreate,
    LocationResponse,
    LocationTreeNode,
    LocationUpdate,
    MaterialIssueRequest,
    MaterialIssueResponse,
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
    StockMoveResponse,
    StocktakeConfirmResult,
    StocktakeCreate,
    StocktakeResponse,
    SupplierCreate,
    SupplierListParams,
    SupplierProductCreate,
    SupplierProductResponse,
    SupplierRatingCreate,
    SupplierRatingResponse,
    SupplierResponse,
    SupplierUpdate,
    TierChangeRequest,
    TierChangeResponse,
    WarehouseCreate,
    WarehouseDetailResponse,
    WarehouseListParams,
    WarehouseResponse,
    WarehouseUpdate,
)
from packages.shared.contracts.supply_chain import PurchaseRequestFromBOM
from packages.supply_chain.services.inventory_service import InventoryService
from packages.supply_chain.services.purchase_service import PurchaseService
from packages.supply_chain.services.stocktake_service import StocktakeService
from packages.supply_chain.services.supplier_service import SupplierService
from packages.supply_chain.services.warehouse_service import WarehouseService

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


# =========================================================================== #
# SupplierProduct (物料-供应商映射)
# =========================================================================== #


@router.post("/supplier-products", response_model=SupplierProductResponse, status_code=201)
async def create_supplier_product(
    body: SupplierProductCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> SupplierProductResponse:
    svc = PurchaseService(session)
    sp = await svc.create_supplier_product(tenant_id, body)
    return SupplierProductResponse.model_validate(sp)


# =========================================================================== #
# BOM-driven purchase (Lane 1 → Lane 3)
# =========================================================================== #


@router.post("/purchase-from-bom", response_model=BOMPurchaseResponse, status_code=201)
async def purchase_from_bom(
    body: PurchaseRequestFromBOM,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> BOMPurchaseResponse:
    """Lane 1 BOM 反算采购: explode BOM → 按供应商分组 → 创建 PR。"""
    svc = PurchaseService(session)
    try:
        prs, unmapped = await svc.purchase_from_bom(
            tenant_id=tenant_id,
            bom_id=body.bom_id,
            target_quantity=body.target_quantity.value,
            target_uom=body.target_quantity.uom.value,
            needed_by=body.needed_by,
            requested_by=body.requested_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BOMPurchaseResponse(
        bom_id=body.bom_id,
        target_quantity=body.target_quantity.value,
        purchase_requests=[PRResponse.model_validate(pr) for pr in prs],
        unmapped_products=unmapped,
    )


# =========================================================================== #
# Warehouse
# =========================================================================== #


@router.post("/warehouses", response_model=WarehouseResponse, status_code=201)
async def create_warehouse(
    body: WarehouseCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> WarehouseResponse:
    svc = WarehouseService(session)
    wh = await svc.create_warehouse(tenant_id, body)
    return WarehouseResponse.model_validate(wh)


@router.get("/warehouses", response_model=dict)
async def list_warehouses(
    tenant_id: UUID = Depends(_tenant_id),
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    params = WarehouseListParams(
        is_active=is_active, search=search, page=page, size=size,
    )
    svc = WarehouseService(session)
    items, total = await svc.list_warehouses(tenant_id, params)
    return {
        "items": [WarehouseResponse.model_validate(w) for w in items],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/warehouses/{wh_id}", response_model=WarehouseDetailResponse)
async def get_warehouse(
    wh_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> WarehouseDetailResponse:
    svc = WarehouseService(session)
    wh = await svc.get_warehouse(tenant_id, wh_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    resp = WarehouseDetailResponse.model_validate(wh)
    resp.locations = [LocationResponse.model_validate(l) for l in wh.locations]
    return resp


@router.patch("/warehouses/{wh_id}", response_model=WarehouseResponse)
async def update_warehouse(
    wh_id: UUID,
    body: WarehouseUpdate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> WarehouseResponse:
    svc = WarehouseService(session)
    wh = await svc.update_warehouse(tenant_id, wh_id, body)
    if wh is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseResponse.model_validate(wh)


@router.get("/warehouses/{wh_id}/location-tree", response_model=list[LocationTreeNode])
async def get_location_tree(
    wh_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> list[LocationTreeNode]:
    """返回仓库完整库位树 (zone → aisle → bin)。"""
    svc = WarehouseService(session)
    wh = await svc.get_warehouse(tenant_id, wh_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    tree = await svc.get_location_tree(tenant_id, wh_id)
    return [LocationTreeNode.model_validate(n) for n in tree]


# =========================================================================== #
# Location
# =========================================================================== #


@router.post("/locations", response_model=LocationResponse, status_code=201)
async def create_location(
    body: LocationCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> LocationResponse:
    svc = WarehouseService(session)
    try:
        loc = await svc.create_location(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return LocationResponse.model_validate(loc)


@router.get("/locations/{loc_id}", response_model=LocationResponse)
async def get_location(
    loc_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> LocationResponse:
    svc = WarehouseService(session)
    loc = await svc.get_location(tenant_id, loc_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationResponse.model_validate(loc)


@router.get("/locations", response_model=list[LocationResponse])
async def list_locations(
    warehouse_id: UUID = Query(...),
    level: str | None = None,
    parent_id: UUID | None = None,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> list[LocationResponse]:
    svc = WarehouseService(session)
    locs = await svc.list_locations(tenant_id, warehouse_id, level=level, parent_id=parent_id)
    return [LocationResponse.model_validate(l) for l in locs]


@router.patch("/locations/{loc_id}", response_model=LocationResponse)
async def update_location(
    loc_id: UUID,
    body: LocationUpdate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> LocationResponse:
    svc = WarehouseService(session)
    loc = await svc.update_location(tenant_id, loc_id, body)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationResponse.model_validate(loc)


# =========================================================================== #
# Inventory
# =========================================================================== #


@router.get("/inventory", response_model=dict)
async def list_inventory(
    tenant_id: UUID = Depends(_tenant_id),
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    batch_no: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    params = InventoryListParams(
        product_id=product_id, warehouse_id=warehouse_id,
        batch_no=batch_no, page=page, size=size,
    )
    svc = InventoryService(session)
    items, total = await svc.list_inventory(tenant_id, params)
    return {
        "items": [InventoryResponse.model_validate(inv) for inv in items],
        "total": total,
        "page": page,
        "size": size,
    }


# =========================================================================== #
# Issue (Lane 2 领料)
# =========================================================================== #


@router.post("/issue", response_model=MaterialIssueResponse, status_code=201)
async def issue_material(
    body: MaterialIssueRequest,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> MaterialIssueResponse:
    """Lane 2 领料端点: 扣减库存,创建 production_issue StockMove。"""
    svc = InventoryService(session)
    try:
        move, inv = await svc.issue_material(
            tenant_id=tenant_id,
            product_id=body.product_id,
            quantity=body.quantity,
            uom=body.uom,
            warehouse_id=body.warehouse_id,
            batch_no=body.batch_no,
            work_order_id=body.work_order_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MaterialIssueResponse(
        move=StockMoveResponse.model_validate(move),
        remaining_available=inv.available,
    )


# =========================================================================== #
# Stocktake (盘点)
# =========================================================================== #


@router.post("/stocktakes", response_model=StocktakeResponse, status_code=201)
async def create_stocktake(
    body: StocktakeCreate,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> StocktakeResponse:
    svc = StocktakeService(session)
    st = await svc.create_stocktake(tenant_id, body)
    return StocktakeResponse.model_validate(st)


@router.get("/stocktakes/{st_id}", response_model=StocktakeResponse)
async def get_stocktake(
    st_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> StocktakeResponse:
    svc = StocktakeService(session)
    st = await svc.get_stocktake(tenant_id, st_id)
    if st is None:
        raise HTTPException(status_code=404, detail="Stocktake not found")
    return StocktakeResponse.model_validate(st)


@router.get("/stocktakes", response_model=list[StocktakeResponse])
async def list_stocktakes(
    tenant_id: UUID = Depends(_tenant_id),
    warehouse_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[StocktakeResponse]:
    svc = StocktakeService(session)
    items = await svc.list_stocktakes(tenant_id, warehouse_id=warehouse_id)
    return [StocktakeResponse.model_validate(st) for st in items]


@router.post("/stocktakes/{st_id}/confirm", response_model=StocktakeConfirmResult)
async def confirm_stocktake(
    st_id: UUID,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> StocktakeConfirmResult:
    """确认盘点: 计算差异,自动创建 adjustment StockMove。"""
    svc = StocktakeService(session)
    try:
        st, moves = await svc.confirm_stocktake(tenant_id, st_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StocktakeConfirmResult(
        stocktake=StocktakeResponse.model_validate(st),
        adjustment_moves=[StockMoveResponse.model_validate(m) for m in moves],
    )


@router.post("/stocktakes/{st_id}/transition", response_model=StocktakeResponse)
async def transition_stocktake(
    st_id: UUID,
    body: StatusTransition,
    tenant_id: UUID = Depends(_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> StocktakeResponse:
    svc = StocktakeService(session)
    try:
        st = await svc.transition_stocktake(tenant_id, st_id, body.to_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StocktakeResponse.model_validate(st)
