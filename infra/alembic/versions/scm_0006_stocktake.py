"""scm: stocktakes + stocktake_lines

Revision ID: scm_0006_stocktake
Revises: scm_0005_inventory
Create Date: 2026-04-07 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "scm_0006_stocktake"
down_revision: str = "scm_0005_inventory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "scm"


def upgrade() -> None:
    op.create_table(
        "stocktakes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stocktake_no", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.warehouses.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("stocktake_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text, nullable=True),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "stocktake_no", name="uq_st_tenant_no"),
        schema=S,
    )
    op.create_index("ix_st_tenant_status", "stocktakes", ["tenant_id", "status"], schema=S)

    op.create_table(
        "stocktake_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stocktake_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.stocktakes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_no", sa.String(32), nullable=False, server_default=""),
        sa.Column("uom", sa.String(8), nullable=False, server_default="pcs"),
        sa.Column("system_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("actual_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("variance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("remark", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("stocktake_id", "product_id", "batch_no", name="uq_stl_stocktake_prod_batch"),
        schema=S,
    )


def downgrade() -> None:
    op.drop_table("stocktake_lines", schema=S)
    op.drop_index("ix_st_tenant_status", table_name="stocktakes", schema=S)
    op.drop_table("stocktakes", schema=S)
