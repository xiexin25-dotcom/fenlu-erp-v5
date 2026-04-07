"""认证路由: 登录 / 刷新 / 当前用户 / 用户管理 / 角色管理。"""

from __future__ import annotations

from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from packages.shared.auth import (
    CurrentUser,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from packages.shared.db import get_session
from packages.shared.models import Role, User, UserRole
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ────────────────────────────────────────────────────────

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
    is_active: bool


class UserDetailOut(UserOut):
    roles: list[str] = []


class UserCreateRequest(BaseModel):
    username: str = Field(..., max_length=64)
    full_name: str = Field(..., max_length=128)
    password: str = Field(..., min_length=4, max_length=255)
    email: str | None = None
    is_superuser: bool = False
    role_ids: list[UUID] = []


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    password: str | None = None
    role_ids: list[UUID] | None = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    permissions: list


class RoleCreateRequest(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    permissions: list[list[str]] = []  # [["resource", "action"], ...]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID | None
    username: str | None
    method: str
    path: str
    status_code: int
    resource: str | None
    action: str | None
    detail: str | None
    ip_address: str | None
    created_at: str | None


# ── Auth ───────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
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


# ── User Management ───────────────────────────────────────────────

def _user_detail(user: User, roles: list[Role] | None = None) -> UserDetailOut:
    role_names = [r.name for r in roles] if roles else []
    return UserDetailOut(
        id=user.id, tenant_id=user.tenant_id, username=user.username,
        full_name=user.full_name, email=user.email,
        is_superuser=user.is_superuser, is_active=user.is_active,
        roles=role_names,
    )


@router.get("/users", response_model=list[UserDetailOut])
async def list_users(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[UserDetailOut]:
    result = await session.execute(
        select(User)
        .where(User.tenant_id == user.tenant_id)
        .order_by(User.username)
    )
    users = result.scalars().all()

    # Load roles for each user
    out = []
    for u in users:
        roles_result = await session.execute(
            select(Role).join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == u.id)
        )
        roles = list(roles_result.scalars().all())
        out.append(_user_detail(u, roles))
    return out


@router.post("/users", response_model=UserDetailOut, status_code=201)
async def create_user(
    body: UserCreateRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> UserDetailOut:
    if not user.is_superuser:
        raise HTTPException(403, "仅管理员可创建用户")

    # Check unique
    existing = await session.execute(
        select(User).where(User.tenant_id == user.tenant_id, User.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"用户名 {body.username} 已存在")

    new_user = User(
        id=uuid4(),
        tenant_id=user.tenant_id,
        username=body.username,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        email=body.email,
        is_superuser=body.is_superuser,
    )
    session.add(new_user)
    await session.flush()

    # Assign roles
    roles = []
    for rid in body.role_ids:
        role = await session.get(Role, rid)
        if role and role.tenant_id == user.tenant_id:
            session.add(UserRole(user_id=new_user.id, role_id=rid))
            roles.append(role)

    await session.commit()
    return _user_detail(new_user, roles)


@router.patch("/users/{user_id}", response_model=UserDetailOut)
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> UserDetailOut:
    if not user.is_superuser:
        raise HTTPException(403, "仅管理员可修改用户")

    target = await session.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, "用户不存在")

    if body.full_name is not None:
        target.full_name = body.full_name
    if body.email is not None:
        target.email = body.email
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.is_superuser is not None:
        target.is_superuser = body.is_superuser
    if body.password is not None:
        target.password_hash = hash_password(body.password)

    # Update roles
    if body.role_ids is not None:
        # Remove old
        old_roles = await session.execute(
            select(UserRole).where(UserRole.user_id == user_id)
        )
        for ur in old_roles.scalars().all():
            await session.delete(ur)
        # Add new
        for rid in body.role_ids:
            session.add(UserRole(user_id=user_id, role_id=rid))

    await session.commit()

    # Reload roles
    roles_result = await session.execute(
        select(Role).join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    roles = list(roles_result.scalars().all())
    return _user_detail(target, roles)


# ── Role Management ──────────────────────────────────────────────

@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[RoleOut]:
    result = await session.execute(
        select(Role).where(Role.tenant_id == user.tenant_id).order_by(Role.code)
    )
    return [RoleOut.model_validate(r) for r in result.scalars().all()]


@router.post("/roles", response_model=RoleOut, status_code=201)
async def create_role(
    body: RoleCreateRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> RoleOut:
    if not user.is_superuser:
        raise HTTPException(403, "仅管理员可创建角色")

    role = Role(
        id=uuid4(),
        tenant_id=user.tenant_id,
        code=body.code,
        name=body.name,
        permissions=body.permissions,
    )
    session.add(role)
    await session.commit()
    return RoleOut.model_validate(role)


# ── Audit Log ────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    resource: str | None = Query(None),
) -> list[AuditLogOut]:
    from packages.shared.models.audit_log import AuditLog

    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == user.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .offset(skip).limit(limit)
    )
    if resource:
        stmt = stmt.where(AuditLog.resource == resource)
    result = await session.execute(stmt)
    logs = result.scalars().all()

    # Resolve usernames
    user_ids = {l.user_id for l in logs if l.user_id}
    user_map: dict[UUID, str] = {}
    if user_ids:
        users_result = await session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        for u in users_result.scalars().all():
            user_map[u.id] = u.full_name

    out = []
    for l in logs:
        out.append(AuditLogOut(
            id=l.id, user_id=l.user_id,
            username=user_map.get(l.user_id) if l.user_id else None,
            method=l.method, path=l.path, status_code=l.status_code,
            resource=l.resource, action=l.action, detail=l.detail,
            ip_address=l.ip_address,
            created_at=l.created_at.isoformat() if l.created_at else None,
        ))
    return out
