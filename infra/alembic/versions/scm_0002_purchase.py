"""scm: purchase_requests, rfqs, purchase_orders, purchase_receipts + lines

Revision ID: scm_0002_purchase
Revises: scm_0001_supplier
Create Date: 2026-04-07 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "scm_0002_purchase"
down_revision: str = "scm_0001_supplier"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "scm"


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # purchase_requests
    # ------------------------------------------------------------------ #
    op.create_table(
        "purchase_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("request_no", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("needed_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text, nullable=True),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "request_no", name="uq_pr_tenant_no"),
        schema=S,
    )
    op.create_index("ix_pr_tenant_status", "purchase_requests", ["tenant_id", "status"], schema=S)

    op.create_table(
        "purchase_request_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.purchase_requests.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(8), nullable=False, server_default="pcs"),
        sa.Column("remark", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=S,
    )

    # ------------------------------------------------------------------ #
    # rfqs
    # ------------------------------------------------------------------ #
    op.create_table(
        "rfqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rfq_no", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.suppliers.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.purchase_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text, nullable=True),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "rfq_no", name="uq_rfq_tenant_no"),
        schema=S,
    )

    op.create_table(
        "rfq_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.rfqs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(8), nullable=False, server_default="pcs"),
        sa.Column("quoted_unit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=S,
    )

    # ------------------------------------------------------------------ #
    # purchase_orders
    # ------------------------------------------------------------------ #
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("order_no", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.rfqs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        sa.Column("expected_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_terms", sa.String(64), nullable=True),
        sa.Column("remark", sa.Text, nullable=True),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "order_no", name="uq_po_tenant_no"),
        schema=S,
    )
    op.create_index("ix_po_tenant_status", "purchase_orders", ["tenant_id", "status"], schema=S)
    op.create_index("ix_po_tenant_supplier", "purchase_orders", ["tenant_id", "supplier_id"], schema=S)

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(8), nullable=False, server_default="pcs"),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="CNY"),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("received_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=S,
    )

    # ------------------------------------------------------------------ #
    # purchase_receipts
    # ------------------------------------------------------------------ #
    op.create_table(
        "purchase_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("receipt_no", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text, nullable=True),
        # mixins
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.UniqueConstraint("tenant_id", "receipt_no", name="uq_receipt_tenant_no"),
        schema=S,
    )

    op.create_table(
        "purchase_receipt_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey(f"{S}.purchase_receipts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordered_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("received_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("rejected_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("uom", sa.String(8), nullable=False, server_default="pcs"),
        sa.Column("batch_no", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=S,
    )


def downgrade() -> None:
    op.drop_table("purchase_receipt_lines", schema=S)
    op.drop_table("purchase_receipts", schema=S)
    op.drop_table("purchase_order_lines", schema=S)
    op.drop_index("ix_po_tenant_supplier", table_name="purchase_orders", schema=S)
    op.drop_index("ix_po_tenant_status", table_name="purchase_orders", schema=S)
    op.drop_table("purchase_orders", schema=S)
    op.drop_table("rfq_lines", schema=S)
    op.drop_table("rfqs", schema=S)
    op.drop_table("purchase_request_lines", schema=S)
    op.drop_index("ix_pr_tenant_status", table_name="purchase_requests", schema=S)
    op.drop_table("purchase_requests", schema=S)
