"""mgmt: approval definitions + instances + steps

Revision ID: mgmt_0005_approval
Revises: mgmt_0004_attendance
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mgmt_0005_approval"
down_revision: str | None = "mgmt_0004_attendance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mgmt"


def upgrade() -> None:
    op.create_table(
        "approval_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("business_type", sa.String(64), nullable=False, comment="业务类型"),
        sa.Column("name", sa.String(128), nullable=False, comment="模板名称"),
        sa.Column("steps_config", postgresql.JSONB, nullable=False, comment="步骤配置"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "business_type", name="uq_approval_defs_tenant_btype"
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "approval_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.approval_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("business_type", sa.String(64), nullable=False),
        sa.Column(
            "business_id", postgresql.UUID(as_uuid=True), nullable=False, comment="业务单据 ID"
        ),
        sa.Column(
            "initiator_id", postgresql.UUID(as_uuid=True), nullable=False, comment="发起人"
        ),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="1"),
        sa.Column("total_steps", sa.Integer, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_approval_inst_tenant_btype",
        "approval_instances",
        ["tenant_id", "business_type"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_approval_inst_tenant_status",
        "approval_instances",
        ["tenant_id", "status"],
        schema=SCHEMA,
    )

    op.create_table(
        "approval_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "instance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.approval_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_no", sa.Integer, nullable=False),
        sa.Column("name", sa.String(128), nullable=False, comment="步骤名称"),
        sa.Column(
            "approver_id", postgresql.UUID(as_uuid=True), nullable=False, comment="审批人"
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="waiting"),
        sa.Column("action", sa.String(16), nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("instance_id", "step_no", name="uq_approval_steps_inst_no"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_approval_steps_approver",
        "approval_steps",
        ["approver_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("approval_steps", schema=SCHEMA)
    op.drop_table("approval_instances", schema=SCHEMA)
    op.drop_table("approval_definitions", schema=SCHEMA)
