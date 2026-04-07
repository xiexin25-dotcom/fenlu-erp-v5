"""scm: supplier_products (ASL for BOM-driven purchase)

Revision ID: scm_0003_supplier_product
Revises: scm_0002_purchase
Create Date: 2026-04-07 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "scm_0003_supplier_product"
down_revision: str = "scm_0002_purchase"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "scm"


def upgrade() -> None:
    op.create_table(
        "supplier_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.suppliers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("is_preferred", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("lead_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("min_order_qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("uom", sa.String(8), nullable=False, server_default="pcs"),
        sa.Column("reference_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "supplier_id", "product_id", name="uq_sp_tenant_supplier_product"),
        schema=S,
    )


def downgrade() -> None:
    op.drop_table("supplier_products", schema=S)
