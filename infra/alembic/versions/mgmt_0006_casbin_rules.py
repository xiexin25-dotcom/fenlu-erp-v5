"""mgmt: casbin_rules table for RBAC policy storage

Revision ID: mgmt_0006_casbin_rules
Revises: mgmt_0005_approval
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mgmt_0006_casbin_rules"
down_revision: str | None = "mgmt_0005_approval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mgmt"


def upgrade() -> None:
    op.create_table(
        "casbin_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ptype", sa.String(8), nullable=False, comment="p or g"),
        sa.Column("v0", sa.String(256), nullable=False, server_default=""),
        sa.Column("v1", sa.String(256), nullable=False, server_default=""),
        sa.Column("v2", sa.String(256), nullable=False, server_default=""),
        sa.Column("v3", sa.String(256), nullable=False, server_default=""),
        sa.Column("v4", sa.String(256), nullable=False, server_default=""),
        sa.Column("v5", sa.String(256), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_casbin_rules_ptype", "casbin_rules", ["ptype"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("casbin_rules", schema=SCHEMA)
