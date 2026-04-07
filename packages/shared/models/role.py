"""Role - 角色与权限 (对应原系统"权限设置")。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from packages.shared.db import Base, TenantMixin, TimestampMixin, UUIDPKMixin


class Role(Base, UUIDPKMixin, TenantMixin, TimestampMixin):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),
        {"schema": "public"},
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Casbin 风格策略 list[ [resource, action] ]
    # postgres 用 JSONB (可索引), 其他方言降级到 JSON (主要为测试)
    permissions: Mapped[list[list[str]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        default=list,
        nullable=False,
    )


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "public"}

    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("public.roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
