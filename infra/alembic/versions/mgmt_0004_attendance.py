"""mgmt: attendance records (daily clock-in/out)

Revision ID: mgmt_0004_attendance
Revises: mgmt_0003_hr
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mgmt_0004_attendance"
down_revision: str | None = "mgmt_0003_hr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mgmt"


def upgrade() -> None:
    op.create_table(
        "attendances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("work_date", sa.Date, nullable=False, comment="考勤日期"),
        sa.Column("clock_in", sa.Time, nullable=True, comment="上班打卡"),
        sa.Column("clock_out", sa.Time, nullable=True, comment="下班打卡"),
        sa.Column("status", sa.String(16), nullable=False, server_default="normal"),
        sa.Column(
            "work_hours",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="8.00",
            comment="工作时长",
        ),
        sa.Column(
            "overtime_hours",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0",
            comment="加班时长",
        ),
        sa.Column("memo", sa.String(256), nullable=True),
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
        sa.UniqueConstraint(
            "tenant_id", "employee_id", "work_date", name="uq_attendances_tenant_emp_date"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_attendances_tenant_date", "attendances", ["tenant_id", "work_date"], schema=SCHEMA
    )
    op.create_index(
        "ix_attendances_employee", "attendances", ["employee_id"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("attendances", schema=SCHEMA)
