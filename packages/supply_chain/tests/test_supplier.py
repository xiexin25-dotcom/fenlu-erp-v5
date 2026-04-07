"""Tests for SCM Supplier models, service, and API."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.supply_chain.api.schemas import (
    SupplierCreate,
    SupplierListParams,
    SupplierRatingCreate,
    SupplierUpdate,
)
from packages.supply_chain.models.supplier import Supplier, SupplierTierChange
from packages.supply_chain.services.supplier_service import SupplierService


@pytest_asyncio.fixture
async def tenant_id(db_session: AsyncSession) -> ...:
    """Create a tenant and return its id."""
    from packages.shared.models import Tenant

    t = Tenant(code="test", name="Test Co")
    db_session.add(t)
    await db_session.flush()
    return t.id


@pytest_asyncio.fixture
async def svc(db_session: AsyncSession) -> SupplierService:
    return SupplierService(db_session)


@pytest_asyncio.fixture
async def sample_supplier(svc: SupplierService, tenant_id) -> Supplier:
    return await svc.create_supplier(
        tenant_id,
        SupplierCreate(code="SUP-001", name="Acme Corp"),
    )


# ------------------------------------------------------------------ #
# Model basics
# ------------------------------------------------------------------ #


class TestSupplierModel:
    @pytest.mark.asyncio
    async def test_create_supplier(self, svc: SupplierService, tenant_id) -> None:
        s = await svc.create_supplier(
            tenant_id,
            SupplierCreate(code="SUP-001", name="Test Supplier"),
        )
        assert s.code == "SUP-001"
        assert s.name == "Test Supplier"
        assert s.tier == "approved"
        assert s.rating_score == 0.0
        assert s.is_online is True

    @pytest.mark.asyncio
    async def test_get_supplier(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        found = await svc.get_supplier(tenant_id, sample_supplier.id)
        assert found is not None
        assert found.code == "SUP-001"

    @pytest.mark.asyncio
    async def test_get_supplier_wrong_tenant(self, svc: SupplierService, sample_supplier) -> None:
        found = await svc.get_supplier(uuid4(), sample_supplier.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_list_suppliers(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        items, total = await svc.list_suppliers(tenant_id, SupplierListParams())
        assert total == 1
        assert items[0].code == "SUP-001"

    @pytest.mark.asyncio
    async def test_list_filter_by_tier(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        from packages.shared.contracts.supply_chain import SupplierTier

        items, total = await svc.list_suppliers(
            tenant_id, SupplierListParams(tier=SupplierTier.APPROVED),
        )
        assert total == 1

        items, total = await svc.list_suppliers(
            tenant_id, SupplierListParams(tier=SupplierTier.STRATEGIC),
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_search(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        items, total = await svc.list_suppliers(
            tenant_id, SupplierListParams(search="acme"),
        )
        assert total == 1

        items, total = await svc.list_suppliers(
            tenant_id, SupplierListParams(search="nonexistent"),
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_update_supplier(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        updated = await svc.update_supplier(
            tenant_id, sample_supplier.id, SupplierUpdate(name="Acme Updated"),
        )
        assert updated is not None
        assert updated.name == "Acme Updated"
        assert updated.code == "SUP-001"  # unchanged


# ------------------------------------------------------------------ #
# Tier transitions
# ------------------------------------------------------------------ #


class TestTierTransition:
    @pytest.mark.asyncio
    async def test_request_tier_change(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        change = await svc.request_tier_change(
            tenant_id, sample_supplier.id, "strategic", "Performance upgrade",
        )
        assert change.from_tier == "approved"
        assert change.to_tier == "strategic"
        assert change.approval_status == "pending"
        assert change.reason == "Performance upgrade"

    @pytest.mark.asyncio
    async def test_tier_change_same_tier_raises(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        with pytest.raises(ValueError, match="already at tier"):
            await svc.request_tier_change(tenant_id, sample_supplier.id, "approved", None)

    @pytest.mark.asyncio
    async def test_tier_change_not_found(self, svc: SupplierService, tenant_id) -> None:
        with pytest.raises(ValueError, match="not found"):
            await svc.request_tier_change(tenant_id, uuid4(), "strategic", None)

    @pytest.mark.asyncio
    async def test_approve_tier_change(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        change = await svc.request_tier_change(
            tenant_id, sample_supplier.id, "strategic", "Upgrade",
        )
        result = await svc.complete_tier_change(tenant_id, change.id, approved=True)
        assert result is not None
        assert result.approval_status == "approved"

        # supplier tier should be updated
        supplier = await svc.get_supplier(tenant_id, sample_supplier.id)
        assert supplier is not None
        assert supplier.tier == "strategic"

    @pytest.mark.asyncio
    async def test_reject_tier_change(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        change = await svc.request_tier_change(
            tenant_id, sample_supplier.id, "blacklisted", "Bad quality",
        )
        result = await svc.complete_tier_change(tenant_id, change.id, approved=False)
        assert result is not None
        assert result.approval_status == "rejected"

        # supplier tier should NOT change
        supplier = await svc.get_supplier(tenant_id, sample_supplier.id)
        assert supplier is not None
        assert supplier.tier == "approved"


# ------------------------------------------------------------------ #
# Rating
# ------------------------------------------------------------------ #


class TestSupplierRating:
    @pytest.mark.asyncio
    async def test_add_rating(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        rating = await svc.add_rating(
            tenant_id,
            sample_supplier.id,
            SupplierRatingCreate(
                period_start=date(2026, 1, 1),
                period_end=date(2026, 3, 31),
                quality_score=85.0,
                delivery_score=90.0,
                price_score=75.0,
                service_score=80.0,
                total_score=82.5,
            ),
        )
        assert rating.total_score == 82.5
        assert rating.supplier_id == sample_supplier.id

        # supplier rating_score should be updated
        supplier = await svc.get_supplier(tenant_id, sample_supplier.id)
        assert supplier is not None
        assert supplier.rating_score == 82.5

    @pytest.mark.asyncio
    async def test_list_ratings(self, svc: SupplierService, tenant_id, sample_supplier) -> None:
        await svc.add_rating(
            tenant_id,
            sample_supplier.id,
            SupplierRatingCreate(
                period_start=date(2026, 1, 1),
                period_end=date(2026, 3, 31),
                quality_score=80, delivery_score=80,
                price_score=80, service_score=80, total_score=80,
            ),
        )
        ratings = await svc.list_ratings(tenant_id, sample_supplier.id)
        assert len(ratings) == 1

    @pytest.mark.asyncio
    async def test_add_rating_not_found(self, svc: SupplierService, tenant_id) -> None:
        with pytest.raises(ValueError, match="not found"):
            await svc.add_rating(
                tenant_id,
                uuid4(),
                SupplierRatingCreate(
                    period_start=date(2026, 1, 1),
                    period_end=date(2026, 3, 31),
                    quality_score=80, delivery_score=80,
                    price_score=80, service_score=80, total_score=80,
                ),
            )
