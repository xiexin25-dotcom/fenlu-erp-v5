"""scm: inventory + stock_moves

Revision ID: scm_0005_inventory
Revises: scm_0004_warehouse
Create Date: 2026-04-07 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "scm_0005_inventory"
down_revision: str = "scm_0004_warehouse"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "scm"


def upgrade() -> None:
    # --- inventory ---
    op.create_table(
        "inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("location_code", sa.String(32), nullable=True),
        sa.Column("uom", sa.String(8), nullable=False, server_default="pcs"),
        sa.Column("batch_no", sa.String(32), nullable=False, server_default=""),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("on_hand", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("in_transit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "product_id", "warehouse_id", "batch_no",
                            name="uq_inv_tenant_prod_wh_batch"),
        schema=S,
    )
    op.create_index("ix_inv_tenant_product", "inventory", ["tenant_id", "product_id"], schema=S)
    op.create_index("ix_inv_tenant_warehouse", "inventory", ["tenant_id", "warehouse_id"], schema=S)

    # --- stock_moves ---
    op.create_table(
        "stock_moves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("move_no", sa.String(32), nullable=False, unique=True),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(8), nullable=False, server_default="pcs"),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_location", sa.String(32), nullable=True),
        sa.Column("to_location", sa.String(32), nullable=True),
        sa.Column("batch_no", sa.String(32), nullable=False, server_default=""),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True,
                  comment="关联单据 ID"),
        sa.Column("remark", sa.Text, nullable=True),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        schema=S,
    )
    op.create_index("ix_sm_tenant_product", "stock_moves", ["tenant_id", "product_id"], schema=S)
    op.create_index("ix_sm_tenant_type", "stock_moves", ["tenant_id", "type"], schema=S)
    op.create_index("ix_sm_reference", "stock_moves", ["reference_id"], schema=S)


def downgrade() -> None:
    op.drop_index("ix_sm_reference", table_name="stock_moves", schema=S)
    op.drop_index("ix_sm_tenant_type", table_name="stock_moves", schema=S)
    op.drop_index("ix_sm_tenant_product", table_name="stock_moves", schema=S)
    op.drop_table("stock_moves", schema=S)
    op.drop_index("ix_inv_tenant_warehouse", table_name="inventory", schema=S)
    op.drop_index("ix_inv_tenant_product", table_name="inventory", schema=S)
    op.drop_table("inventory", schema=S)
