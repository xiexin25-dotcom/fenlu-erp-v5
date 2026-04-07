"""
SCM · 供应商服务层
==================

供应商 CRUD + tier 变更审批 (跨 Lane 4)。
"""

from __future__ import annotations

from uuid import UUID

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    SupplierCreate,
    SupplierListParams,
    SupplierRatingCreate,
    SupplierUpdate,
)
from packages.supply_chain.models.supplier import (
    Supplier,
    SupplierRating,
    SupplierTierChange,
)

# Lane 4 审批端点 (同一网关内)
_MGMT_APPROVAL_URL = "http://localhost:8004/mgmt/approval"


class SupplierService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    async def create_supplier(
        self, tenant_id: UUID, data: SupplierCreate,
    ) -> Supplier:
        supplier = Supplier(
            tenant_id=tenant_id,
            code=data.code,
            name=data.name,
            tier=data.tier.value,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            address=data.address,
            remark=data.remark,
        )
        self._session.add(supplier)
        await self._session.flush()
        return supplier

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #

    async def get_supplier(self, tenant_id: UUID, supplier_id: UUID) -> Supplier | None:
        stmt = select(Supplier).where(
            Supplier.tenant_id == tenant_id,
            Supplier.id == supplier_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_suppliers(
        self, tenant_id: UUID, params: SupplierListParams,
    ) -> tuple[list[Supplier], int]:
        base = select(Supplier).where(Supplier.tenant_id == tenant_id)

        if params.tier is not None:
            base = base.where(Supplier.tier == params.tier.value)
        if params.is_online is not None:
            base = base.where(Supplier.is_online == params.is_online)
        if params.search:
            pattern = f"%{params.search}%"
            base = base.where(
                or_(Supplier.code.ilike(pattern), Supplier.name.ilike(pattern)),
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        items_stmt = (
            base
            .order_by(Supplier.created_at.desc())
            .offset((params.page - 1) * params.size)
            .limit(params.size)
        )
        rows = (await self._session.execute(items_stmt)).scalars().all()
        return list(rows), total

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #

    async def update_supplier(
        self, tenant_id: UUID, supplier_id: UUID, data: SupplierUpdate,
    ) -> Supplier | None:
        supplier = await self.get_supplier(tenant_id, supplier_id)
        if supplier is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(supplier, field, value)

        await self._session.flush()
        return supplier

    # ------------------------------------------------------------------ #
    # Tier transition (需 Lane 4 审批)
    # ------------------------------------------------------------------ #

    async def request_tier_change(
        self,
        tenant_id: UUID,
        supplier_id: UUID,
        to_tier: str,
        reason: str | None,
        requested_by: UUID | None = None,
    ) -> SupplierTierChange:
        supplier = await self.get_supplier(tenant_id, supplier_id)
        if supplier is None:
            raise ValueError(f"Supplier {supplier_id} not found")

        if supplier.tier == to_tier:
            raise ValueError(f"Supplier already at tier {to_tier}")

        change = SupplierTierChange(
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            from_tier=supplier.tier,
            to_tier=to_tier,
            reason=reason,
            approval_status="pending",
            created_by=requested_by,
        )
        self._session.add(change)
        await self._session.flush()

        # 异步请求 Lane 4 审批 (fire-and-forget, 不阻塞当前事务)
        await self._request_mgmt_approval(change, tenant_id)

        return change

    async def _request_mgmt_approval(
        self, change: SupplierTierChange, tenant_id: UUID,
    ) -> None:
        """向 Lane 4 发起审批请求。失败不阻塞,记录 pending 即可。"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    _MGMT_APPROVAL_URL,
                    json={
                        "source_lane": "scm",
                        "document_type": "supplier_tier_change",
                        "document_id": str(change.id),
                        "tenant_id": str(tenant_id),
                        "title": f"供应商等级变更: {change.from_tier} → {change.to_tier}",
                        "detail": change.reason or "",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    change.approval_id = data.get("approval_id")
        except httpx.HTTPError:
            # Lane 4 不可用时降级为 pending,后续可通过回调补齐
            pass

    async def complete_tier_change(
        self,
        tenant_id: UUID,
        change_id: UUID,
        approved: bool,
    ) -> SupplierTierChange | None:
        """Lane 4 审批回调: 完成 tier 变更。"""
        stmt = select(SupplierTierChange).where(
            SupplierTierChange.tenant_id == tenant_id,
            SupplierTierChange.id == change_id,
            SupplierTierChange.approval_status == "pending",
        )
        result = await self._session.execute(stmt)
        change = result.scalar_one_or_none()
        if change is None:
            return None

        if approved:
            change.approval_status = "approved"
            # 更新供应商 tier
            supplier = await self.get_supplier(tenant_id, change.supplier_id)
            if supplier:
                supplier.tier = change.to_tier
                # 同步更新 rating_score 不在此处,由评分流程独立驱动
        else:
            change.approval_status = "rejected"

        await self._session.flush()
        return change

    # ------------------------------------------------------------------ #
    # Rating
    # ------------------------------------------------------------------ #

    async def add_rating(
        self,
        tenant_id: UUID,
        supplier_id: UUID,
        data: SupplierRatingCreate,
    ) -> SupplierRating:
        supplier = await self.get_supplier(tenant_id, supplier_id)
        if supplier is None:
            raise ValueError(f"Supplier {supplier_id} not found")

        rating = SupplierRating(
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            period_start=data.period_start,
            period_end=data.period_end,
            quality_score=data.quality_score,
            delivery_score=data.delivery_score,
            price_score=data.price_score,
            service_score=data.service_score,
            total_score=data.total_score,
        )
        self._session.add(rating)
        await self._session.flush()

        # 更新供应商主表的 rating_score 为最新评分
        supplier.rating_score = data.total_score
        await self._session.flush()

        return rating

    async def list_ratings(
        self, tenant_id: UUID, supplier_id: UUID,
    ) -> list[SupplierRating]:
        stmt = (
            select(SupplierRating)
            .where(
                SupplierRating.tenant_id == tenant_id,
                SupplierRating.supplier_id == supplier_id,
            )
            .order_by(SupplierRating.period_start.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
