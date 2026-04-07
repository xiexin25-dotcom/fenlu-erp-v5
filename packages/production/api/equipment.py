"""Equipment + EAM endpoints · TASK-MFG-007 / MFG-008。

Routes:
    POST   /mfg/equipment                    创建设备
    GET    /mfg/equipment                     设备列表
    GET    /mfg/equipment/{id}                单台设备
    GET    /mfg/equipment/{id}/oee?date=      OEE 计算
    POST   /mfg/equipment/{id}/faults         记录故障
    GET    /mfg/equipment/{id}/faults         故障列表
    POST   /mfg/maintenance/plans             创建维保计划
    POST   /mfg/maintenance/generate          触发到期维保生成 (模拟 cron)
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import Equipment, FaultRecord, MaintenanceLog, MaintenancePlan
from packages.production.services.event_publisher import EventPublisher
from packages.production.api.job_tickets import get_publisher
from packages.production.services.maintenance import generate_due_maintenance
from packages.production.services.oee import calculate_oee
from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Lane
from packages.shared.contracts.events import EquipmentFaultEvent, EventType
from packages.shared.contracts.production import EquipmentSummary, OEERecordDTO
from packages.shared.db import get_session

router = APIRouter(tags=["equipment"])


# ── Request / Response schemas ──────────────────────────────────────────────── #


class EquipmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    workshop_id: UUID
    status: str = "idle"
    is_special_equipment: bool = False


class FaultCreate(BaseModel):
    fault_code: str = Field(..., max_length=64)
    severity: str = Field(..., pattern=r"^(minor|major|critical)$")
    description: str | None = None
    started_at: datetime
    ended_at: datetime | None = None


class FaultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    equipment_id: UUID
    fault_code: str
    severity: str
    description: str | None
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime


class MaintenancePlanCreate(BaseModel):
    equipment_id: UUID
    name: str = Field(..., max_length=255)
    interval_days: int = Field(..., ge=1)


class MaintenancePlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    equipment_id: UUID
    name: str
    interval_days: int
    last_generated: date | None
    is_active: bool
    created_at: datetime


class MaintenanceLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    equipment_id: UUID
    plan_id: UUID | None
    description: str
    performed_at: datetime
    performed_by: UUID
    created_at: datetime


# ── Helpers ─────────────────────────────────────────────────────────────────── #


def _to_summary(eq: Equipment) -> EquipmentSummary:
    return EquipmentSummary.model_validate(
        {
            "id": eq.id,
            "code": eq.code,
            "name": eq.name,
            "workshop_id": eq.workshop_id,
            "status": eq.status,
            "is_special_equipment": eq.is_special_equipment,
            "created_at": eq.created_at,
            "updated_at": eq.updated_at,
        }
    )


# ── Equipment CRUD ──────────────────────────────────────────────────────────── #


@router.post("/equipment", response_model=EquipmentSummary, status_code=201)
async def create_equipment(
    body: EquipmentCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> EquipmentSummary:
    eq = Equipment(
        tenant_id=user.tenant_id,
        code=body.code,
        name=body.name,
        workshop_id=body.workshop_id,
        status=body.status,
        is_special_equipment=body.is_special_equipment,
        created_by=user.id,
    )
    session.add(eq)
    await session.flush()
    await session.refresh(eq)
    return _to_summary(eq)


@router.get("/equipment", response_model=list[EquipmentSummary])
async def list_equipment(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[EquipmentSummary]:
    result = await session.execute(
        select(Equipment)
        .where(Equipment.tenant_id == user.tenant_id)
        .order_by(Equipment.code)
    )
    return [_to_summary(eq) for eq in result.scalars().all()]


@router.get("/equipment/{equipment_id}", response_model=EquipmentSummary)
async def get_equipment(
    equipment_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> EquipmentSummary:
    eq = (
        await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if eq is None:
        raise HTTPException(404, "equipment not found")
    return _to_summary(eq)


# ── OEE (TASK-MFG-008) ──────────────────────────────────────────────────────── #


@router.get("/equipment/{equipment_id}/oee", response_model=OEERecordDTO)
async def get_oee(
    equipment_id: UUID,
    user: CurrentUser,
    target_date: date | None = None,
    session: AsyncSession = Depends(get_session),
) -> OEERecordDTO:
    # Verify equipment
    eq = (
        await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if eq is None:
        raise HTTPException(404, "equipment not found")

    d = target_date or date.today()
    result = await calculate_oee(session, equipment_id, d)

    return OEERecordDTO(
        equipment_id=equipment_id,
        record_date=d,
        availability=result.availability,
        performance=result.performance,
        quality=result.quality,
        oee=result.oee,
    )


# ── Fault records ───────────────────────────────────────────────────────────── #


@router.post("/equipment/{equipment_id}/faults", response_model=FaultOut, status_code=201)
async def create_fault(
    equipment_id: UUID,
    body: FaultCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    publisher: EventPublisher = Depends(get_publisher),
) -> FaultRecord:
    # Verify equipment
    eq = (
        await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if eq is None:
        raise HTTPException(404, "equipment not found")

    fault = FaultRecord(
        tenant_id=user.tenant_id,
        equipment_id=equipment_id,
        fault_code=body.fault_code,
        severity=body.severity,
        description=body.description,
        started_at=body.started_at,
        ended_at=body.ended_at,
        created_by=user.id,
    )
    session.add(fault)

    # Update equipment status to fault
    eq.status = "fault"

    await session.flush()
    await session.refresh(fault)

    # Emit EquipmentFaultEvent
    event = EquipmentFaultEvent(
        event_id=uuid4(),
        event_type=EventType.EQUIPMENT_FAULT,
        source_lane=Lane.PRODUCTION,
        occurred_at=datetime.now(timezone.utc),
        tenant_id=user.tenant_id,
        actor_id=user.id,
        equipment_id=equipment_id,
        fault_code=body.fault_code,
        severity=body.severity,
    )
    await publisher.publish(event)

    return fault


@router.get("/equipment/{equipment_id}/faults", response_model=list[FaultOut])
async def list_faults(
    equipment_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[FaultRecord]:
    result = await session.execute(
        select(FaultRecord).where(
            FaultRecord.equipment_id == equipment_id,
            FaultRecord.tenant_id == user.tenant_id,
        ).order_by(FaultRecord.started_at.desc())
    )
    return list(result.scalars().all())


# ── Maintenance plans ──────────────────────────────────────────────────────── #


@router.post("/maintenance/plans", response_model=MaintenancePlanOut, status_code=201)
async def create_maintenance_plan(
    body: MaintenancePlanCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> MaintenancePlan:
    # Verify equipment
    eq = (
        await session.execute(
            select(Equipment).where(
                Equipment.id == body.equipment_id,
                Equipment.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if eq is None:
        raise HTTPException(404, "equipment not found")

    plan = MaintenancePlan(
        tenant_id=user.tenant_id,
        equipment_id=body.equipment_id,
        name=body.name,
        interval_days=body.interval_days,
        created_by=user.id,
    )
    session.add(plan)
    await session.flush()
    await session.refresh(plan)
    return plan


@router.post("/maintenance/generate", response_model=list[MaintenanceLogOut])
async def trigger_maintenance_generation(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[MaintenanceLog]:
    """手动触发到期维保生成 (生产环境由 Celery beat 调用)。"""
    logs = await generate_due_maintenance(session)
    return logs
