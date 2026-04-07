"""
审批流引擎 · ApprovalDefinition / ApprovalInstance / ApprovalStep
=================================================================

ApprovalDefinition: 按 business_type 配置线性 N-step 审批模板。
ApprovalInstance:   一次具体审批流程实例。
ApprovalStep:       实例中每一步的审批记录。

设计: 线性审批 — step_no 从 1 递增,当前步骤审批通过后自动推进到下一步。
      全部步骤通过 → instance.status = approved。
      任一步骤拒绝 → instance.status = rejected。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db.base import Base
from packages.shared.db.mixins import AuditMixin, TenantMixin, TimestampMixin, UUIDPKMixin

SCHEMA = "mgmt"


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class ApprovalAction(StrEnum):
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    WITHDRAW = "withdraw"


class InstanceStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class StepStatus(StrEnum):
    WAITING = "waiting"
    APPROVED = "approved"
    REJECTED = "rejected"


# --------------------------------------------------------------------------- #
# ApprovalDefinition (审批模板)
# --------------------------------------------------------------------------- #


class ApprovalDefinition(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """审批定义 — 每个 business_type 对应一个线性多步模板。

    ``steps_config`` 是 JSON 数组,每项:
        {"step_no": 1, "name": "部门主管", "approver_id": "<UUID>"}
    """

    __tablename__ = "approval_definitions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "business_type", name="uq_approval_defs_tenant_btype"
        ),
        {"schema": SCHEMA},
    )

    business_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="业务类型,如 purchase_order"
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    steps_config: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, comment="步骤配置 JSON"
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# ApprovalInstance (审批实例)
# --------------------------------------------------------------------------- #


class ApprovalInstance(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """一次具体的审批流。"""

    __tablename__ = "approval_instances"
    __table_args__ = (
        Index("ix_approval_inst_tenant_btype", "tenant_id", "business_type"),
        Index("ix_approval_inst_tenant_status", "tenant_id", "status"),
        {"schema": SCHEMA},
    )

    definition_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.approval_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    business_type: Mapped[str] = mapped_column(String(64), nullable=False)
    business_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, comment="关联业务单据 ID"
    )
    initiator_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, comment="发起人"
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="业务快照"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=InstanceStatus.PENDING
    )
    current_step: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="当前待审步骤号"
    )
    total_steps: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="总步骤数"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    steps: Mapped[list[ApprovalStep]] = relationship(
        "ApprovalStep",
        back_populates="instance",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ApprovalStep.step_no",
    )


# --------------------------------------------------------------------------- #
# ApprovalStep (审批步骤)
# --------------------------------------------------------------------------- #


class ApprovalStep(Base, UUIDPKMixin, TenantMixin, TimestampMixin):
    """审批实例中的单步记录。"""

    __tablename__ = "approval_steps"
    __table_args__ = (
        UniqueConstraint(
            "instance_id", "step_no", name="uq_approval_steps_inst_no"
        ),
        Index("ix_approval_steps_approver", "approver_id"),
        {"schema": SCHEMA},
    )

    instance_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.approval_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="步骤名称")
    approver_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, comment="审批人"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=StepStatus.WAITING
    )
    action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    instance: Mapped[ApprovalInstance] = relationship(
        "ApprovalInstance", back_populates="steps"
    )
