"""mfg: create work_orders table

Revision ID: mfg_0001_work_order
Revises: 0001_foundation
Create Date: 2026-04-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mfg_0001_work_order"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # 业务字段
        sa.Column("order_no", sa.String(64), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("routing_id", postgresql.UUID(as_uuid=True), nullable=False),
        # 数量 (Quantity DTO 拆 value + uom)
        sa.Column("planned_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("planned_quantity_uom", sa.String(16), nullable=False),
        sa.Column("completed_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("completed_quantity_uom", sa.String(16), nullable=False),
        sa.Column("scrap_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("scrap_quantity_uom", sa.String(16), nullable=False),
        # 状态
        sa.Column("status", sa.String(20), nullable=False),
        # 计划 / 实际时间
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        # 关联
        sa.Column("sales_order_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        # 约束
        sa.UniqueConstraint("tenant_id", "order_no", name="uq_mfg_wo_tenant_order_no"),
        schema="mfg",
    )


def downgrade() -> None:
    op.drop_table("work_orders", schema="mfg")
