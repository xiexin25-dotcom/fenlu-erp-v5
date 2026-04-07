"""QC Inspection endpoints · TASK-MFG-005。

Routes:
    POST  /mfg/qc/inspections                  创建检验记录
    GET   /mfg/qc/inspections?work_order_id=    查询
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import QCInspection
from packages.production.services.event_publisher import (
    EventPublisher,
)
from packages.production.api.job_tickets import get_publisher
from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Lane
from packages.shared.contracts.events import EventType, QCFailedEvent
from packages.shared.contracts.production import (
    InspectionResult,
    InspectionType,
    QCInspectionDTO,
)
from packages.shared.db import get_session

router = APIRouter(prefix="/qc", tags=["qc"])


# ── Request schema ──────────────────────────────────────────────────────────── #


class InspectionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    inspection_no: str = Field(..., max_length=64)
    type: InspectionType
    product_id: UUID
    work_order_id: UUID | None = None
    sample_size: int = Field(..., ge=1)
    defect_count: int = Field(..., ge=0)
    result: InspectionResult
    inspector_id: UUID


# ── Helpers ─────────────────────────────────────────────────────────────────── #


def _to_dto(insp: QCInspection) -> QCInspectionDTO:
    return QCInspectionDTO.model_validate(
        {
            "id": insp.id,
            "inspection_no": insp.inspection_no,
            "type": insp.type,
            "product_id": insp.product_id,
            "work_order_id": insp.work_order_id,
            "sample_size": insp.sample_size,
            "defect_count": insp.defect_count,
            "result": insp.result,
            "inspector_id": insp.inspector_id,
            "created_at": insp.created_at,
            "updated_at": insp.updated_at,
        }
    )


# ── Endpoints ───────────────────────────────────────────────────────────────── #


@router.post("/inspections", response_model=QCInspectionDTO, status_code=201)
async def create_inspection(
    body: InspectionCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    publisher: EventPublisher = Depends(get_publisher),
) -> QCInspectionDTO:
    insp = QCInspection(
        tenant_id=user.tenant_id,
        inspection_no=body.inspection_no,
        type=body.type.value,
        product_id=body.product_id,
        work_order_id=body.work_order_id,
        sample_size=body.sample_size,
        defect_count=body.defect_count,
        result=body.result.value,
        inspector_id=body.inspector_id,
        created_by=user.id,
    )
    session.add(insp)
    await session.flush()
    await session.refresh(insp)

    # Auto-emit QCFailedEvent when result = FAIL
    if body.result == InspectionResult.FAIL:
        event = QCFailedEvent(
            event_id=uuid4(),
            event_type=EventType.QC_FAILED,
            source_lane=Lane.PRODUCTION,
            occurred_at=datetime.now(timezone.utc),
            tenant_id=user.tenant_id,
            actor_id=user.id,
            inspection_id=insp.id,
            product_id=body.product_id,
            work_order_id=body.work_order_id,
            defect_count=body.defect_count,
            sample_size=body.sample_size,
        )
        await publisher.publish(event)

    return _to_dto(insp)


@router.get("/inspections", response_model=list[QCInspectionDTO])
async def list_inspections(
    user: CurrentUser,
    work_order_id: UUID | None = None,
    product_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[QCInspectionDTO]:
    stmt = select(QCInspection).where(QCInspection.tenant_id == user.tenant_id)
    if work_order_id is not None:
        stmt = stmt.where(QCInspection.work_order_id == work_order_id)
    if product_id is not None:
        stmt = stmt.where(QCInspection.product_id == product_id)
    stmt = stmt.order_by(QCInspection.created_at.desc())
    result = await session.execute(stmt)
    return [_to_dto(i) for i in result.scalars().all()]
