"""plm: routings + routing_operations

Revision ID: plm_0005_routing
Revises: plm_0004_cad_attachments
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "plm_0005_routing"
down_revision: str = "plm_0004_cad_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "routings",
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
        sa.UniqueConstraint("product_id", "version", name="uq_plm_routings_product_version"),
        schema="plm",
    )

    op.create_table(
        "routing_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "routing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plm.routings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("operation_code", sa.String(64), nullable=False),
        sa.Column("operation_name", sa.String(200), nullable=False),
        sa.Column("workstation_code", sa.String(64), nullable=True),
        sa.Column("standard_minutes", sa.Float, nullable=False),
        sa.Column("setup_minutes", sa.Float, nullable=False, server_default="0"),
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
    op.drop_table("routing_operations", schema="plm")
    op.drop_table("routings", schema="plm")
