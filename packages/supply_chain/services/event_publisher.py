"""
SCM · Redis Streams 事件发布器
==============================

将事件写入 scm-events stream,供 Lane 4 (mgmt) 和 BI 消费。
生产环境用 Redis,测试时可注入 InMemoryPublisher。
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SCM_STREAM = "scm-events"


class EventPublisher(Protocol):
    async def publish(self, event_type: str, payload: dict[str, Any]) -> None: ...


class RedisEventPublisher:
    """通过 Redis XADD 发布事件。"""

    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self._redis_url = redis_url
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        client = await self._get_client()
        await client.xadd(
            SCM_STREAM,
            {"event_type": event_type, "payload": json.dumps(payload, default=str)},
        )


class InMemoryPublisher:
    """测试用: 把事件存到内存列表。"""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))
