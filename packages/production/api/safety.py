"""Safety hazard endpoints · TASK-MFG-009。

Routes:
    POST   /mfg/safety/hazards                      上报隐患
    GET    /mfg/safety/hazards                       列表
    GET    /mfg/safety/hazards/{id}                  详情
    PATCH  /mfg/safety/hazards/{id}/transition       状态流转
    GET    /mfg/safety/hazards/{id}/audit-log        审计日志
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import HazardAuditLog, SafetyHazard
from packages.production.services.event_publisher import EventPublisher
from packages.production.api.job_tickets import get_publisher
from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Lane
from packages.shared.contracts.events import BaseEvent, EventType
from packages.shared.contracts.production import (
    HazardLevel,
    HazardStatus,
    SafetyHazardDTO,
)
from packages.shared.db import get_session

router = APIRouter(prefix="/safety", tags=["safety"])

# ── 状态机 ──────────────────────────────────────────────────────────────────── #

_ALLOWED_TRANSITIONS: dict[HazardStatus, list[HazardStatus]] = {
    HazardStatus.REPORTED: [HazardStatus.ASSIGNED],
    HazardStatus.ASSIGNED: [HazardStatus.RECTIFYING],
    HazardStatus.RECTIFYING: [HazardStatus.VERIFIED],
    HazardStatus.VERIFIED: [HazardStatus.CLOSED],
    HazardStatus.CLOSED: [],
}


# ── Request schemas ─────────────────────────────────────────────────────────── #


class HazardCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    hazard_no: str = Field(..., max_length=64)
    location: str = Field(..., max_length=255)
    level: HazardLevel
    description: str | None = None


class HazardTransition(BaseModel):
    status: HazardStatus
    remark: str | None = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    hazard_id: UUID
    from_status: str
    to_status: str
    transitioned_by: UUID
    remark: str | None
    created_at: datetime


# ── Helpers ─────────────────────────────────────────────────────────────────── #


def _to_dto(h: SafetyHazard) -> SafetyHazardDTO:
    return SafetyHazardDTO.model_validate(
        {
            "id": h.id,
            "hazard_no": h.hazard_no,
            "location": h.location,
            "level": h.level,
            "status": h.status,
            "reported_by": h.reported_by,
            "rectified_at": h.rectified_at,
            "closed_at": h.closed_at,
            "created_at": h.created_at,
            "updated_at": h.updated_at,
        }
    )


# ── Endpoints ───────────────────────────────────────────────────────────────── #


@router.post("/hazards", response_model=SafetyHazardDTO, status_code=201)
async def create_hazard(
    body: HazardCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    publisher: EventPublisher = Depends(get_publisher),
) -> SafetyHazardDTO:
    hazard = SafetyHazard(
        tenant_id=user.tenant_id,
        hazard_no=body.hazard_no,
        location=body.location,
        level=body.level.value,
        status=HazardStatus.REPORTED.value,
        description=body.description,
        reported_by=user.id,
        created_by=user.id,
    )
    session.add(hazard)
    await session.flush()
    await session.refresh(hazard)

    # Audit log for initial creation
    log = HazardAuditLog(
        tenant_id=user.tenant_id,
        hazard_id=hazard.id,
        from_status="",
        to_status=HazardStatus.REPORTED.value,
        transitioned_by=user.id,
        remark="隐患上报",
    )
    session.add(log)

    # Emit event
    event = BaseEvent(
        event_id=uuid4(),
        event_type=EventType.HAZARD_REPORTED,
        source_lane=Lane.PRODUCTION,
        occurred_at=datetime.now(timezone.utc),
        tenant_id=user.tenant_id,
        actor_id=user.id,
    )
    await publisher.publish(event)

    await session.flush()
    return _to_dto(hazard)


@router.get("/hazards", response_model=list[SafetyHazardDTO])
async def list_hazards(
    user: CurrentUser,
    status: HazardStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[SafetyHazardDTO]:
    stmt = select(SafetyHazard).where(SafetyHazard.tenant_id == user.tenant_id)
    if status is not None:
        stmt = stmt.where(SafetyHazard.status == status.value)
    stmt = stmt.order_by(SafetyHazard.created_at.desc())
    result = await session.execute(stmt)
    return [_to_dto(h) for h in result.scalars().all()]


@router.get("/hazards/{hazard_id}", response_model=SafetyHazardDTO)
async def get_hazard(
    hazard_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> SafetyHazardDTO:
    h = (
        await session.execute(
            select(SafetyHazard).where(
                SafetyHazard.id == hazard_id,
                SafetyHazard.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if h is None:
        raise HTTPException(404, "hazard not found")
    return _to_dto(h)


@router.patch("/hazards/{hazard_id}/transition", response_model=SafetyHazardDTO)
async def transition_hazard(
    hazard_id: UUID,
    body: HazardTransition,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> SafetyHazardDTO:
    h = (
        await session.execute(
            select(SafetyHazard).where(
                SafetyHazard.id == hazard_id,
                SafetyHazard.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if h is None:
        raise HTTPException(404, "hazard not found")

    current = HazardStatus(h.status)
    target = body.status
    allowed = _ALLOWED_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(
            422,
            f"cannot transition from {current.value} to {target.value}; "
            f"allowed: {[s.value for s in allowed]}",
        )

    old_status = h.status
    h.status = target.value
    h.updated_by = user.id

    now = datetime.now(timezone.utc)
    if target == HazardStatus.VERIFIED:
        h.rectified_at = now
    elif target == HazardStatus.CLOSED:
        h.closed_at = now

    # Write audit log
    log = HazardAuditLog(
        tenant_id=user.tenant_id,
        hazard_id=hazard_id,
        from_status=old_status,
        to_status=target.value,
        transitioned_by=user.id,
        remark=body.remark,
    )
    session.add(log)

    await session.flush()
    await session.refresh(h)
    return _to_dto(h)


@router.get("/hazards/{hazard_id}/audit-log", response_model=list[AuditLogOut])
async def get_audit_log(
    hazard_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[HazardAuditLog]:
    result = await session.execute(
        select(HazardAuditLog).where(
            HazardAuditLog.hazard_id == hazard_id,
            HazardAuditLog.tenant_id == user.tenant_id,
        ).order_by(HazardAuditLog.created_at.asc())
    )
    return list(result.scalars().all())
