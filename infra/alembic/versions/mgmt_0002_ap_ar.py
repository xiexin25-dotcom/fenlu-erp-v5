"""mgmt: AP (accounts payable) + AR (accounts receivable)

Revision ID: mgmt_0002_ap_ar
Revises: mgmt_0001_gl_journal
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mgmt_0002_ap_ar"
down_revision: str | None = "mgmt_0001_gl_journal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mgmt"


def upgrade() -> None:
    op.create_table(
        "ap_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "purchase_order_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="采购订单 ID",
        ),
        sa.Column(
            "supplier_id", postgresql.UUID(as_uuid=True), nullable=False, comment="供应商 ID"
        ),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False, comment="应付总额"),
        sa.Column(
            "paid_amount",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
            comment="已付金额",
        ),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CNY"),
        sa.Column("due_date", sa.Date, nullable=False, comment="到期日"),
        sa.Column("status", sa.String(16), nullable=False, server_default="unpaid"),
        sa.Column("memo", sa.Text, nullable=True),
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
        sa.UniqueConstraint("tenant_id", "purchase_order_id", name="uq_ap_records_tenant_po"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ap_records_tenant_status", "ap_records", ["tenant_id", "status"], schema=SCHEMA
    )
    op.create_index(
        "ix_ap_records_tenant_due", "ap_records", ["tenant_id", "due_date"], schema=SCHEMA
    )

    op.create_table(
        "ar_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "sales_order_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="销售订单 ID",
        ),
        sa.Column(
            "customer_id", postgresql.UUID(as_uuid=True), nullable=False, comment="客户 ID"
        ),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False, comment="应收总额"),
        sa.Column(
            "received_amount",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
            comment="已收金额",
        ),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CNY"),
        sa.Column("due_date", sa.Date, nullable=False, comment="到期日"),
        sa.Column("status", sa.String(16), nullable=False, server_default="unpaid"),
        sa.Column("memo", sa.Text, nullable=True),
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
        sa.UniqueConstraint("tenant_id", "sales_order_id", name="uq_ar_records_tenant_so"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ar_records_tenant_status", "ar_records", ["tenant_id", "status"], schema=SCHEMA
    )
    op.create_index(
        "ix_ar_records_tenant_due", "ar_records", ["tenant_id", "due_date"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("ar_records", schema=SCHEMA)
    op.drop_table("ap_records", schema=SCHEMA)
