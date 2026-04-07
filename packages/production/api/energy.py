"""Energy endpoints · TASK-MFG-010。

Routes:
    POST   /mfg/energy/meters                          创建表具
    GET    /mfg/energy/meters                           表具列表
    POST   /mfg/energy/readings                         批量采集
    GET    /mfg/energy/unit-consumption?product_id=&period=  单位能耗汇总
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import EnergyMeter, EnergyReading
from packages.production.models.job_ticket import JobTicket
from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Quantity, UnitOfMeasure
from packages.shared.contracts.production import (
    EnergyReadingDTO,
    EnergyType,
    UnitConsumptionDTO,
)
from packages.shared.db import get_session

router = APIRouter(prefix="/energy", tags=["energy"])


# ── Request / Response schemas ──────────────────────────────────────────────── #


class MeterCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    energy_type: EnergyType
    uom: str = Field(..., max_length=16)
    location: str | None = None


class MeterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    energy_type: str
    uom: str
    location: str | None
    created_at: datetime


class ReadingInput(BaseModel):
    meter_id: UUID
    energy_type: EnergyType
    timestamp: datetime
    reading: float = Field(..., ge=0)
    delta: float = Field(..., ge=0)
    uom: str


class BatchReadings(BaseModel):
    readings: list[ReadingInput] = Field(..., min_length=1)


# ── Helpers ─────────────────────────────────────────────────────────────────── #


def _parse_period(period: str) -> timedelta:
    if not period.endswith("d"):
        raise HTTPException(422, "period must end with 'd' (e.g. '30d')")
    try:
        days = int(period[:-1])
    except ValueError:
        raise HTTPException(422, "period must be like '30d'")
    if days <= 0:
        raise HTTPException(422, "period must be positive")
    return timedelta(days=days)


# ── Meter CRUD ──────────────────────────────────────────────────────────────── #


@router.post("/meters", response_model=MeterOut, status_code=201)
async def create_meter(
    body: MeterCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> EnergyMeter:
    meter = EnergyMeter(
        tenant_id=user.tenant_id,
        code=body.code,
        name=body.name,
        energy_type=body.energy_type.value,
        uom=body.uom,
        location=body.location,
        created_by=user.id,
    )
    session.add(meter)
    await session.flush()
    await session.refresh(meter)
    return meter


@router.get("/meters", response_model=list[MeterOut])
async def list_meters(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[EnergyMeter]:
    result = await session.execute(
        select(EnergyMeter)
        .where(EnergyMeter.tenant_id == user.tenant_id)
        .order_by(EnergyMeter.code)
    )
    return list(result.scalars().all())


# ── Batch reading ingest ────────────────────────────────────────────────────── #


@router.post("/readings", response_model=list[EnergyReadingDTO], status_code=201)
async def ingest_readings(
    body: BatchReadings,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[EnergyReadingDTO]:
    results: list[EnergyReadingDTO] = []
    for r in body.readings:
        reading = EnergyReading(
            tenant_id=user.tenant_id,
            meter_id=r.meter_id,
            energy_type=r.energy_type.value,
            timestamp=r.timestamp,
            reading=r.reading,
            delta=r.delta,
            uom=r.uom,
        )
        session.add(reading)
        results.append(
            EnergyReadingDTO(
                meter_id=r.meter_id,
                energy_type=r.energy_type,
                timestamp=r.timestamp,
                reading=r.reading,
                delta=r.delta,
                uom=r.uom,
            )
        )
    await session.flush()
    return results


# ── Unit consumption rollup ─────────────────────────────────────────────────── #


@router.get("/unit-consumption", response_model=UnitConsumptionDTO)
async def unit_consumption(
    user: CurrentUser,
    product_id: UUID = Query(...),
    period: str = Query("30d"),
    energy_type: EnergyType = Query(EnergyType.ELECTRICITY),
    session: AsyncSession = Depends(get_session),
) -> UnitConsumptionDTO:
    td = _parse_period(period)
    now = datetime.now(timezone.utc)
    period_start = (now - td).date()
    period_end = now.date()
    since = now - td

    # Total energy consumption for this energy_type in period
    consumption_row = (
        await session.execute(
            select(func.coalesce(func.sum(EnergyReading.delta), 0.0)).where(
                EnergyReading.tenant_id == user.tenant_id,
                EnergyReading.energy_type == energy_type.value,
                EnergyReading.timestamp >= since,
            )
        )
    ).scalar_one()
    total_consumption = float(consumption_row)

    # Total output for product in period (from job tickets)
    output_row = (
        await session.execute(
            select(func.coalesce(func.sum(JobTicket.completed_qty), 0)).where(
                JobTicket.tenant_id == user.tenant_id,
                JobTicket.reported_at >= since,
            )
        )
    ).scalar_one()
    output_qty = Decimal(str(output_row))

    unit_cons = total_consumption / float(output_qty) if output_qty > 0 else 0.0

    return UnitConsumptionDTO(
        product_id=product_id,
        period_start=period_start,
        period_end=period_end,
        energy_type=energy_type,
        total_consumption=total_consumption,
        output_quantity=Quantity(value=output_qty, uom=UnitOfMeasure.PIECE),
        unit_consumption=round(unit_cons, 6),
    )
