"""
Casbin enforcer 服务
====================

- 从 mgmt.casbin_rules 加载策略到内存
- 使用 infra/casbin/model.conf (RBAC with domain/tenant)
- Redis pub/sub 热更新: 任何策略变更后 publish 到 channel,
  所有进程收到后 reload
- 提供 sync 的 enforce() 供 FastAPI Depends 使用

典型 policy 行:
    p, role:admin, tenant_xxx, mgmt.*, *          # admin 可访问 mgmt 下所有资源
    p, role:hr,    tenant_xxx, mgmt.employee, *   # hr 角色可管理员工
    g, user_id,    role:admin, tenant_xxx          # 用户属于 admin 角色 (in tenant)
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any
from uuid import UUID

import casbin
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.casbin_rule import CasbinRule
from packages.shared.db.base import get_sessionmaker

logger = logging.getLogger(__name__)

MODEL_PATH = str(Path(__file__).resolve().parents[3] / "infra" / "casbin" / "model.conf")
REDIS_CHANNEL = "casbin:policy_changed"

# Singleton enforcer
_enforcer: casbin.Enforcer | None = None


# --------------------------------------------------------------------------- #
# Enforcer lifecycle
# --------------------------------------------------------------------------- #


def get_enforcer() -> casbin.Enforcer:
    """获取全局 Casbin enforcer (懒加载)。"""
    global _enforcer
    if _enforcer is None:
        _enforcer = casbin.Enforcer(MODEL_PATH)
        # 初始策略为空,需要调用 load_policies_from_db() 加载
    return _enforcer


def reset_enforcer() -> None:
    """重置 (测试用)。"""
    global _enforcer
    _enforcer = None


async def load_policies_from_db(session: AsyncSession | None = None) -> int:
    """从 DB 加载全量策略到 enforcer 内存,返回规则数。"""
    enforcer = get_enforcer()
    enforcer.clear_policy()

    own_session = session is None
    if session is None:
        sm = get_sessionmaker()
        session = sm()

    try:
        result = await session.execute(select(CasbinRule))
        rules = list(result.scalars().all())

        count = 0
        for rule in rules:
            vals = [v for v in [rule.v0, rule.v1, rule.v2, rule.v3, rule.v4, rule.v5] if v]
            if rule.ptype == "p":
                enforcer.add_policy(*vals)
            elif rule.ptype == "g":
                enforcer.add_grouping_policy(*vals)
            count += 1

        logger.info("Casbin: loaded %d rules from DB", count)
        return count
    finally:
        if own_session:
            await session.close()


# --------------------------------------------------------------------------- #
# Enforce
# --------------------------------------------------------------------------- #


def enforce(sub: str, dom: str, obj: str, act: str) -> bool:
    """同步 enforce — 供 FastAPI Depends 使用。"""
    enforcer = get_enforcer()
    return enforcer.enforce(sub, dom, obj, act)


# --------------------------------------------------------------------------- #
# Policy CRUD (async, via DB + enforcer memory)
# --------------------------------------------------------------------------- #


async def add_policy(
    session: AsyncSession,
    *,
    ptype: str = "p",
    v0: str = "",
    v1: str = "",
    v2: str = "",
    v3: str = "",
    v4: str = "",
    v5: str = "",
) -> CasbinRule:
    """添加策略到 DB 并同步到 enforcer 内存。"""
    from uuid import uuid4

    rule = CasbinRule(
        id=uuid4(), ptype=ptype, v0=v0, v1=v1, v2=v2, v3=v3, v4=v4, v5=v5
    )
    session.add(rule)
    await session.flush()

    # 同步到内存
    vals = [v for v in [v0, v1, v2, v3, v4, v5] if v]
    enforcer = get_enforcer()
    if ptype == "p":
        enforcer.add_policy(*vals)
    elif ptype == "g":
        enforcer.add_grouping_policy(*vals)

    await _publish_change()
    return rule


async def remove_policy(
    session: AsyncSession,
    *,
    ptype: str = "p",
    v0: str = "",
    v1: str = "",
    v2: str = "",
    v3: str = "",
) -> bool:
    """删除策略。"""
    stmt = delete(CasbinRule).where(
        CasbinRule.ptype == ptype,
        CasbinRule.v0 == v0,
        CasbinRule.v1 == v1,
        CasbinRule.v2 == v2,
        CasbinRule.v3 == v3,
    )
    result = await session.execute(stmt)
    await session.flush()

    vals = [v for v in [v0, v1, v2, v3] if v]
    enforcer = get_enforcer()
    if ptype == "p":
        enforcer.remove_policy(*vals)
    elif ptype == "g":
        enforcer.remove_grouping_policy(*vals)

    await _publish_change()
    return (result.rowcount or 0) > 0


async def add_role_for_user(
    session: AsyncSession,
    *,
    user_id: str,
    role: str,
    tenant_id: str,
) -> CasbinRule:
    """给用户分配角色 (g 规则)。"""
    return await add_policy(
        session, ptype="g", v0=user_id, v1=role, v2=tenant_id
    )


async def list_policies(session: AsyncSession) -> list[CasbinRule]:
    result = await session.execute(
        select(CasbinRule).order_by(CasbinRule.ptype, CasbinRule.v0)
    )
    return list(result.scalars().all())


# --------------------------------------------------------------------------- #
# Redis pub/sub 热更新
# --------------------------------------------------------------------------- #


async def _publish_change() -> None:
    """通知其他进程重新加载策略。"""
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(redis_url)
        await r.publish(REDIS_CHANNEL, "reload")
        await r.aclose()
    except Exception:
        logger.warning("Casbin: failed to publish policy change to Redis", exc_info=True)


async def start_policy_watcher() -> None:
    """后台任务: 监听 Redis channel,收到通知后 reload。"""
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        logger.info("Casbin: REDIS_URL not set, policy watcher disabled")
        return
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(REDIS_CHANNEL)
        logger.info("Casbin: policy watcher started on channel %s", REDIS_CHANNEL)
        async for message in pubsub.listen():
            if message["type"] == "message":
                logger.info("Casbin: received policy change, reloading...")
                await load_policies_from_db()
    except Exception:
        logger.warning("Casbin: policy watcher failed", exc_info=True)
