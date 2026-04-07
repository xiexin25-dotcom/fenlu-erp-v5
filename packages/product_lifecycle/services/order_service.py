"""Quote → Contract → Order service.

报价单状态机: draft → submitted → approved → contracted → ordered
ordered 时自动创建 SalesOrder + SalesOrderLines (从 QuoteItems 复制)。
order confirm 时 emit SalesOrderConfirmedEvent。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.product_lifecycle.models import (
    QUOTE_TRANSITIONS,
    Quote,
    QuoteItem,
    QuoteStatus,
    SalesOrder,
    SalesOrderLine,
    SalesOrderStatus,
)


class InvalidQuoteTransitionError(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"invalid quote transition: {current} → {target}")


# --------------------------------------------------------------------------- #
# Quote CRUD
# --------------------------------------------------------------------------- #


async def create_quote(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    customer_id: UUID,
    quote_no: str,
    currency: str = "CNY",
    valid_until: datetime | None = None,
    remark: str | None = None,
) -> Quote:
    quote = Quote(
        tenant_id=tenant_id,
        customer_id=customer_id,
        quote_no=quote_no,
        currency=currency,
        valid_until=valid_until,
        remark=remark,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(quote)
    await session.flush()
    return quote


async def get_quote(
    session: AsyncSession, *, tenant_id: UUID, quote_id: UUID,
) -> Quote | None:
    result = await session.execute(
        select(Quote)
        .options(selectinload(Quote.items))
        .where(Quote.id == quote_id, Quote.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def add_quote_item(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    quote_id: UUID,
    product_id: UUID,
    quantity: Decimal,
    uom: str,
    unit_price: Decimal,
    currency: str = "CNY",
) -> QuoteItem:
    line_total = quantity * unit_price
    item = QuoteItem(
        tenant_id=tenant_id,
        quote_id=quote_id,
        product_id=product_id,
        quantity=quantity,
        uom=uom,
        unit_price=unit_price,
        line_total=line_total,
        currency=currency,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(item)
    await session.flush()

    # 更新 quote total
    quote = await get_quote(session, tenant_id=tenant_id, quote_id=quote_id)
    if quote is not None:
        quote.total_amount = sum(i.line_total for i in quote.items)
        await session.flush()

    return item


# --------------------------------------------------------------------------- #
# Quote transition + order creation
# --------------------------------------------------------------------------- #


async def transition_quote(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    quote_id: UUID,
    target_status: str,
    promised_delivery: datetime | None = None,
    event_publisher: Any = None,
) -> Quote:
    """推进报价单状态。到 ordered 时自动创建 SalesOrder 并 confirm。"""
    quote = await get_quote(session, tenant_id=tenant_id, quote_id=quote_id)
    if quote is None:
        raise ValueError("quote not found")

    current = QuoteStatus(quote.status)
    target = QuoteStatus(target_status)
    if target not in QUOTE_TRANSITIONS.get(current, []):
        raise InvalidQuoteTransitionError(quote.status, target_status)

    quote.status = target.value
    quote.updated_by = user_id
    await session.flush()

    # ordered → create SalesOrder + confirm + emit event
    if target == QuoteStatus.ORDERED:
        order = await _create_order_from_quote(
            session, quote=quote, user_id=user_id,
            promised_delivery=promised_delivery,
        )
        await _confirm_order(
            session, order=order, user_id=user_id,
            event_publisher=event_publisher,
        )

    # re-fetch
    quote = await get_quote(session, tenant_id=tenant_id, quote_id=quote_id)
    assert quote is not None
    return quote


async def _create_order_from_quote(
    session: AsyncSession,
    *,
    quote: Quote,
    user_id: UUID,
    promised_delivery: datetime | None = None,
) -> SalesOrder:
    """从 Quote 创建 SalesOrder + Lines。"""
    order_no = quote.quote_no.replace("QT-", "SO-", 1)
    if order_no == quote.quote_no:
        order_no = f"SO-{quote.quote_no}"

    order = SalesOrder(
        tenant_id=quote.tenant_id,
        customer_id=quote.customer_id,
        quote_id=quote.id,
        order_no=order_no,
        status=SalesOrderStatus.DRAFT,
        total_amount=quote.total_amount,
        currency=quote.currency,
        promised_delivery=promised_delivery,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(order)
    await session.flush()

    for qi in quote.items:
        line = SalesOrderLine(
            tenant_id=quote.tenant_id,
            order_id=order.id,
            product_id=qi.product_id,
            quantity=qi.quantity,
            uom=qi.uom,
            unit_price=qi.unit_price,
            line_total=qi.line_total,
            currency=qi.currency,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(line)

    await session.flush()
    return order


async def _confirm_order(
    session: AsyncSession,
    *,
    order: SalesOrder,
    user_id: UUID,
    event_publisher: Any = None,
) -> None:
    """确认订单并发布 SalesOrderConfirmedEvent。"""
    order.status = SalesOrderStatus.CONFIRMED
    order.updated_by = user_id
    await session.flush()

    event_data = {
        "event_id": str(uuid4()),
        "event_type": "sales_order.confirmed",
        "source_lane": "plm",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": str(order.tenant_id),
        "actor_id": str(user_id),
        "sales_order_id": str(order.id),
        "customer_id": str(order.customer_id),
        "total_amount": str(order.total_amount),
        "currency": order.currency,
    }

    if event_publisher is not None:
        await event_publisher(event_data)
    else:
        from packages.product_lifecycle.services.event_publisher import publish_event

        await publish_event(event_data)


# --------------------------------------------------------------------------- #
# SalesOrder read
# --------------------------------------------------------------------------- #


async def get_sales_order(
    session: AsyncSession, *, tenant_id: UUID, order_id: UUID,
) -> SalesOrder | None:
    result = await session.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.lines))
        .where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()
