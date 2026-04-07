"""plm: cad_attachments

Revision ID: plm_0004_cad_attachments
Revises: plm_0003_bom
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "plm_0004_cad_attachments"
down_revision: str = "plm_0003_bom"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cad_attachments",
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
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False, unique=True),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
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
    op.drop_table("cad_attachments", schema="plm")
