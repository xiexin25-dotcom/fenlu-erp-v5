"""mfg: create energy_meters + energy_readings tables

Revision ID: mfg_0006_energy
Revises: mfg_0005_safety
Create Date: 2026-04-06

Note: In production PostgreSQL, energy_readings should be converted to a
TimescaleDB hypertable after table creation:
    SELECT create_hypertable('mfg.energy_readings', 'timestamp');
This is done via init.sql or a manual step, not in Alembic (SQLite compat).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mfg_0006_energy"
down_revision: str | None = "mfg_0005_safety"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "energy_meters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("energy_type", sa.String(20), nullable=False),
        sa.Column("uom", sa.String(16), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="mfg",
    )

    op.create_table(
        "energy_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "meter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mfg.energy_meters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("energy_type", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reading", sa.Float, nullable=False),
        sa.Column("delta", sa.Float, nullable=False),
        sa.Column("uom", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="mfg",
    )


def downgrade() -> None:
    op.drop_table("energy_readings", schema="mfg")
    op.drop_table("energy_meters", schema="mfg")
