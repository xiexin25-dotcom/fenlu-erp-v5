"""scm: warehouses + locations (4-level hierarchy)

Revision ID: scm_0004_warehouse
Revises: scm_0003_supplier_product
Create Date: 2026-04-07 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "scm_0004_warehouse"
down_revision: str = "scm_0003_supplier_product"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "scm"


def upgrade() -> None:
    # --- warehouses ---
    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("address", sa.String(256), nullable=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("remark", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_wh_tenant_code"),
        schema=S,
    )

    # --- locations ---
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("level", sa.String(8), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.locations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("capacity", sa.Integer, nullable=True, comment="库位容量(件)"),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "warehouse_id", "code", name="uq_loc_tenant_wh_code"),
        schema=S,
    )
    op.create_index("ix_loc_tenant_warehouse", "locations", ["tenant_id", "warehouse_id"], schema=S)
    op.create_index("ix_loc_parent", "locations", ["parent_id"], schema=S)


def downgrade() -> None:
    op.drop_index("ix_loc_parent", table_name="locations", schema=S)
    op.drop_index("ix_loc_tenant_warehouse", table_name="locations", schema=S)
    op.drop_table("locations", schema=S)
    op.drop_table("warehouses", schema=S)
