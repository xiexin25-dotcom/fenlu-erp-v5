"""management_decision test fixtures.

确保 mgmt 模型被注册到 Base.metadata,供 SQLite 建表。
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

import packages.management_decision.models  # noqa: F401 — 注册 ORM 到 metadata
from packages.management_decision.models.finance import AccountType, GLAccount


@pytest_asyncio.fixture
async def seed_gl_accounts(
    db_session: AsyncSession, seed_admin: dict[str, Any]
) -> dict[str, Any]:
    """创建一组基本科目供凭证测试使用。"""
    tid = seed_admin["tenant_id"]
    uid = seed_admin["user_id"]

    cash = GLAccount(
        id=uuid4(),
        tenant_id=tid,
        code="1001",
        name="库存现金",
        account_type=AccountType.ASSET,
        level=1,
        created_by=uid,
    )
    bank = GLAccount(
        id=uuid4(),
        tenant_id=tid,
        code="1002",
        name="银行存款",
        account_type=AccountType.ASSET,
        level=1,
        created_by=uid,
    )
    revenue = GLAccount(
        id=uuid4(),
        tenant_id=tid,
        code="6001",
        name="主营业务收入",
        account_type=AccountType.REVENUE,
        level=1,
        created_by=uid,
    )
    expense = GLAccount(
        id=uuid4(),
        tenant_id=tid,
        code="6601",
        name="管理费用",
        account_type=AccountType.EXPENSE,
        level=1,
        created_by=uid,
    )

    db_session.add_all([cash, bank, revenue, expense])
    await db_session.commit()

    return {
        **seed_admin,
        "cash_id": cash.id,
        "bank_id": bank.id,
        "revenue_id": revenue.id,
        "expense_id": expense.id,
    }
