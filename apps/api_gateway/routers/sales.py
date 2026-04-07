"""销售管理路由: 订单CRUD + 收款 + 发货。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.auth import CurrentUser
from packages.shared.db import get_session
from packages.shared.models.sales_order import (
    SalesDoc, SalesDocItem, OrderStatus, PaymentStatus, ShipmentStatus,
)

router = APIRouter(prefix="/sales", tags=["sales"])


# ── Schemas ────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: UUID
    product_name: str = ""
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    uom: str = "pcs"


class OrderCreate(BaseModel):
    order_no: str = Field(..., max_length=64)
    customer_id: UUID
    customer_name: str = ""
    order_date: date
    delivery_date: date | None = None
    salesperson: str | None = None
    remark: str | None = None
    items: list[OrderItemCreate] = []


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: UUID
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    shipped_qty: Decimal
    uom: str


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_no: str
    customer_id: UUID
    customer_name: str
    order_status: str
    payment_status: str
    shipment_status: str
    total_amount: Decimal
    paid_amount: Decimal
    balance: Decimal
    order_date: date
    delivery_date: date | None
    shipped_date: date | None
    salesperson: str | None
    remark: str | None
    created_at: datetime | None = None
    items: list[OrderItemOut] = []


class PaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    memo: str | None = None


class ShipmentRequest(BaseModel):
    items: list[dict] = []  # [{product_id, quantity}]
    memo: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("", response_model=list[OrderOut])
async def list_orders(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    status: str | None = Query(None),
    payment: str | None = Query(None),
    shipment: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[OrderOut]:
    stmt = select(SalesDoc).where(SalesDoc.tenant_id == user.tenant_id)
    if status:
        stmt = stmt.where(SalesDoc.order_status == status)
    if payment:
        stmt = stmt.where(SalesDoc.payment_status == payment)
    if shipment:
        stmt = stmt.where(SalesDoc.shipment_status == shipment)
    stmt = stmt.order_by(SalesDoc.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return [OrderOut.model_validate(o) for o in result.scalars().all()]


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    body: OrderCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> OrderOut:
    total = Decimal("0")
    items = []
    for it in body.items:
        amt = (it.quantity * it.unit_price).quantize(Decimal("0.01"))
        total += amt
        items.append(SalesDocItem(
            id=uuid4(), product_id=it.product_id, product_name=it.product_name,
            quantity=it.quantity, unit_price=it.unit_price, amount=amt, uom=it.uom,
        ))

    order = SalesDoc(
        id=uuid4(), tenant_id=user.tenant_id,
        order_no=body.order_no, customer_id=body.customer_id,
        customer_name=body.customer_name,
        order_date=body.order_date, delivery_date=body.delivery_date,
        salesperson=body.salesperson, remark=body.remark,
        total_amount=total, balance=total, created_by=user.id,
        items=items,
    )
    session.add(order)
    await session.commit()

    # Auto-create AR record
    try:
        from packages.management_decision.models.ap_ar import ARRecord
        ar = ARRecord(
            id=uuid4(), tenant_id=user.tenant_id,
            sales_order_id=order.id, customer_id=body.customer_id,
            total_amount=total, due_date=body.delivery_date or body.order_date,
            created_by=user.id,
        )
        session.add(ar)
        await session.commit()
    except Exception:
        pass  # AR creation failure shouldn't block order

    return OrderOut.model_validate(order)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> OrderOut:
    order = await session.get(SalesDoc, order_id)
    if not order or order.tenant_id != user.tenant_id:
        raise HTTPException(404, "订单不存在")
    return OrderOut.model_validate(order)


@router.post("/{order_id}/confirm", response_model=OrderOut)
async def confirm_order(
    order_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> OrderOut:
    order = await session.get(SalesDoc, order_id)
    if not order or order.tenant_id != user.tenant_id:
        raise HTTPException(404, "订单不存在")
    if order.order_status != OrderStatus.DRAFT:
        raise HTTPException(400, f"当前状态 {order.order_status} 不可确认")
    order.order_status = OrderStatus.CONFIRMED
    await session.commit()
    return OrderOut.model_validate(order)


@router.post("/{order_id}/payment", response_model=OrderOut)
async def record_payment(
    order_id: UUID,
    body: PaymentRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> OrderOut:
    order = await session.get(SalesDoc, order_id)
    if not order or order.tenant_id != user.tenant_id:
        raise HTTPException(404, "订单不存在")

    order.paid_amount = order.paid_amount + body.amount
    order.balance = order.total_amount - order.paid_amount

    if order.balance <= 0:
        order.payment_status = PaymentStatus.PAID
        order.balance = Decimal("0")
    else:
        order.payment_status = PaymentStatus.PARTIAL

    # Update order status
    if order.order_status == OrderStatus.CONFIRMED:
        order.order_status = OrderStatus.IN_PROGRESS

    await session.commit()
    return OrderOut.model_validate(order)


@router.post("/{order_id}/ship", response_model=OrderOut)
async def record_shipment(
    order_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> OrderOut:
    order = await session.get(SalesDoc, order_id)
    if not order or order.tenant_id != user.tenant_id:
        raise HTTPException(404, "订单不存在")

    order.shipment_status = ShipmentStatus.SHIPPED
    order.shipped_date = date.today()

    # Mark all items as shipped
    for item in order.items:
        item.shipped_qty = item.quantity

    # Check if completed
    if order.payment_status == PaymentStatus.PAID:
        order.order_status = OrderStatus.COMPLETED

    if order.order_status == OrderStatus.CONFIRMED:
        order.order_status = OrderStatus.IN_PROGRESS

    await session.commit()
    return OrderOut.model_validate(order)


# ── Dashboard Stats ────────────────────────────────────────────────

@router.get("/stats/summary")
async def sales_summary(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    base = select(SalesDoc).where(SalesDoc.tenant_id == user.tenant_id)

    total_orders = (await session.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    unpaid_unshipped = (await session.execute(
        select(func.count()).select_from(
            base.where(
                SalesDoc.payment_status == PaymentStatus.UNPAID,
                SalesDoc.shipment_status == ShipmentStatus.UNSHIPPED,
            ).subquery()
        )
    )).scalar() or 0

    paid_unshipped = (await session.execute(
        select(func.count()).select_from(
            base.where(
                SalesDoc.payment_status == PaymentStatus.PAID,
                SalesDoc.shipment_status == ShipmentStatus.UNSHIPPED,
            ).subquery()
        )
    )).scalar() or 0

    unpaid_shipped = (await session.execute(
        select(func.count()).select_from(
            base.where(
                SalesDoc.payment_status == PaymentStatus.UNPAID,
                SalesDoc.shipment_status == ShipmentStatus.SHIPPED,
            ).subquery()
        )
    )).scalar() or 0

    total_receivable = (await session.execute(
        select(func.coalesce(func.sum(SalesDoc.balance), 0)).where(
            SalesDoc.tenant_id == user.tenant_id, SalesDoc.balance > 0
        )
    )).scalar() or 0

    return {
        "total_orders": total_orders,
        "unpaid_unshipped": unpaid_unshipped,
        "paid_unshipped": paid_unshipped,
        "unpaid_shipped": unpaid_shipped,
        "total_receivable": float(total_receivable),
    }
