"""mfg: create job_tickets table

Revision ID: mfg_0002_job_ticket
Revises: mfg_0001_work_order
Create Date: 2026-04-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mfg_0002_job_ticket"
down_revision: str | None = "mfg_0001_work_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mfg.work_orders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ticket_no", sa.String(64), nullable=False),
        # 报工数据
        sa.Column("completed_qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("scrap_qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("minutes", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text, nullable=True),
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
    op.drop_table("job_tickets", schema="mfg")
