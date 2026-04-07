"""plm: customers, contacts, leads, opportunities, sales_orders, service_tickets

Revision ID: plm_0007_crm
Revises: plm_0006_ecn
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "plm_0007_crm"
down_revision: str = "plm_0006_ecn"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tenant_fk() -> sa.Column:
    return sa.Column(
        "tenant_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def _audit_cols() -> list[sa.Column]:
    return [
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
    ]


def _ts_cols() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    # customers
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _tenant_fk(),
        sa.Column("code", sa.String(64), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("rating", sa.String(8), nullable=True),
        sa.Column("is_online", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("address", sa.Text, nullable=True),
        *_audit_cols(),
        *_ts_cols(),
        sa.UniqueConstraint("tenant_id", "code", name="uq_plm_customers_tenant_code"),
        schema="plm",
    )

    # contacts
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _tenant_fk(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.customers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("title", sa.String(64), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
        *_audit_cols(),
        *_ts_cols(),
        schema="plm",
    )

    # leads
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _tenant_fk(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.customers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        *_audit_cols(),
        *_ts_cols(),
        schema="plm",
    )

    # opportunities
    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _tenant_fk(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.customers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False, server_default="qualification"),
        sa.Column("expected_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("expected_close", sa.DateTime(timezone=True), nullable=True),
        *_audit_cols(),
        *_ts_cols(),
        schema="plm",
    )

    # sales_orders
    op.create_table(
        "sales_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _tenant_fk(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.customers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("order_no", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        sa.Column("promised_delivery", sa.DateTime(timezone=True), nullable=True),
        *_audit_cols(),
        *_ts_cols(),
        schema="plm",
    )

    # service_tickets
    op.create_table(
        "service_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _tenant_fk(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.customers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ticket_no", sa.String(64), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nps_score", sa.Integer, nullable=True),
        *_audit_cols(),
        *_ts_cols(),
        schema="plm",
    )


def downgrade() -> None:
    op.drop_table("service_tickets", schema="plm")
    op.drop_table("sales_orders", schema="plm")
    op.drop_table("opportunities", schema="plm")
    op.drop_table("leads", schema="plm")
    op.drop_table("contacts", schema="plm")
    op.drop_table("customers", schema="plm")
