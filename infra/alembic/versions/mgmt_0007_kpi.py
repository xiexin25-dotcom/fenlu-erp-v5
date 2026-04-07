"""mgmt: KPI definitions + data points

Revision ID: mgmt_0007_kpi
Revises: mgmt_0006_casbin_rules
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mgmt_0007_kpi"
down_revision: str | None = "mgmt_0006_casbin_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mgmt"


def upgrade() -> None:
    op.create_table(
        "kpi_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(64), nullable=False, comment="KPI 编码"),
        sa.Column("name", sa.String(128), nullable=False, comment="KPI 名称"),
        sa.Column("category", sa.String(32), nullable=False, comment="分类"),
        sa.Column("unit", sa.String(32), nullable=False, comment="单位"),
        sa.Column("source_lane", sa.String(8), nullable=False, comment="数据来源 lane"),
        sa.Column("aggregation", sa.String(16), nullable=False, comment="聚合方式"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_kpi_defs_tenant_code"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_kpi_defs_category", "kpi_definitions", ["tenant_id", "category"], schema=SCHEMA
    )

    op.create_table(
        "kpi_data_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kpi_code", sa.String(64), nullable=False, comment="关联 KPI code"),
        sa.Column("period", sa.Date, nullable=False, comment="数据周期"),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("target", sa.Float, nullable=True, comment="目标值"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "tenant_id", "kpi_code", "period", name="uq_kpi_dp_tenant_code_period"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_kpi_dp_code_period",
        "kpi_data_points",
        ["tenant_id", "kpi_code", "period"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("kpi_data_points", schema=SCHEMA)
    op.drop_table("kpi_definitions", schema=SCHEMA)
