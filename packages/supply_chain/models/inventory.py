"""
SCM · 库存 + 库存移动模型
=========================

核心规则: 所有库存变动必须通过 StockMove, 禁止直接 UPDATE Inventory。
Inventory 表由 InventoryService 通过 StockMove 驱动更新。

库存量定义:
  on_hand   = 物理在库总量
  reserved  = 已预留 (被工单/销售占用但未出库)
  in_transit = 在途 (采购已发货未入库)
  available = on_hand - reserved (可自由使用)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin

SCM_SCHEMA = "scm"


class Inventory(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """库存快照表 — 每个 (tenant, product, warehouse, batch) 一行。"""

    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "product_id", "warehouse_id", "batch_no",
            name="uq_inv_tenant_prod_wh_batch",
        ),
        Index("ix_inv_tenant_product", "tenant_id", "product_id"),
        Index("ix_inv_tenant_warehouse", "tenant_id", "warehouse_id"),
        {"schema": SCM_SCHEMA},
    )

    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    uom: Mapped[str] = mapped_column(String(8), nullable=False, default="pcs")
    batch_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    reserved: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    in_transit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)

    @property
    def available(self) -> Decimal:
        return self.on_hand - self.reserved


class StockMove(Base, UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin):
    """库存移动流水 — 不可变,每条记录代表一次库存变动。"""

    __tablename__ = "stock_moves"
    __table_args__ = (
        Index("ix_sm_tenant_product", "tenant_id", "product_id"),
        Index("ix_sm_tenant_type", "tenant_id", "type"),
        Index("ix_sm_reference", "reference_id"),
        {"schema": SCM_SCHEMA},
    )

    move_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(8), nullable=False, default="pcs")

    warehouse_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(f"{SCM_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    from_location: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_location: Mapped[str | None] = mapped_column(String(32), nullable=True)
    batch_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    reference_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True,
        comment="关联单据 ID (工单/采购单/销售单)",
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
