"""
GL 会计科目 / 记账凭证 / 凭证行
================================

双重记账约束 (借贷平衡) 在 ORM 层通过 ``JournalEntry.validate_balanced``
校验,API 层在创建前调用此方法,不平衡则 422。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from packages.shared.db.base import Base
from packages.shared.db.mixins import AuditMixin, TenantMixin, TimestampMixin, UUIDPKMixin

SCHEMA = "mgmt"


# --------------------------------------------------------------------------- #
# 枚举
# --------------------------------------------------------------------------- #


class AccountType(StrEnum):
    """会计科目类型 (一级分类)。"""

    ASSET = "asset"  # 资产
    LIABILITY = "liability"  # 负债
    EQUITY = "equity"  # 所有者权益
    REVENUE = "revenue"  # 收入
    EXPENSE = "expense"  # 费用


class JournalStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    VOIDED = "voided"


# --------------------------------------------------------------------------- #
# 会计科目表
# --------------------------------------------------------------------------- #


class GLAccount(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """总账科目 (Chart of Accounts)。"""

    __tablename__ = "gl_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_gl_accounts_tenant_code"),
        Index("ix_gl_accounts_tenant_type", "tenant_id", "account_type"),
        {"schema": SCHEMA},
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False, comment="科目编码,如 1001")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="科目名称")
    account_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="科目类型")
    parent_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.gl_accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="上级科目",
    )
    level: Mapped[int] = mapped_column(nullable=False, default=1, comment="科目层级 1-4")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    children: Mapped[list[GLAccount]] = relationship(
        "GLAccount", back_populates="parent", lazy="selectin"
    )
    parent: Mapped[GLAccount | None] = relationship(
        "GLAccount", back_populates="children", remote_side="GLAccount.id", lazy="joined"
    )


# --------------------------------------------------------------------------- #
# 记账凭证 (Journal Entry)
# --------------------------------------------------------------------------- #


class JournalEntry(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """记账凭证头。"""

    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entry_no", name="uq_journal_entries_tenant_no"),
        Index("ix_journal_entries_tenant_date", "tenant_id", "entry_date"),
        {"schema": SCHEMA},
    )

    entry_no: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="凭证号,如 JV-202604-0001"
    )
    entry_date: Mapped[date] = mapped_column(nullable=False, comment="记账日期")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=JournalStatus.DRAFT, comment="凭证状态"
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True, comment="摘要")
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="过账时间"
    )

    # relationships
    lines: Mapped[list[JournalLine]] = relationship(
        "JournalLine",
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="JournalLine.line_no",
    )


# --------------------------------------------------------------------------- #
# 凭证行 (Journal Line)
# --------------------------------------------------------------------------- #


class JournalLine(Base, UUIDPKMixin, TenantMixin, TimestampMixin):
    """凭证明细行 — 每行只有借方或贷方金额,不能同时非零。"""

    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint(
            "(debit_amount = 0 AND credit_amount > 0) OR (debit_amount > 0 AND credit_amount = 0)",
            name="ck_journal_lines_one_side",
        ),
        Index("ix_journal_lines_entry", "entry_id"),
        Index("ix_journal_lines_account", "account_id"),
        {"schema": SCHEMA},
    )

    entry_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.journal_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_no: Mapped[int] = mapped_column(nullable=False, comment="行号")
    account_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.gl_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="借方金额"
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), comment="贷方金额"
    )
    description: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="行摘要")

    # relationships
    entry: Mapped[JournalEntry] = relationship("JournalEntry", back_populates="lines")
    account: Mapped[GLAccount] = relationship("GLAccount", lazy="joined")
