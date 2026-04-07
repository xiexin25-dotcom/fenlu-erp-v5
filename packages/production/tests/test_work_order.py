"""TASK-MFG-001 · WorkOrder model test."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import WorkOrder


@pytest.mark.asyncio
async def test_create_work_order(db_session: AsyncSession) -> None:
    """Insert a WorkOrder row and verify all fields round-trip correctly."""
    # 需要先建一个 tenant (FK 约束)
    from packages.shared.models import Tenant

    tenant = Tenant(code="test-mfg", name="Test Factory")
    db_session.add(tenant)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    wo = WorkOrder(
        tenant_id=tenant.id,
        order_no="WO-2026-0001",
        product_id=uuid4(),
        bom_id=uuid4(),
        routing_id=uuid4(),
        planned_quantity=Decimal("100.0000"),
        planned_quantity_uom="pcs",
        completed_quantity=Decimal("0"),
        completed_quantity_uom="pcs",
        scrap_quantity=Decimal("0"),
        scrap_quantity_uom="pcs",
        status="planned",
        planned_start=now,
        planned_end=now,
    )
    db_session.add(wo)
    await db_session.flush()

    assert wo.id is not None
    assert wo.order_no == "WO-2026-0001"
    assert wo.status == "planned"
    assert wo.planned_quantity == Decimal("100.0000")
    assert wo.tenant_id == tenant.id
    assert wo.actual_start is None
    assert wo.sales_order_id is None
