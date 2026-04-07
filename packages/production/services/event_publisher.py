"""Redis Streams event publisher · TASK-MFG-004。

轻量封装: XADD 到 mfg-events stream。
测试时通过 dependency override 注入 FakePublisher。
"""

from __future__ import annotations

import os
from typing import Protocol

from packages.shared.contracts.events import BaseEvent

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MFG_STREAM = "mfg-events"


class EventPublisher(Protocol):
    async def publish(self, event: BaseEvent) -> None: ...


class RedisEventPublisher:
    """真实 Redis Streams 发布者。"""

    def __init__(self) -> None:
        self._redis: object | None = None

    async def _get_redis(self) -> object:
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    async def publish(self, event: BaseEvent) -> None:
        r = await self._get_redis()
        data = {k: str(v) for k, v in event.model_dump(mode="json").items() if v is not None}
        await r.xadd(MFG_STREAM, data)  # type: ignore[union-attr]

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()  # type: ignore[union-attr]
            self._redis = None


class FakeEventPublisher:
    """测试用: 收集已发布事件,不连 Redis。"""

    def __init__(self) -> None:
        self.events: list[BaseEvent] = []

    async def publish(self, event: BaseEvent) -> None:
        self.events.append(event)
