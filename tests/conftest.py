"""Pytest conftest · 全局 fixtures。

提供 SQLite-backed test DB + authenticated TestClient,所有 lane 的测试都
应该 import 这里的 fixtures 而不是自己造轮子。

设计要点:
- 每个测试函数一个全新的 in-memory SQLite,完全隔离
- 自动剥离 PostgreSQL schema (sqlite 不支持)
- 自动 monkey-patch DATABASE_URL
- `client` fixture 给未认证测试用
- `auth_client` fixture 给已登录测试用 (admin user)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# 必须在 import 任何 packages 之前设置环境变量
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")


@pytest.fixture(autouse=True)
def _reset_db_globals() -> Iterator[None]:
    """每个测试重置 db 全局,保证 in-memory sqlite 不串数据。"""
    import packages.shared.db.base as db_base

    db_base._engine = None
    db_base._sessionmaker = None
    db_base.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    yield


@pytest.fixture
def metadata() -> Any:
    """剥离 schema (sqlite 不支持) 并返回 Base.metadata。"""
    # 必须 import 模型让 metadata 注册
    import packages.management_decision.models  # noqa: F401
    import packages.product_lifecycle.models  # noqa: F401
    import packages.production.models  # noqa: F401
    import packages.shared.models  # noqa: F401
    import packages.supply_chain.models  # noqa: F401
    from packages.shared.db import Base

    for table in Base.metadata.tables.values():
        table.schema = None
    return Base.metadata


@pytest_asyncio.fixture
async def db_session(metadata: Any) -> AsyncIterator[AsyncSession]:
    """每测试一个全新 sqlite,自动建表。"""
    from packages.shared.db import get_engine, get_sessionmaker

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    sm = get_sessionmaker()
    async with sm() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seed_admin(db_session: AsyncSession) -> dict[str, Any]:
    """建一个 demo tenant + admin user,返回登录所需信息。"""
    from packages.shared.auth import hash_password
    from packages.shared.models import Tenant, User

    tenant = Tenant(code="demo", name="Demo Co")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id,
        username="admin",
        full_name="Admin User",
        password_hash=hash_password("pass1234"),
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()

    return {
        "tenant_code": tenant.code,
        "tenant_id": tenant.id,
        "username": user.username,
        "user_id": user.id,
        "password": "pass1234",
    }


@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """未认证的 TestClient (db_session fixture 保证表已建好)。"""
    from apps.api_gateway.main import app

    return TestClient(app)


@pytest.fixture
def auth_client(client: TestClient, seed_admin: dict[str, Any]) -> TestClient:
    """已登录的 TestClient,Authorization header 已注入。"""
    r = client.post(
        "/auth/login",
        json={
            "tenant_code": seed_admin["tenant_code"],
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
