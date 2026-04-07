"""mgmt: GL accounts + journal entries + journal lines

Revision ID: mgmt_0001_gl_journal
Revises: 0001_foundation
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mgmt_0001_gl_journal"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mgmt"


def upgrade() -> None:
    op.create_table(
        "gl_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(32), nullable=False, comment="科目编码"),
        sa.Column("name", sa.String(128), nullable=False, comment="科目名称"),
        sa.Column("account_type", sa.String(16), nullable=False, comment="科目类型"),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.gl_accounts.id", ondelete="SET NULL"),
            nullable=True,
            comment="上级科目",
        ),
        sa.Column("level", sa.Integer, nullable=False, server_default="1", comment="科目层级"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text, nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        # AuditMixin
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_gl_accounts_tenant_code"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_gl_accounts_tenant_type",
        "gl_accounts",
        ["tenant_id", "account_type"],
        schema=SCHEMA,
    )

    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("entry_no", sa.String(32), nullable=False, comment="凭证号"),
        sa.Column("entry_date", sa.Date, nullable=False, comment="记账日期"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("memo", sa.Text, nullable=True, comment="摘要"),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True, comment="过账时间"),
        # TimestampMixin
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        # AuditMixin
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "entry_no", name="uq_journal_entries_tenant_no"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_journal_entries_tenant_date",
        "journal_entries",
        ["tenant_id", "entry_date"],
        schema=SCHEMA,
    )

    op.create_table(
        "journal_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.journal_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("line_no", sa.Integer, nullable=False, comment="行号"),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.gl_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "debit_amount",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
            comment="借方金额",
        ),
        sa.Column(
            "credit_amount",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
            comment="贷方金额",
        ),
        sa.Column("description", sa.String(256), nullable=True, comment="行摘要"),
        # TimestampMixin
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "(debit_amount = 0 AND credit_amount > 0) OR (debit_amount > 0 AND credit_amount = 0)",
            name="ck_journal_lines_one_side",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_journal_lines_entry", "journal_lines", ["entry_id"], schema=SCHEMA)
    op.create_index("ix_journal_lines_account", "journal_lines", ["account_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("journal_lines", schema=SCHEMA)
    op.drop_table("journal_entries", schema=SCHEMA)
    op.drop_table("gl_accounts", schema=SCHEMA)
