"""mfg: create qc_inspections table

Revision ID: mfg_0003_qc_inspection
Revises: mfg_0002_job_ticket
Create Date: 2026-04-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mfg_0003_qc_inspection"
down_revision: str | None = "mfg_0002_job_ticket"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qc_inspections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("inspection_no", sa.String(64), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("sample_size", sa.Integer, nullable=False),
        sa.Column("defect_count", sa.Integer, nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("inspector_id", postgresql.UUID(as_uuid=True), nullable=False),
        # 审计
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        # 时间戳
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="mfg",
    )


def downgrade() -> None:
    op.drop_table("qc_inspections", schema="mfg")
