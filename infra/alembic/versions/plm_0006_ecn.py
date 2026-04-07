"""plm: ecns (engineering change notices)

Revision ID: plm_0006_ecn
Revises: plm_0005_routing
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "plm_0006_ecn"
down_revision: str = "plm_0005_routing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ecns",
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
        sa.Column("ecn_no", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
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
        sa.UniqueConstraint("tenant_id", "ecn_no", name="uq_plm_ecns_tenant_ecn_no"),
        schema="plm",
    )


def downgrade() -> None:
    op.drop_table("ecns", schema="plm")
