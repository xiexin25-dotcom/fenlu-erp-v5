"""组织机构路由 (对应原系统 1.2 组织管理)。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from packages.shared.auth import CurrentUser
from packages.shared.db import get_session
from packages.shared.models import Organization
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/orgs", tags=["organizations"])


class OrgCreate(BaseModel):
    type_id: UUID
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    parent_id: UUID | None = None
    leader_id: UUID | None = None
    phone: str | None = None
    email: str | None = None
    description: str | None = None
    sort_order: int = 0


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    parent_id: UUID | None
    type_id: UUID
    code: str
    name: str
    leader_id: UUID | None
    sort_order: int


@router.get("", response_model=list[OrgOut])
async def list_orgs(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[Organization]:
    result = await session.execute(
        select(Organization)
        .where(Organization.tenant_id == user.tenant_id)
        .order_by(Organization.sort_order)
    )
    return list(result.scalars().all())


@router.post("", response_model=OrgOut, status_code=201)
async def create_org(
    body: OrgCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Organization:
    org = Organization(
        tenant_id=user.tenant_id,
        **body.model_dump(),
    )
    session.add(org)
    await session.flush()
    return org


@router.get("/{org_id}", response_model=OrgOut)
async def get_org(
    org_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Organization:
    org = (
        await session.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if org is None:
        raise HTTPException(404, "organization not found")
    return org
