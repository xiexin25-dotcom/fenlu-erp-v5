"""
SCM · 仓库 + 库位模型
=====================

库位 4 级层次: warehouse → zone → aisle → bin
通过 parent_id 自引用实现树形结构,level 枚举约束层级。
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin

SCM_SCHEMA = "scm"


class Warehouse(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """仓库主表。"""

    __tablename__ = "warehouses"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_wh_tenant_code"),
        {"schema": SCM_SCHEMA},
    )

    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    manager_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    locations: Mapped[list[Location]] = relationship(
        back_populates="warehouse",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="Location.warehouse_id",
    )


class LocationLevel(StrEnum):
    ZONE = "zone"
    AISLE = "aisle"
    BIN = "bin"


class Location(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """库位 (zone / aisle / bin)。

    层级规则:
      - zone  的 parent_id 为 NULL (直属仓库)
      - aisle 的 parent_id 指向 zone
      - bin   的 parent_id 指向 aisle
    """

    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_id", "code", name="uq_loc_tenant_wh_code"),
        Index("ix_loc_tenant_warehouse", "tenant_id", "warehouse_id"),
        Index("ix_loc_parent", "parent_id"),
        {"schema": SCM_SCHEMA},
    )

    warehouse_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.warehouses.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(8), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.locations.id", ondelete="CASCADE"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="库位容量(件)")

    warehouse: Mapped[Warehouse] = relationship(
        back_populates="locations", foreign_keys=[warehouse_id],
    )
    children: Mapped[list[Location]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    parent: Mapped[Location | None] = relationship(
        back_populates="children",
        remote_side="Location.id",
        lazy="selectin",
    )


# 层级 parent 校验规则
VALID_PARENT_LEVEL: dict[str, str | None] = {
    "zone": None,       # zone 直属仓库,parent_id = NULL
    "aisle": "zone",    # aisle 挂在 zone 下
    "bin": "aisle",     # bin 挂在 aisle 下
}


def validate_location_hierarchy(
    level: str,
    parent: Location | None,
) -> None:
    """校验库位层级关系。"""
    expected_parent = VALID_PARENT_LEVEL.get(level)
    if expected_parent is None and parent is not None:
        raise ValueError(f"Location level '{level}' must not have a parent (zone is top-level)")
    if expected_parent is not None and parent is None:
        raise ValueError(f"Location level '{level}' requires a parent of level '{expected_parent}'")
    if expected_parent is not None and parent is not None and parent.level != expected_parent:
        raise ValueError(
            f"Location level '{level}' requires parent level '{expected_parent}', "
            f"got '{parent.level}'"
        )
