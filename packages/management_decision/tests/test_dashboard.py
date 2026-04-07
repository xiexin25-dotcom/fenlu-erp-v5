"""Tests for executive dashboard (TASK-MGMT-010)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.ap_ar import APRecord, APStatus, ARRecord
from packages.management_decision.models.kpi import KPIDataPoint


# --------------------------------------------------------------------------- #
# Seed helpers
# --------------------------------------------------------------------------- #


async def _seed_data(session: AsyncSession, tenant_id: Any) -> None:
    """Seed AR, AP, KPI data points for dashboard test."""
    today = date.today()

    # AR records
    for amount in ["50000", "30000"]:
        session.add(
            ARRecord(
                id=uuid4(),
                tenant_id=tenant_id,
                sales_order_id=uuid4(),
                customer_id=uuid4(),
                total_amount=Decimal(amount),
                received_amount=Decimal("10000"),
                currency="CNY",
                due_date=today + timedelta(days=30),
                status=APStatus.PARTIAL,
            )
        )

    # AP records
    session.add(
        APRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            purchase_order_id=uuid4(),
            supplier_id=uuid4(),
            total_amount=Decimal("40000"),
            paid_amount=Decimal("15000"),
            currency="CNY",
            due_date=today + timedelta(days=30),
            status=APStatus.PARTIAL,
        )
    )

    # KPI data points
    kpis = [
        ("OPS-003", today, 500),
        ("OPS-003", today - timedelta(days=1), 450),
        ("OPS-001", today, 87.5),
        ("OPS-001", today - timedelta(days=1), 85.0),
        ("OPS-002", today, 92.0),
        ("SAF-001", today, 3),
        ("SAF-002", today, 70.0),
        ("SAF-003", today, 45),
        ("ENG-002", today, 12000),
        ("ENG-002", today - timedelta(days=1), 11500),
        ("ENG-002", today - timedelta(days=2), 11800),
        ("ENG-001", today, 0.85),
        ("ENG-003", today, 2.4),
    ]
    for code, period, value in kpis:
        session.add(
            KPIDataPoint(
                id=uuid4(),
                tenant_id=tenant_id,
                kpi_code=code,
                period=period,
                value=value,
            )
        )

    await session.flush()


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


class TestExecDashboardAPI:
    def test_empty_dashboard(self, auth_client: TestClient) -> None:
        """无数据时也不报错,返回零值结构。"""
        r = auth_client.get("/mgmt/bi/dashboards/exec")
        assert r.status_code == 200, r.text
        data = r.json()

        assert "as_of" in data
        assert "revenue" in data
        assert "production" in data
        assert "safety" in data
        assert "energy" in data
        assert "cash" in data

    def test_dashboard_structure(self, auth_client: TestClient) -> None:
        """验证返回结构完整性。"""
        r = auth_client.get("/mgmt/bi/dashboards/exec")
        data = r.json()

        # Revenue section
        rev = data["revenue"]
        assert "today" in rev
        assert "month_to_date" in rev
        assert "ar_balance" in rev
        assert rev["unit"] == "CNY"

        # Production section
        prod = data["production"]
        assert "weekly_output" in prod
        assert "oee_avg" in prod
        assert "ontime_rate" in prod

        # Safety section
        safe = data["safety"]
        assert "total_hazards" in safe
        assert "closure_rate" in safe
        assert "consecutive_safe_days" in safe

        # Energy section
        eng = data["energy"]
        assert "daily_trend" in eng
        assert isinstance(eng["daily_trend"], list)
        assert "unit_consumption" in eng
        assert "per_piece_energy" in eng

        # Cash section
        cash = data["cash"]
        assert "net_cash_flow" in cash
        assert "month_received" in cash
        assert "month_paid" in cash
        assert "ap_due" in cash


class TestExecDashboardWithData:
    @pytest.mark.asyncio
    async def test_dashboard_values(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        """Seed 数据后验证 dashboard 各项数值正确。"""
        from packages.management_decision.services.dashboard import (
            get_executive_dashboard,
        )

        tid = seed_admin["tenant_id"]
        await _seed_data(db_session, tid)
        await db_session.commit()

        data = await get_executive_dashboard(db_session, tenant_id=tid)

        # Revenue: 50000 + 30000 = 80000
        assert data["revenue"]["month_to_date"] == 80000.0
        # AR balance: (50000-10000) + (30000-10000) = 60000
        assert data["revenue"]["ar_balance"] == 60000.0

        # Production: 500 + 450 this week (if both in this week)
        assert data["production"]["weekly_output"] >= 500
        # OEE avg
        assert data["production"]["oee_avg"] > 0

        # Safety
        assert data["safety"]["total_hazards"] == 3
        assert data["safety"]["closure_rate"] == 70.0
        assert data["safety"]["consecutive_safe_days"] == 45

        # Energy trend has data points
        assert len(data["energy"]["daily_trend"]) >= 1
        assert data["energy"]["unit_consumption"] == 0.85
        assert data["energy"]["per_piece_energy"] == 2.4

        # Cash: received=20000 (2×10000), paid=15000, net=5000
        assert data["cash"]["month_received"] == 20000.0
        assert data["cash"]["month_paid"] == 15000.0
        assert data["cash"]["net_cash_flow"] == 5000.0
        # AP due: 40000 - 15000 = 25000
        assert data["cash"]["ap_due"] == 25000.0

    @pytest.mark.asyncio
    async def test_energy_trend_ordering(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        """能耗趋势数据按日期升序排列。"""
        from packages.management_decision.services.dashboard import (
            get_executive_dashboard,
        )

        tid = seed_admin["tenant_id"]
        await _seed_data(db_session, tid)
        await db_session.commit()

        data = await get_executive_dashboard(db_session, tenant_id=tid)
        trend = data["energy"]["daily_trend"]
        if len(trend) >= 2:
            dates = [t["date"] for t in trend]
            assert dates == sorted(dates)
