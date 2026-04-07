"""plm: quotes, quote_items, sales_order_lines, add quote_id to sales_orders

Revision ID: plm_0008_quotes_order_lines
Revises: plm_0007_crm
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "plm_0008_quotes_order_lines"
down_revision: str = "plm_0007_crm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    # quotes
    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.customers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("quote_no", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text, nullable=True),
        *_audit_cols(),
        *_ts_cols(),
        sa.UniqueConstraint("tenant_id", "quote_no", name="uq_plm_quotes_tenant_quote_no"),
        schema="plm",
    )

    # quote_items
    op.create_table(
        "quote_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.quotes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(16), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        *_audit_cols(),
        *_ts_cols(),
        schema="plm",
    )

    # sales_order_lines
    op.create_table(
        "sales_order_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plm.sales_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(16), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        *_audit_cols(),
        *_ts_cols(),
        schema="plm",
    )

    # add quote_id to sales_orders
    op.add_column(
        "sales_orders",
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="plm",
    )


def downgrade() -> None:
    op.drop_column("sales_orders", "quote_id", schema="plm")
    op.drop_table("sales_order_lines", schema="plm")
    op.drop_table("quote_items", schema="plm")
    op.drop_table("quotes", schema="plm")
