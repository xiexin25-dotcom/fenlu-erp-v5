"""Tests for event consumers (TASK-MGMT-008).

Tests the handler registry, dispatch mechanism, and concrete handlers
that create AR/AP records and write KPI data points from upstream events.
All tests use the in-memory SQLite DB — no Redis needed.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.ap_ar import APRecord, ARRecord
from packages.management_decision.models.kpi import KPIDataPoint
from packages.management_decision.services.event_consumer import (
    STREAM_EVENTS,
    dispatch,
    get_all_handlers,
    get_handlers,
)
from packages.shared.contracts.events import EventType


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


class TestHandlerRegistry:
    def test_handlers_registered_for_key_events(self) -> None:
        """所有关键事件类型都有 handler 注册。"""
        expected = [
            EventType.SALES_ORDER_CONFIRMED,
            EventType.PURCHASE_ORDER_APPROVED,
            EventType.OEE_CALCULATED,
            EventType.QC_FAILED,
            EventType.HAZARD_REPORTED,
            EventType.ENERGY_THRESHOLD_BREACHED,
            EventType.WORK_ORDER_COMPLETED,
        ]
        for et in expected:
            handlers = get_handlers(str(et))
            assert len(handlers) >= 1, f"No handler for {et}"

    def test_stream_events_map_complete(self) -> None:
        """STREAM_EVENTS 包含 plm/scm/mfg 三个 stream。"""
        assert "plm-events" in STREAM_EVENTS
        assert "scm-events" in STREAM_EVENTS
        assert "mfg-events" in STREAM_EVENTS

    def test_all_handler_names(self) -> None:
        """确认具体 handler 函数已注册。"""
        all_h = get_all_handlers()
        names = {h.__name__ for handlers in all_h.values() for h in handlers}
        assert "handle_sales_order_confirmed" in names
        assert "handle_purchase_order_approved" in names
        assert "handle_oee_calculated" in names
        assert "handle_qc_failed" in names
        assert "handle_hazard_reported" in names


# --------------------------------------------------------------------------- #
# Dispatch + AR from SalesOrderConfirmed
# --------------------------------------------------------------------------- #


class TestSalesOrderHandler:
    @pytest.mark.asyncio
    async def test_creates_ar_record(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        tid = seed_admin["tenant_id"]
        event_data = {
            "event_id": str(uuid4()),
            "event_type": EventType.SALES_ORDER_CONFIRMED,
            "tenant_id": str(tid),
            "sales_order_id": str(uuid4()),
            "customer_id": str(uuid4()),
            "total_amount": {"amount": "50000.0000", "currency": "CNY"},
        }

        count = await dispatch(EventType.SALES_ORDER_CONFIRMED, event_data, db_session)
        assert count == 1
        await db_session.commit()

        result = await db_session.execute(
            select(ARRecord).where(ARRecord.tenant_id == tid)
        )
        ar = result.scalar_one()
        assert ar.total_amount == Decimal("50000.0000")
        assert "自动创建" in (ar.memo or "")


# --------------------------------------------------------------------------- #
# Dispatch + AP from PurchaseOrderApproved
# --------------------------------------------------------------------------- #


class TestPurchaseOrderHandler:
    @pytest.mark.asyncio
    async def test_creates_ap_record(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        tid = seed_admin["tenant_id"]
        event_data = {
            "event_id": str(uuid4()),
            "event_type": EventType.PURCHASE_ORDER_APPROVED,
            "tenant_id": str(tid),
            "purchase_order_id": str(uuid4()),
            "supplier_id": str(uuid4()),
            "total_amount": {"amount": "30000.0000", "currency": "CNY"},
        }

        count = await dispatch(EventType.PURCHASE_ORDER_APPROVED, event_data, db_session)
        assert count == 1
        await db_session.commit()

        result = await db_session.execute(
            select(APRecord).where(APRecord.tenant_id == tid)
        )
        ap = result.scalar_one()
        assert ap.total_amount == Decimal("30000.0000")


# --------------------------------------------------------------------------- #
# KPI data point handlers
# --------------------------------------------------------------------------- #


class TestOEEHandler:
    @pytest.mark.asyncio
    async def test_writes_oee_kpi(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        tid = seed_admin["tenant_id"]
        event_data = {
            "tenant_id": str(tid),
            "oee_value": 85.5,
        }

        await dispatch(EventType.OEE_CALCULATED, event_data, db_session)
        await db_session.commit()

        result = await db_session.execute(
            select(KPIDataPoint).where(
                KPIDataPoint.tenant_id == tid,
                KPIDataPoint.kpi_code == "OPS-001",
            )
        )
        dp = result.scalar_one()
        assert dp.value == 85.5

    @pytest.mark.asyncio
    async def test_oee_upsert_overwrites(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        """同一天两次 OEE 事件 → 覆盖 (非累加)。"""
        tid = seed_admin["tenant_id"]
        for val in [80.0, 90.0]:
            await dispatch(
                EventType.OEE_CALCULATED,
                {"tenant_id": str(tid), "oee_value": val},
                db_session,
            )
        await db_session.commit()

        result = await db_session.execute(
            select(KPIDataPoint).where(
                KPIDataPoint.tenant_id == tid,
                KPIDataPoint.kpi_code == "OPS-001",
            )
        )
        dp = result.scalar_one()
        assert dp.value == 90.0  # latest wins


class TestHazardHandler:
    @pytest.mark.asyncio
    async def test_hazard_increments(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        """多次隐患上报 → 累加。"""
        tid = seed_admin["tenant_id"]
        for _ in range(3):
            await dispatch(
                EventType.HAZARD_REPORTED,
                {"tenant_id": str(tid)},
                db_session,
            )
        await db_session.commit()

        result = await db_session.execute(
            select(KPIDataPoint).where(
                KPIDataPoint.tenant_id == tid,
                KPIDataPoint.kpi_code == "SAF-001",
            )
        )
        dp = result.scalar_one()
        assert dp.value == 3.0


class TestQCFailedHandler:
    @pytest.mark.asyncio
    async def test_writes_defect_rate(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        tid = seed_admin["tenant_id"]
        event_data = {
            "tenant_id": str(tid),
            "defect_count": 5,
            "sample_size": 100,
        }
        await dispatch(EventType.QC_FAILED, event_data, db_session)
        await db_session.commit()

        result = await db_session.execute(
            select(KPIDataPoint).where(
                KPIDataPoint.tenant_id == tid,
                KPIDataPoint.kpi_code == "QUA-003",
            )
        )
        dp = result.scalar_one()
        assert dp.value == pytest.approx(5.0)  # 5/100 * 100 = 5%


class TestWorkOrderCompletedHandler:
    @pytest.mark.asyncio
    async def test_increments_daily_output(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        tid = seed_admin["tenant_id"]
        for qty in [100, 50, 75]:
            await dispatch(
                EventType.WORK_ORDER_COMPLETED,
                {
                    "tenant_id": str(tid),
                    "completed_quantity": {"value": str(qty), "uom": "pcs"},
                },
                db_session,
            )
        await db_session.commit()

        result = await db_session.execute(
            select(KPIDataPoint).where(
                KPIDataPoint.tenant_id == tid,
                KPIDataPoint.kpi_code == "OPS-003",
            )
        )
        dp = result.scalar_one()
        assert dp.value == 225.0  # 100 + 50 + 75


class TestEnergyHandler:
    @pytest.mark.asyncio
    async def test_writes_energy_kpi(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        tid = seed_admin["tenant_id"]
        await dispatch(
            EventType.ENERGY_THRESHOLD_BREACHED,
            {"tenant_id": str(tid), "actual": 12500.0},
            db_session,
        )
        await db_session.commit()

        result = await db_session.execute(
            select(KPIDataPoint).where(
                KPIDataPoint.tenant_id == tid,
                KPIDataPoint.kpi_code == "ENG-002",
            )
        )
        dp = result.scalar_one()
        assert dp.value == 12500.0
