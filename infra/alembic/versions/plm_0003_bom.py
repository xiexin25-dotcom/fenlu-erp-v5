"""plm: boms + bom_items

Revision ID: plm_0003_bom
Revises: plm_0002_products
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "plm_0003_bom"
down_revision: str = "plm_0002_products"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "boms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plm.products.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("description", sa.Text, nullable=True),
        # audit
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        # timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("product_id", "version", name="uq_plm_boms_product_version"),
        schema="plm",
    )

    op.create_table(
        "bom_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "bom_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plm.boms.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "component_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plm.products.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(16), nullable=False),
        sa.Column("scrap_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("is_optional", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("remark", sa.String(500), nullable=True),
        # audit
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        # timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="plm",
    )


def downgrade() -> None:
    op.drop_table("bom_items", schema="plm")
    op.drop_table("boms", schema="plm")
