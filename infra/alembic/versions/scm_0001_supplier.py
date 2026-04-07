"""scm: suppliers, supplier_ratings, supplier_tier_changes

Revision ID: scm_0001_supplier
Revises: 0001_foundation
Create Date: 2026-04-07 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "scm_0001_supplier"
down_revision: str = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- suppliers ---
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("tier", sa.String(16), nullable=False, server_default="approved"),
        sa.Column("rating_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("is_online", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("contact_name", sa.String(64), nullable=True),
        sa.Column("contact_phone", sa.String(32), nullable=True),
        sa.Column("address", sa.String(256), nullable=True),
        sa.Column("remark", sa.Text, nullable=True),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_supplier_tenant_code"),
        sa.CheckConstraint("rating_score >= 0 AND rating_score <= 100"),
        schema="scm",
    )
    op.create_index(
        "ix_supplier_tenant_tier", "suppliers", ["tenant_id", "tier"], schema="scm",
    )

    # --- supplier_ratings ---
    op.create_table(
        "supplier_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scm.suppliers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("quality_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("delivery_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("price_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("service_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_score", sa.Float, nullable=False, server_default="0"),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "supplier_id", "period_start",
            name="uq_rating_tenant_supplier_period",
        ),
        sa.CheckConstraint("total_score >= 0 AND total_score <= 100"),
        schema="scm",
    )

    # --- supplier_tier_changes ---
    op.create_table(
        "supplier_tier_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scm.suppliers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("from_tier", sa.String(16), nullable=False),
        sa.Column("to_tier", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("approval_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column(
            "approval_id", postgresql.UUID(as_uuid=True), nullable=True,
            comment="Lane 4 审批单 ID",
        ),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        schema="scm",
    )


def downgrade() -> None:
    op.drop_table("supplier_tier_changes", schema="scm")
    op.drop_table("supplier_ratings", schema="scm")
    op.drop_index("ix_supplier_tenant_tier", table_name="suppliers", schema="scm")
    op.drop_table("suppliers", schema="scm")
