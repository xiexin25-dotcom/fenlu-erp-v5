"""Organization - 组织机构 (对应原系统"基础数据-组织机构")。

支持自引用树形:总公司 → 分公司 → 部门 → 班组。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import Base, TenantMixin, TimestampMixin, UUIDPKMixin


class OrganizationType(Base, UUIDPKMixin, TenantMixin, TimestampMixin):
    """组织类型: 总公司/分公司/部门/工会/班组 (原系统 1.1)。"""

    __tablename__ = "organization_types"
    __table_args__ = {"schema": "public"}

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Organization(Base, UUIDPKMixin, TenantMixin, TimestampMixin):
    """组织机构 (原系统 1.2)。"""

    __tablename__ = "organizations"
    __table_args__ = {"schema": "public"}

    parent_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("public.organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    type_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("public.organization_types.id"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    leader_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
