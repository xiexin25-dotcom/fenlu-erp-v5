"""
Celery worker + beat schedule
==============================

启动:
    celery -A packages.management_decision.worker worker --beat --loglevel=info

调度:
- 每小时: OEE / 产量 roll-up (由 event_consumer 实时写入,此处仅修正)
- 每日 02:00: 财务 / HR / 安全 roll-up
- 每日 03:00: 全量 roll-up (冗余保障)
"""

from __future__ import annotations

import asyncio
import logging
import os

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery("mgmt_worker", broker=REDIS_URL, backend=REDIS_URL)

app.conf.beat_schedule = {
    "daily-finance-rollup": {
        "task": "packages.management_decision.worker.daily_finance_rollup",
        "schedule": crontab(hour=2, minute=0),
    },
    "daily-hr-rollup": {
        "task": "packages.management_decision.worker.daily_hr_rollup",
        "schedule": crontab(hour=2, minute=10),
    },
    "daily-safety-rollup": {
        "task": "packages.management_decision.worker.daily_safety_rollup",
        "schedule": crontab(hour=2, minute=20),
    },
    "daily-full-rollup": {
        "task": "packages.management_decision.worker.full_rollup",
        "schedule": crontab(hour=3, minute=0),
    },
}
app.conf.timezone = "Asia/Shanghai"


def _run_async(coro):  # type: ignore[no-untyped-def]
    """在 sync Celery task 中运行 async 函数。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _get_tenant_ids() -> list:
    """获取所有活跃 tenant ID。"""
    from sqlalchemy import select

    from packages.shared.db.base import get_sessionmaker
    from packages.shared.models import Tenant

    sm = get_sessionmaker()
    async with sm() as session:
        result = await session.execute(
            select(Tenant.id).where(Tenant.is_active.is_(True))
        )
        return [row[0] for row in result.all()]


async def _run_rollup_for_all_tenants(rollup_name: str) -> dict:
    """对所有 tenant 执行指定 roll-up。"""
    from packages.shared.db.base import get_sessionmaker

    from .services import rollups

    rollup_func = getattr(rollups, rollup_name)
    tenant_ids = await _get_tenant_ids()

    sm = get_sessionmaker()
    results = {}
    for tid in tenant_ids:
        async with sm() as session:
            try:
                r = await rollup_func(session, tenant_id=tid)
                await session.commit()
                results[str(tid)] = r
            except Exception:
                await session.rollback()
                logger.exception("Roll-up %s failed for tenant %s", rollup_name, tid)
                results[str(tid)] = {"status": "error"}

    return results


@app.task
def daily_finance_rollup() -> dict:
    return _run_async(_run_rollup_for_all_tenants("run_daily_finance_rollup"))


@app.task
def daily_hr_rollup() -> dict:
    return _run_async(_run_rollup_for_all_tenants("run_daily_hr_rollup"))


@app.task
def daily_safety_rollup() -> dict:
    return _run_async(_run_rollup_for_all_tenants("run_daily_safety_rollup"))


@app.task
def full_rollup() -> dict:
    return _run_async(_run_rollup_for_all_tenants("run_all_rollups"))
