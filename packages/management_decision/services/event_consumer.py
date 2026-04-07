"""
跨 Lane 事件消费者
==================

订阅 Redis Streams (plm-events / scm-events / mfg-events),
使用 consumer group 保证 at-least-once + backpressure。

使用 ``@on(EventType.X)`` 注册 handler,dispatch 时自动路由。

Handler 签名: async def handler(event_data: dict, session: AsyncSession) -> None

Stream 结构:
    stream key = "{lane}-events"   e.g. "plm-events"
    每条消息字段: event_type, payload (JSON string)

Consumer group 按 stream 分组: "mgmt-bi-{stream}"
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.contracts.events import EventType

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Handler registry
# --------------------------------------------------------------------------- #

HandlerFunc = Callable[[dict, AsyncSession], Coroutine[Any, Any, None]]

_handlers: dict[str, list[HandlerFunc]] = defaultdict(list)

# Stream → EventTypes mapping
STREAM_EVENTS: dict[str, list[str]] = {
    "plm-events": [
        EventType.SALES_ORDER_CONFIRMED,
    ],
    "scm-events": [
        EventType.PURCHASE_ORDER_APPROVED,
    ],
    "mfg-events": [
        EventType.OEE_CALCULATED,
        EventType.QC_FAILED,
        EventType.HAZARD_REPORTED,
        EventType.ENERGY_THRESHOLD_BREACHED,
        EventType.WORK_ORDER_COMPLETED,
        EventType.EQUIPMENT_FAULT,
    ],
}


def on(event_type: EventType | str) -> Callable[[HandlerFunc], HandlerFunc]:
    """装饰器: 注册事件 handler。"""

    def decorator(func: HandlerFunc) -> HandlerFunc:
        _handlers[str(event_type)].append(func)
        return func

    return decorator


def get_handlers(event_type: str) -> list[HandlerFunc]:
    return _handlers.get(event_type, [])


def get_all_handlers() -> dict[str, list[HandlerFunc]]:
    return dict(_handlers)


async def dispatch(event_type: str, event_data: dict, session: AsyncSession) -> int:
    """分发事件给所有注册的 handler,返回执行的 handler 数量。"""
    handlers = get_handlers(event_type)
    count = 0
    for handler in handlers:
        try:
            await handler(event_data, session)
            count += 1
        except Exception:
            logger.exception(
                "Handler %s failed for event %s", handler.__name__, event_type
            )
    return count


# --------------------------------------------------------------------------- #
# Concrete handlers
# --------------------------------------------------------------------------- #


@on(EventType.SALES_ORDER_CONFIRMED)
async def handle_sales_order_confirmed(data: dict, session: AsyncSession) -> None:
    """PLM 销售订单确认 → 创建 AR 应收账款。"""
    from packages.management_decision.services.ap_ar import create_ar_record

    await create_ar_record(
        session,
        tenant_id=UUID(data["tenant_id"]),
        sales_order_id=UUID(data["sales_order_id"]),
        customer_id=UUID(data["customer_id"]),
        total_amount=Decimal(str(data["total_amount"]["amount"])),
        currency=data["total_amount"].get("currency", "CNY"),
        due_date=date.today(),  # 默认当天,后续可从 payload 覆盖
        memo=f"自动创建 from event {data.get('event_id', '')}",
    )
    logger.info("AR created for sales_order %s", data.get("sales_order_id"))


@on(EventType.PURCHASE_ORDER_APPROVED)
async def handle_purchase_order_approved(data: dict, session: AsyncSession) -> None:
    """SCM 采购订单审批 → 创建 AP 应付账款。"""
    from packages.management_decision.services.ap_ar import create_ap_record

    await create_ap_record(
        session,
        tenant_id=UUID(data["tenant_id"]),
        purchase_order_id=UUID(data["purchase_order_id"]),
        supplier_id=UUID(data["supplier_id"]),
        total_amount=Decimal(str(data["total_amount"]["amount"])),
        currency=data["total_amount"].get("currency", "CNY"),
        due_date=date.today(),
        memo=f"自动创建 from event {data.get('event_id', '')}",
    )
    logger.info("AP created for purchase_order %s", data.get("purchase_order_id"))


@on(EventType.OEE_CALCULATED)
async def handle_oee_calculated(data: dict, session: AsyncSession) -> None:
    """MFG OEE 计算完成 → 写入 KPI 数据点。"""
    await _upsert_kpi_data_point(
        session,
        tenant_id=UUID(data["tenant_id"]),
        kpi_code="OPS-001",
        period=date.today(),
        value=float(data.get("oee_value", data.get("value", 0))),
    )


@on(EventType.QC_FAILED)
async def handle_qc_failed(data: dict, session: AsyncSession) -> None:
    """MFG 质检不合格 → 更新不良品率 KPI。"""
    defect_count = data.get("defect_count", 0)
    sample_size = data.get("sample_size", 1)
    rate = (defect_count / sample_size * 100) if sample_size > 0 else 0
    await _upsert_kpi_data_point(
        session,
        tenant_id=UUID(data["tenant_id"]),
        kpi_code="QUA-003",
        period=date.today(),
        value=rate,
    )


@on(EventType.HAZARD_REPORTED)
async def handle_hazard_reported(data: dict, session: AsyncSession) -> None:
    """MFG 安全隐患上报 → 累加安全隐患数 KPI。"""
    await _upsert_kpi_data_point(
        session,
        tenant_id=UUID(data["tenant_id"]),
        kpi_code="SAF-001",
        period=date.today(),
        value=1,  # 增量,aggregation=sum
        increment=True,
    )


@on(EventType.ENERGY_THRESHOLD_BREACHED)
async def handle_energy_threshold(data: dict, session: AsyncSession) -> None:
    """MFG 能耗超标 → 写入月度用电量 KPI。"""
    await _upsert_kpi_data_point(
        session,
        tenant_id=UUID(data["tenant_id"]),
        kpi_code="ENG-002",
        period=date.today(),
        value=float(data.get("actual", 0)),
    )


@on(EventType.WORK_ORDER_COMPLETED)
async def handle_work_order_completed(data: dict, session: AsyncSession) -> None:
    """MFG 工单完工 → 累加日产量 KPI。"""
    qty = data.get("completed_quantity", {})
    value = float(qty.get("value", qty) if isinstance(qty, dict) else qty)
    await _upsert_kpi_data_point(
        session,
        tenant_id=UUID(data["tenant_id"]),
        kpi_code="OPS-003",
        period=date.today(),
        value=value,
        increment=True,
    )


# --------------------------------------------------------------------------- #
# KPI data point helper
# --------------------------------------------------------------------------- #


async def _upsert_kpi_data_point(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    kpi_code: str,
    period: date,
    value: float,
    target: float | None = None,
    increment: bool = False,
) -> None:
    """写入或更新 KPI 数据点。increment=True 时累加而非覆盖。"""
    from sqlalchemy import select

    from packages.management_decision.models.kpi import KPIDataPoint

    stmt = select(KPIDataPoint).where(
        KPIDataPoint.tenant_id == tenant_id,
        KPIDataPoint.kpi_code == kpi_code,
        KPIDataPoint.period == period,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        if increment:
            existing.value += value
        else:
            existing.value = value
        if target is not None:
            existing.target = target
    else:
        dp = KPIDataPoint(
            id=uuid4(),
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            period=period,
            value=value,
            target=target,
        )
        session.add(dp)

    await session.flush()


# --------------------------------------------------------------------------- #
# Redis Streams consumer loop
# --------------------------------------------------------------------------- #


async def consume_stream(
    stream: str,
    group: str = "mgmt-bi",
    consumer_name: str = "worker-1",
) -> None:
    """持续消费一个 Redis Stream。生产环境由 worker 进程启动。"""
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        logger.warning("REDIS_URL not set, stream consumer %s disabled", stream)
        return

    import redis.asyncio as aioredis

    r = aioredis.from_url(redis_url)

    # 创建 consumer group (如果不存在)
    try:
        await r.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception:
        pass  # group already exists

    from packages.shared.db.base import get_sessionmaker

    sm = get_sessionmaker()
    logger.info("Stream consumer started: %s / %s / %s", stream, group, consumer_name)

    while True:
        try:
            messages = await r.xreadgroup(
                group, consumer_name, {stream: ">"}, count=10, block=5000
            )
            if not messages:
                continue

            for _, entries in messages:
                for msg_id, fields in entries:
                    event_type = (
                        fields.get(b"event_type") or fields.get("event_type", b"")
                    )
                    if isinstance(event_type, bytes):
                        event_type = event_type.decode()

                    payload_raw = fields.get(b"payload") or fields.get("payload", b"{}")
                    if isinstance(payload_raw, bytes):
                        payload_raw = payload_raw.decode()

                    try:
                        event_data = json.loads(payload_raw)
                    except json.JSONDecodeError:
                        event_data = {}

                    event_data.setdefault("event_type", event_type)

                    async with sm() as session:
                        try:
                            count = await dispatch(event_type, event_data, session)
                            await session.commit()
                            if count > 0:
                                logger.info(
                                    "Processed %s: %d handlers", event_type, count
                                )
                        except Exception:
                            await session.rollback()
                            logger.exception("Failed processing %s", event_type)

                    # ACK
                    await r.xack(stream, group, msg_id)

        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Stream consumer %s error, retrying in 5s...", stream)
            await asyncio.sleep(5)

    await r.aclose()


async def start_all_consumers() -> None:
    """启动全部 stream consumer (生产环境入口)。"""
    tasks = []
    for stream in STREAM_EVENTS:
        group = f"mgmt-bi-{stream}"
        tasks.append(asyncio.create_task(consume_stream(stream, group=group)))
    await asyncio.gather(*tasks)
