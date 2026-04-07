"""
异步 SQLAlchemy 2.0 基础设施
============================

提供:
- async engine + session factory
- DeclarativeBase
- get_session() FastAPI 依赖
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://fenlu:fenlu_dev@localhost:5432/fenlu_v5",
)


class Base(DeclarativeBase):
    """所有 ORM 模型的根。各 lane 通过 __table_args__ = {'schema': 'mfg'} 隔离。"""

    type_annotation_map: dict[Any, Any] = {}


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # SQLite (测试场景) 不支持连接池参数
        kwargs: dict[str, Any] = {"echo": False, "pool_pre_ping": True}
        if not DATABASE_URL.startswith("sqlite"):
            kwargs["pool_size"] = 10
            kwargs["max_overflow"] = 20
        _engine = create_async_engine(DATABASE_URL, **kwargs)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖:每个请求一个 session,自动 commit/rollback。"""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
