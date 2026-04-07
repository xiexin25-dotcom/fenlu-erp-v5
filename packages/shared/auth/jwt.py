"""JWT 签发与验证。

Access Token: 30min, 用于 API 请求
Refresh Token: 14d, 用于换 access
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(minutes=int(os.getenv("JWT_ACCESS_TTL_MINUTES", "30")))
REFRESH_TTL = timedelta(days=int(os.getenv("JWT_REFRESH_TTL_DAYS", "14")))

TokenType = Literal["access", "refresh"]


def create_token(
    *,
    user_id: UUID,
    tenant_id: UUID,
    token_type: TokenType,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    ttl = ACCESS_TTL if token_type == "access" else REFRESH_TTL
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    if extra:
        payload.update(extra)
    encoded = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # PyJWT >=2 returns str, but type stub still says bytes in some versions
    return encoded if isinstance(encoded, str) else encoded.decode("utf-8")


def decode_token(token: str, expected_type: TokenType = "access") -> dict[str, Any]:
    """解码并验证 token,失败抛 jwt.PyJWTError 子类。"""
    payload: dict[str, Any] = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("typ") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token, got {payload.get('typ')}")
    return payload
