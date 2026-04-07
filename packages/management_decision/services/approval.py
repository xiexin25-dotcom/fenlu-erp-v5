"""
审批流引擎 service
==================

线性 N-step 审批:
1. submit → 创建 instance + N 个 step (status=waiting)
2. approve step N → 如果 N < total, current_step++ ; 如果 N == total, instance → approved
3. reject 任一步 → instance → rejected
4. withdraw → 发起人撤回 → instance → withdrawn
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.management_decision.models.approval import (
    ApprovalAction,
    ApprovalDefinition,
    ApprovalInstance,
    ApprovalStep,
    InstanceStatus,
    StepStatus,
)


# --------------------------------------------------------------------------- #
# Definition CRUD
# --------------------------------------------------------------------------- #


async def create_definition(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    business_type: str,
    name: str,
    steps_config: list[dict[str, Any]],
    description: str | None = None,
    created_by: UUID | None = None,
) -> ApprovalDefinition:
    defn = ApprovalDefinition(
        id=uuid4(),
        tenant_id=tenant_id,
        business_type=business_type,
        name=name,
        steps_config=steps_config,
        description=description,
        created_by=created_by,
    )
    session.add(defn)
    await session.flush()
    return defn


async def get_definition(
    session: AsyncSession, *, tenant_id: UUID, definition_id: UUID
) -> ApprovalDefinition | None:
    stmt = select(ApprovalDefinition).where(
        ApprovalDefinition.id == definition_id,
        ApprovalDefinition.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_definition_by_type(
    session: AsyncSession, *, tenant_id: UUID, business_type: str
) -> ApprovalDefinition | None:
    stmt = select(ApprovalDefinition).where(
        ApprovalDefinition.tenant_id == tenant_id,
        ApprovalDefinition.business_type == business_type,
        ApprovalDefinition.is_active.is_(True),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_definitions(
    session: AsyncSession, *, tenant_id: UUID
) -> list[ApprovalDefinition]:
    stmt = (
        select(ApprovalDefinition)
        .where(ApprovalDefinition.tenant_id == tenant_id)
        .order_by(ApprovalDefinition.business_type)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# --------------------------------------------------------------------------- #
# Submit (发起审批)
# --------------------------------------------------------------------------- #


async def submit_approval(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    business_type: str,
    business_id: UUID,
    initiator_id: UUID,
    payload: dict[str, Any],
) -> ApprovalInstance:
    """发起审批 — 根据 business_type 查找 definition,创建 instance + steps。"""
    defn = await get_definition_by_type(
        session, tenant_id=tenant_id, business_type=business_type
    )
    if defn is None:
        raise ValueError(f"未找到业务类型 '{business_type}' 的审批定义")

    steps_cfg = defn.steps_config
    instance = ApprovalInstance(
        id=uuid4(),
        tenant_id=tenant_id,
        definition_id=defn.id,
        business_type=business_type,
        business_id=business_id,
        initiator_id=initiator_id,
        payload=payload,
        status=InstanceStatus.PENDING,
        current_step=1,
        total_steps=len(steps_cfg),
        created_by=initiator_id,
    )

    for cfg in steps_cfg:
        step = ApprovalStep(
            id=uuid4(),
            tenant_id=tenant_id,
            instance_id=instance.id,
            step_no=cfg["step_no"],
            name=cfg["name"],
            approver_id=UUID(str(cfg["approver_id"])),
            status=StepStatus.WAITING,
        )
        instance.steps.append(step)

    session.add(instance)
    await session.flush()
    return instance


# --------------------------------------------------------------------------- #
# Action (审批/拒绝/撤回)
# --------------------------------------------------------------------------- #


async def act_on_approval(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    instance_id: UUID,
    actor_id: UUID,
    action: str,
    comment: str | None = None,
) -> ApprovalInstance:
    """对审批实例执行动作。"""
    instance = await get_instance(session, tenant_id=tenant_id, instance_id=instance_id)
    if instance is None:
        raise ValueError("审批实例不存在")

    if instance.status != InstanceStatus.PENDING:
        raise ValueError(f"审批已结束,当前状态: {instance.status}")

    now = datetime.now(timezone.utc)

    if action == ApprovalAction.WITHDRAW:
        if actor_id != instance.initiator_id:
            raise ValueError("只有发起人可以撤回")
        instance.status = InstanceStatus.WITHDRAWN
        instance.completed_at = now
        await session.flush()
        return instance

    # Find current step
    current = None
    for s in instance.steps:
        if s.step_no == instance.current_step:
            current = s
            break

    if current is None:
        raise ValueError("找不到当前审批步骤")

    if actor_id != current.approver_id:
        raise ValueError("你不是当前步骤的审批人")

    if action == ApprovalAction.APPROVE:
        current.status = StepStatus.APPROVED
        current.action = ApprovalAction.APPROVE
        current.comment = comment
        current.acted_at = now

        if instance.current_step >= instance.total_steps:
            instance.status = InstanceStatus.APPROVED
            instance.completed_at = now
        else:
            instance.current_step += 1

    elif action == ApprovalAction.REJECT:
        current.status = StepStatus.REJECTED
        current.action = ApprovalAction.REJECT
        current.comment = comment
        current.acted_at = now
        instance.status = InstanceStatus.REJECTED
        instance.completed_at = now

    else:
        raise ValueError(f"不支持的动作: {action}")

    await session.flush()
    return instance


# --------------------------------------------------------------------------- #
# Query
# --------------------------------------------------------------------------- #


async def get_instance(
    session: AsyncSession, *, tenant_id: UUID, instance_id: UUID
) -> ApprovalInstance | None:
    stmt = (
        select(ApprovalInstance)
        .options(selectinload(ApprovalInstance.steps))
        .where(
            ApprovalInstance.id == instance_id,
            ApprovalInstance.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_instances(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    business_type: str | None = None,
    status: str | None = None,
    initiator_id: UUID | None = None,
) -> list[ApprovalInstance]:
    stmt = (
        select(ApprovalInstance)
        .options(selectinload(ApprovalInstance.steps))
        .where(ApprovalInstance.tenant_id == tenant_id)
        .order_by(ApprovalInstance.created_at.desc())
    )
    if business_type:
        stmt = stmt.where(ApprovalInstance.business_type == business_type)
    if status:
        stmt = stmt.where(ApprovalInstance.status == status)
    if initiator_id:
        stmt = stmt.where(ApprovalInstance.initiator_id == initiator_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_pending_for_approver(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    approver_id: UUID,
) -> list[ApprovalInstance]:
    """查询某审批人待办的审批实例。"""
    # 找到该审批人作为当前步骤审批人的 pending 实例
    step_sub = (
        select(ApprovalStep.instance_id)
        .where(
            ApprovalStep.approver_id == approver_id,
            ApprovalStep.status == StepStatus.WAITING,
        )
        .scalar_subquery()
    )
    stmt = (
        select(ApprovalInstance)
        .options(selectinload(ApprovalInstance.steps))
        .where(
            ApprovalInstance.tenant_id == tenant_id,
            ApprovalInstance.status == InstanceStatus.PENDING,
            ApprovalInstance.id.in_(step_sub),
        )
        .order_by(ApprovalInstance.created_at.desc())
    )
    result = await session.execute(stmt)
    instances = list(result.scalars().all())
    # 进一步过滤: 只保留 current_step 对应的 approver 是该用户的
    return [
        inst for inst in instances
        if any(
            s.step_no == inst.current_step and s.approver_id == approver_id
            for s in inst.steps
        )
    ]
