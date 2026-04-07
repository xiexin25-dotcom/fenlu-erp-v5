"""Lane 1 · PLM API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Page
from packages.shared.db import get_session

from .schemas import (
    BOMCreate,
    BOMItemCreate,
    BOMItemOut,
    BOMOut,
    CadAttachmentOut,
    ProductCreate,
    ProductOut,
    ProductVersionCreate,
    ProductVersionOut,
)

router = APIRouter(prefix="/plm", tags=["product-lifecycle"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "lane": "product_lifecycle"}


# ── Products ──────────────────────────────────────────────────────────────── #


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ProductOut:
    from packages.product_lifecycle.services.product_service import (
        create_product as _create,
    )

    product = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        code=body.code,
        name=body.name,
        category=body.category.value,
        uom=body.uom,
        description=body.description,
    )
    return ProductOut.model_validate(product)


@router.get("/products", response_model=Page[ProductOut])
async def list_products(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> Page[ProductOut]:
    from packages.product_lifecycle.services.product_service import (
        list_products as _list,
    )

    items, total = await _list(session, tenant_id=user.tenant_id, page=page, size=size)
    return Page[ProductOut](
        items=[ProductOut.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ProductOut:
    from packages.product_lifecycle.services.product_service import (
        get_product as _get,
    )

    product = await _get(session, tenant_id=user.tenant_id, product_id=product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    return ProductOut.model_validate(product)


# ── Versions ──────────────────────────────────────────────────────────────── #


@router.post(
    "/products/{product_id}/versions",
    response_model=ProductVersionOut,
    status_code=201,
)
async def create_version(
    product_id: UUID,
    body: ProductVersionCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ProductVersionOut:
    from packages.product_lifecycle.services.product_service import (
        create_version as _create_ver,
    )

    try:
        ver = await _create_ver(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            product_id=product_id,
            change_summary=body.change_summary,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return ProductVersionOut.model_validate(ver)


# ── BOM ───────────────────────────────────────────────────────────────────── #


def _bom_to_out(bom: object, total_cost_amount: object = None) -> BOMOut:
    """Convert BOM ORM → BOMOut, enriching component code/name from relationship."""
    from packages.product_lifecycle.models import BOM as BOMModel

    assert isinstance(bom, BOMModel)
    items_out = []
    for item in bom.items:
        items_out.append(
            BOMItemOut(
                id=item.id,
                component_id=item.component_id,
                component_code=item.component.code if item.component else "",
                component_name=item.component.name if item.component else "",
                quantity=item.quantity,
                uom=item.uom,
                scrap_rate=item.scrap_rate,
                unit_cost=item.unit_cost,
                is_optional=item.is_optional,
                remark=item.remark,
            )
        )
    from decimal import Decimal

    from packages.shared.contracts.base import Money

    tc = None
    if total_cost_amount is not None and isinstance(total_cost_amount, Decimal):
        tc = Money(amount=total_cost_amount)

    return BOMOut(
        id=bom.id,
        product_id=bom.product_id,
        product_code=bom.product.code if bom.product else "",
        version=bom.version,
        status=bom.status,
        description=bom.description,
        items=items_out,
        total_cost=tc,
        created_at=bom.created_at,
        updated_at=bom.updated_at,
    )


@router.post("/bom", response_model=BOMOut, status_code=201)
async def create_bom(
    body: BOMCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BOMOut:
    from packages.product_lifecycle.services.bom_service import create_bom as _create

    bom = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        product_id=body.product_id,
        version=body.version,
        description=body.description,
    )
    # re-fetch with relationships
    from packages.product_lifecycle.services.bom_service import get_bom

    bom = await get_bom(session, tenant_id=user.tenant_id, bom_id=bom.id)
    assert bom is not None
    return _bom_to_out(bom)


@router.get("/bom/{bom_id}", response_model=BOMOut)
async def get_bom_detail(
    bom_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BOMOut:
    from packages.product_lifecycle.services.bom_service import get_bom, rollup_cost

    bom = await get_bom(session, tenant_id=user.tenant_id, bom_id=bom_id)
    if bom is None:
        raise HTTPException(404, "BOM not found")
    cost = await rollup_cost(session, bom)
    return _bom_to_out(bom, cost)


@router.post("/bom/{bom_id}/items", response_model=BOMItemOut, status_code=201)
async def add_bom_item(
    bom_id: UUID,
    body: BOMItemCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BOMItemOut:
    from packages.product_lifecycle.services.bom_service import (
        CycleDetectedError,
        add_bom_item as _add,
    )

    try:
        item = await _add(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            bom_id=bom_id,
            component_id=body.component_id,
            quantity=body.quantity,
            uom=body.uom,
            scrap_rate=body.scrap_rate,
            unit_cost=body.unit_cost,
            is_optional=body.is_optional,
            remark=body.remark,
        )
    except CycleDetectedError as e:
        raise HTTPException(422, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e

    # re-fetch to get component relationship
    from packages.product_lifecycle.services.bom_service import get_bom

    bom = await get_bom(session, tenant_id=user.tenant_id, bom_id=bom_id)
    assert bom is not None
    for it in bom.items:
        if it.id == item.id:
            return BOMItemOut(
                id=it.id,
                component_id=it.component_id,
                component_code=it.component.code if it.component else "",
                component_name=it.component.name if it.component else "",
                quantity=it.quantity,
                uom=it.uom,
                scrap_rate=it.scrap_rate,
                unit_cost=it.unit_cost,
                is_optional=it.is_optional,
                remark=it.remark,
            )
    # fallback (shouldn't happen)
    return BOMItemOut.model_validate(item)


# ── CAD Attachments ───────────────────────────────────────────────────────── #


@router.post(
    "/products/{product_id}/cad",
    response_model=CadAttachmentOut,
    status_code=201,
)
async def upload_cad(
    product_id: UUID,
    file: UploadFile,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> CadAttachmentOut:
    from packages.product_lifecycle.services.cad_service import upload_cad as _upload

    if not file.filename:
        raise HTTPException(400, "filename is required")

    file_data = await file.read()
    if len(file_data) == 0:
        raise HTTPException(400, "empty file")

    try:
        attachment = await _upload(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            product_id=product_id,
            filename=file.filename,
            file_data=file_data,
            content_type=file.content_type or "application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return CadAttachmentOut.model_validate(attachment)


@router.get(
    "/products/{product_id}/cad",
    response_model=list[CadAttachmentOut],
)
async def list_cad_attachments(
    product_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[CadAttachmentOut]:
    from packages.product_lifecycle.services.cad_service import (
        list_cad_attachments as _list,
    )

    items = await _list(session, tenant_id=user.tenant_id, product_id=product_id)
    return [CadAttachmentOut.model_validate(a) for a in items]
