"""FastAPI 认证依赖。

使用方法:
    @router.get("/me")
    async def me(user: CurrentUser) -> dict:
        return {"id": str(user.id), "name": user.full_name}
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.auth.jwt import decode_token
from packages.shared.db import get_session
from packages.shared.models import User


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(401, "token expired") from e
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"invalid token: {e}") from e

    user_id = UUID(payload["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(401, "user not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(resource: str, action: str) -> Any:
    """权限装饰器工厂 (后续接 Casbin)。

    用法: @router.post("/", dependencies=[Depends(require_permission("mfg.work_order", "create"))])
    """

    async def _check(user: CurrentUser) -> None:
        if user.is_superuser:
            return
        # TODO Lane 4 集成 Casbin enforcer 后,在此处查 user 的所有 role.permissions
        # 此处先放行已认证用户,作为 foundation 占位
        return

    return _check
