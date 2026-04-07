"""PLM event publisher — Redis Streams.

Stream: plm-events
"""

from __future__ import annotations

import json
import os
from typing import Any

import redis.asyncio as aioredis

STREAM_NAME = "plm-events"

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
    return _redis


async def publish_event(event_data: dict[str, Any]) -> str:
    """发布事件到 plm-events stream,返回 stream entry ID。"""
    r = get_redis()
    # Redis XADD: field values must be strings
    payload = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in event_data.items()}
    entry_id: Any = await r.xadd(STREAM_NAME, payload)
    return str(entry_id)
