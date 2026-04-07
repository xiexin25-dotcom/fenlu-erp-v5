"""认证路由: 登录 / 刷新 / 当前用户。"""

from __future__ import annotations

from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException
from packages.shared.auth import (
    CurrentUser,
    create_token,
    decode_token,
    verify_password,
)
from packages.shared.db import get_session
from packages.shared.models import User
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    tenant_code: str = Field(..., max_length=64)
    username: str = Field(..., max_length=64)
    password: str = Field(..., min_length=1, max_length=255)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    username: str
    full_name: str
    email: str | None
    is_superuser: bool


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    # 通过 tenant_code + username 联合定位用户
    from packages.shared.models import Tenant

    tenant = (
        await session.execute(select(Tenant).where(Tenant.code == body.tenant_code))
    ).scalar_one_or_none()
    if tenant is None or not tenant.is_active:
        raise HTTPException(401, "invalid credentials")

    user = (
        await session.execute(
            select(User).where(
                User.tenant_id == tenant.id,
                User.username == body.username,
            )
        )
    ).scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")

    return TokenPair(
        access_token=create_token(user_id=user.id, tenant_id=user.tenant_id, token_type="access"),
        refresh_token=create_token(user_id=user.id, tenant_id=user.tenant_id, token_type="refresh"),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"invalid refresh token: {e}") from e

    user_id = UUID(payload["sub"])
    tenant_id = UUID(payload["tid"])
    return TokenPair(
        access_token=create_token(user_id=user_id, tenant_id=tenant_id, token_type="access"),
        refresh_token=create_token(user_id=user_id, tenant_id=tenant_id, token_type="refresh"),
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
