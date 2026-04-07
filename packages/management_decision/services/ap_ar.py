"""
AP / AR service · 应付应收 CRUD
================================
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.ap_ar import APRecord, APStatus, ARRecord


# --------------------------------------------------------------------------- #
# AP helpers
# --------------------------------------------------------------------------- #


def _derive_ap_status(total: Decimal, paid: Decimal) -> str:
    if paid >= total:
        return APStatus.PAID
    if paid > 0:
        return APStatus.PARTIAL
    return APStatus.UNPAID


# --------------------------------------------------------------------------- #
# AP
# --------------------------------------------------------------------------- #


async def create_ap_record(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    purchase_order_id: UUID,
    supplier_id: UUID,
    total_amount: Decimal,
    paid_amount: Decimal = Decimal("0"),
    currency: str = "CNY",
    due_date: "date",
    memo: str | None = None,
    created_by: UUID | None = None,
) -> APRecord:
    from datetime import date as _date  # noqa: F811

    record = APRecord(
        id=uuid4(),
        tenant_id=tenant_id,
        purchase_order_id=purchase_order_id,
        supplier_id=supplier_id,
        total_amount=total_amount,
        paid_amount=paid_amount,
        currency=currency,
        due_date=due_date,
        status=_derive_ap_status(total_amount, paid_amount),
        memo=memo,
        created_by=created_by,
    )
    session.add(record)
    await session.flush()
    return record


async def get_ap_record(
    session: AsyncSession, *, tenant_id: UUID, record_id: UUID
) -> APRecord | None:
    stmt = select(APRecord).where(APRecord.id == record_id, APRecord.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_ap_records(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    status: str | None = None,
) -> list[APRecord]:
    stmt = (
        select(APRecord)
        .where(APRecord.tenant_id == tenant_id)
        .order_by(APRecord.due_date)
    )
    if status:
        stmt = stmt.where(APRecord.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_ap_record(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    record_id: UUID,
    paid_amount: Decimal | None = None,
    status: str | None = None,
    memo: str | None = None,
    updated_by: UUID | None = None,
) -> APRecord | None:
    record = await get_ap_record(session, tenant_id=tenant_id, record_id=record_id)
    if record is None:
        return None
    if paid_amount is not None:
        record.paid_amount = paid_amount
        record.status = _derive_ap_status(record.total_amount, paid_amount)
    if status is not None:
        record.status = status
    if memo is not None:
        record.memo = memo
    if updated_by is not None:
        record.updated_by = updated_by
    await session.flush()
    return record


# --------------------------------------------------------------------------- #
# AR helpers
# --------------------------------------------------------------------------- #


def _derive_ar_status(total: Decimal, received: Decimal) -> str:
    if received >= total:
        return APStatus.PAID
    if received > 0:
        return APStatus.PARTIAL
    return APStatus.UNPAID


# --------------------------------------------------------------------------- #
# AR
# --------------------------------------------------------------------------- #


async def create_ar_record(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    sales_order_id: UUID,
    customer_id: UUID,
    total_amount: Decimal,
    received_amount: Decimal = Decimal("0"),
    currency: str = "CNY",
    due_date: "date",
    memo: str | None = None,
    created_by: UUID | None = None,
) -> ARRecord:
    from datetime import date as _date  # noqa: F811

    record = ARRecord(
        id=uuid4(),
        tenant_id=tenant_id,
        sales_order_id=sales_order_id,
        customer_id=customer_id,
        total_amount=total_amount,
        received_amount=received_amount,
        currency=currency,
        due_date=due_date,
        status=_derive_ar_status(total_amount, received_amount),
        memo=memo,
        created_by=created_by,
    )
    session.add(record)
    await session.flush()
    return record


async def get_ar_record(
    session: AsyncSession, *, tenant_id: UUID, record_id: UUID
) -> ARRecord | None:
    stmt = select(ARRecord).where(ARRecord.id == record_id, ARRecord.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_ar_records(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    status: str | None = None,
) -> list[ARRecord]:
    stmt = (
        select(ARRecord)
        .where(ARRecord.tenant_id == tenant_id)
        .order_by(ARRecord.due_date)
    )
    if status:
        stmt = stmt.where(ARRecord.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_ar_record(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    record_id: UUID,
    received_amount: Decimal | None = None,
    status: str | None = None,
    memo: str | None = None,
    updated_by: UUID | None = None,
) -> ARRecord | None:
    record = await get_ar_record(session, tenant_id=tenant_id, record_id=record_id)
    if record is None:
        return None
    if received_amount is not None:
        record.received_amount = received_amount
        record.status = _derive_ar_status(record.total_amount, received_amount)
    if status is not None:
        record.status = status
    if memo is not None:
        record.memo = memo
    if updated_by is not None:
        record.updated_by = updated_by
    await session.flush()
    return record
