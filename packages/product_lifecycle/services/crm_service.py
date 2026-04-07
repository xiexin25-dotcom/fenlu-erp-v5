"""CRM service: Lead/Opportunity CRUD, stage transitions, funnel aggregation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.product_lifecycle.models import (
    LEAD_TRANSITIONS,
    OPPORTUNITY_TRANSITIONS,
    Lead,
    LeadStatus,
    Opportunity,
    OpportunityStage,
)


class InvalidStageTransitionError(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"invalid stage transition: {current} → {target}")


# --------------------------------------------------------------------------- #
# Lead CRUD + transition
# --------------------------------------------------------------------------- #


async def create_lead(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    customer_id: UUID,
    title: str,
    source: str | None = None,
) -> Lead:
    lead = Lead(
        tenant_id=tenant_id,
        customer_id=customer_id,
        title=title,
        source=source,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(lead)
    await session.flush()
    return lead


async def get_lead(
    session: AsyncSession, *, tenant_id: UUID, lead_id: UUID,
) -> Lead | None:
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def transition_lead(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    lead_id: UUID,
    target_status: str,
) -> Lead:
    lead = await get_lead(session, tenant_id=tenant_id, lead_id=lead_id)
    if lead is None:
        raise ValueError("lead not found")

    current = LeadStatus(lead.status)
    target = LeadStatus(target_status)
    if target not in LEAD_TRANSITIONS.get(current, []):
        raise InvalidStageTransitionError(lead.status, target_status)

    lead.status = target.value
    lead.updated_by = user_id
    await session.flush()
    return lead


# --------------------------------------------------------------------------- #
# Opportunity CRUD + transition
# --------------------------------------------------------------------------- #


async def create_opportunity(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    customer_id: UUID,
    title: str,
    expected_amount: Decimal | None = None,
    expected_close: datetime | None = None,
) -> Opportunity:
    opp = Opportunity(
        tenant_id=tenant_id,
        customer_id=customer_id,
        title=title,
        expected_amount=expected_amount,
        expected_close=expected_close,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(opp)
    await session.flush()
    return opp


async def get_opportunity(
    session: AsyncSession, *, tenant_id: UUID, opp_id: UUID,
) -> Opportunity | None:
    result = await session.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def transition_opportunity(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    opp_id: UUID,
    target_stage: str,
) -> Opportunity:
    opp = await get_opportunity(session, tenant_id=tenant_id, opp_id=opp_id)
    if opp is None:
        raise ValueError("opportunity not found")

    current = OpportunityStage(opp.stage)
    target = OpportunityStage(target_stage)
    if target not in OPPORTUNITY_TRANSITIONS.get(current, []):
        raise InvalidStageTransitionError(opp.stage, target_stage)

    opp.stage = target.value
    opp.updated_by = user_id
    await session.flush()
    return opp


# --------------------------------------------------------------------------- #
# Funnel aggregation
# --------------------------------------------------------------------------- #


async def get_funnel(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> dict[str, dict[str, int]]:
    """返回 lead 各 status 计数 + opportunity 各 stage 计数。

    如果指定 period,按 created_at 过滤。
    返回格式:
    {
        "leads": {"new": 5, "contacted": 3, ...},
        "opportunities": {"qualification": 2, "proposal": 1, ...}
    }
    """
    # Lead counts
    lead_q = select(Lead.status, func.count()).where(Lead.tenant_id == tenant_id)
    if period_start:
        lead_q = lead_q.where(Lead.created_at >= period_start)
    if period_end:
        lead_q = lead_q.where(Lead.created_at <= period_end)
    lead_q = lead_q.group_by(Lead.status)
    lead_result = await session.execute(lead_q)
    lead_counts = {row[0]: row[1] for row in lead_result.all()}

    # Opportunity counts
    opp_q = select(Opportunity.stage, func.count()).where(Opportunity.tenant_id == tenant_id)
    if period_start:
        opp_q = opp_q.where(Opportunity.created_at >= period_start)
    if period_end:
        opp_q = opp_q.where(Opportunity.created_at <= period_end)
    opp_q = opp_q.group_by(Opportunity.stage)
    opp_result = await session.execute(opp_q)
    opp_counts = {row[0]: row[1] for row in opp_result.all()}

    return {"leads": lead_counts, "opportunities": opp_counts}
