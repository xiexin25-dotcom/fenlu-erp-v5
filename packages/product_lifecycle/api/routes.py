"""Lane 1 · PLM API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Page
from packages.shared.db import get_session

from .schemas import ProductCreate, ProductOut, ProductVersionCreate, ProductVersionOut

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
