"""mgmt: employees + payrolls + payroll_items

Revision ID: mgmt_0003_hr
Revises: mgmt_0002_ap_ar
Create Date: 2026-04-06 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mgmt_0003_hr"
down_revision: str | None = "mgmt_0002_ap_ar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "mgmt"


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("employee_no", sa.String(32), nullable=False, comment="工号"),
        sa.Column("name", sa.String(64), nullable=False, comment="姓名"),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.users.id", ondelete="SET NULL"),
            nullable=True,
            comment="关联登录账号",
        ),
        sa.Column(
            "department_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.organizations.id", ondelete="SET NULL"),
            nullable=True,
            comment="所属部门",
        ),
        sa.Column("position", sa.String(64), nullable=False, server_default="", comment="岗位"),
        sa.Column(
            "base_salary",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
            comment="基本工资",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("tenant_id", "employee_no", name="uq_employees_tenant_no"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_employees_tenant_user"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_employees_tenant_dept", "employees", ["tenant_id", "department_id"], schema=SCHEMA
    )

    op.create_table(
        "payrolls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("period", sa.String(7), nullable=False, comment="薪资周期 YYYY-MM"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column(
            "total_amount",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
            comment="总金额",
        ),
        sa.Column("head_count", sa.Integer, nullable=False, server_default="0", comment="人数"),
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
        sa.UniqueConstraint("tenant_id", "period", name="uq_payrolls_tenant_period"),
        schema=SCHEMA,
    )

    op.create_table(
        "payroll_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "payroll_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.payrolls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.employees.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("employee_no", sa.String(32), nullable=False, comment="冗余工号"),
        sa.Column("employee_name", sa.String(64), nullable=False, comment="冗余姓名"),
        sa.Column("base_salary", sa.Numeric(18, 4), nullable=False, comment="基本工资"),
        sa.Column(
            "overtime_pay",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
            comment="加班费",
        ),
        sa.Column(
            "deductions",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
            comment="扣除项",
        ),
        sa.Column("net_pay", sa.Numeric(18, 4), nullable=False, comment="实发工资"),
        sa.Column("memo", sa.String(256), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "tenant_id", "payroll_id", "employee_id", name="uq_payroll_items_payroll_emp"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_payroll_items_payroll", "payroll_items", ["payroll_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_payroll_items_employee", "payroll_items", ["employee_id"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("payroll_items", schema=SCHEMA)
    op.drop_table("payrolls", schema=SCHEMA)
    op.drop_table("employees", schema=SCHEMA)
