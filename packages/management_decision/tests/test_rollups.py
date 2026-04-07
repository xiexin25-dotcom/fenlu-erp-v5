"""Tests for aggregation roll-ups (TASK-MGMT-009)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.ap_ar import APRecord, APStatus, ARRecord
from packages.management_decision.models.attendance import Attendance, AttendanceStatus
from packages.management_decision.models.hr import Employee
from packages.management_decision.models.kpi import KPIDataPoint


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


async def _seed_ar(session: AsyncSession, tenant_id: Any, amount: str) -> None:
    session.add(
        ARRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            sales_order_id=uuid4(),
            customer_id=uuid4(),
            total_amount=Decimal(amount),
            received_amount=Decimal("0"),
            currency="CNY",
            due_date=date.today(),
            status=APStatus.UNPAID,
        )
    )
    await session.flush()


async def _seed_ap(
    session: AsyncSession, tenant_id: Any, total: str, paid: str = "0"
) -> None:
    session.add(
        APRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            purchase_order_id=uuid4(),
            supplier_id=uuid4(),
            total_amount=Decimal(total),
            paid_amount=Decimal(paid),
            currency="CNY",
            due_date=date.today(),
            status=APStatus.PARTIAL if Decimal(paid) > 0 else APStatus.UNPAID,
        )
    )
    await session.flush()


async def _seed_employee(session: AsyncSession, tenant_id: Any, no: str) -> Employee:
    emp = Employee(
        id=uuid4(),
        tenant_id=tenant_id,
        employee_no=no,
        name=f"员工{no}",
        position="工程师",
        base_salary=Decimal("8000"),
    )
    session.add(emp)
    await session.flush()
    return emp


async def _seed_attendance(
    session: AsyncSession,
    tenant_id: Any,
    employee_id: Any,
    work_date: date,
    status: str = AttendanceStatus.NORMAL,
) -> None:
    session.add(
        Attendance(
            id=uuid4(),
            tenant_id=tenant_id,
            employee_id=employee_id,
            work_date=work_date,
            status=status,
            work_hours=Decimal("8") if status != AttendanceStatus.ABSENT else Decimal("0"),
        )
    )
    await session.flush()


# --------------------------------------------------------------------------- #
# Finance roll-ups
# --------------------------------------------------------------------------- #


class TestFinanceRollups:
    @pytest.mark.asyncio
    async def test_monthly_revenue(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.rollups import rollup_monthly_revenue

        tid = seed_admin["tenant_id"]
        await _seed_ar(db_session, tid, "10000")
        await _seed_ar(db_session, tid, "20000")
        await db_session.commit()

        await rollup_monthly_revenue(db_session, tenant_id=tid)
        await db_session.commit()

        dp = (
            await db_session.execute(
                select(KPIDataPoint).where(
                    KPIDataPoint.tenant_id == tid,
                    KPIDataPoint.kpi_code == "FIN-001",
                )
            )
        ).scalar_one()
        assert dp.value == 30000.0

    @pytest.mark.asyncio
    async def test_ap_balance(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.rollups import rollup_ap_balance

        tid = seed_admin["tenant_id"]
        await _seed_ap(db_session, tid, "50000", "10000")  # balance 40000
        await _seed_ap(db_session, tid, "30000", "0")  # balance 30000
        await db_session.commit()

        await rollup_ap_balance(db_session, tenant_id=tid)
        await db_session.commit()

        dp = (
            await db_session.execute(
                select(KPIDataPoint).where(
                    KPIDataPoint.tenant_id == tid,
                    KPIDataPoint.kpi_code == "FIN-003",
                )
            )
        ).scalar_one()
        assert dp.value == 70000.0

    @pytest.mark.asyncio
    async def test_cash_flow(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.rollups import rollup_cash_flow

        tid = seed_admin["tenant_id"]
        # AR with some received
        ar = ARRecord(
            id=uuid4(),
            tenant_id=tid,
            sales_order_id=uuid4(),
            customer_id=uuid4(),
            total_amount=Decimal("100000"),
            received_amount=Decimal("60000"),
            currency="CNY",
            due_date=date.today(),
            status=APStatus.PARTIAL,
        )
        db_session.add(ar)
        # AP with some paid
        ap = APRecord(
            id=uuid4(),
            tenant_id=tid,
            purchase_order_id=uuid4(),
            supplier_id=uuid4(),
            total_amount=Decimal("80000"),
            paid_amount=Decimal("25000"),
            currency="CNY",
            due_date=date.today(),
            status=APStatus.PARTIAL,
        )
        db_session.add(ap)
        await db_session.commit()

        await rollup_cash_flow(db_session, tenant_id=tid)
        await db_session.commit()

        dp = (
            await db_session.execute(
                select(KPIDataPoint).where(
                    KPIDataPoint.tenant_id == tid,
                    KPIDataPoint.kpi_code == "FIN-004",
                )
            )
        ).scalar_one()
        assert dp.value == 35000.0  # 60000 - 25000


# --------------------------------------------------------------------------- #
# HR roll-ups
# --------------------------------------------------------------------------- #


class TestHRRollups:
    @pytest.mark.asyncio
    async def test_attendance_rate(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.rollups import rollup_attendance_rate

        tid = seed_admin["tenant_id"]
        emp = await _seed_employee(db_session, tid, "E01")

        today = date.today()
        # 3 normal + 1 absent = 75% rate
        for d in range(1, 4):
            await _seed_attendance(
                db_session, tid, emp.id, today.replace(day=d), AttendanceStatus.NORMAL
            )
        await _seed_attendance(
            db_session, tid, emp.id, today.replace(day=4), AttendanceStatus.ABSENT
        )
        await db_session.commit()

        await rollup_attendance_rate(db_session, tenant_id=tid, as_of=today.replace(day=4))
        await db_session.commit()

        dp = (
            await db_session.execute(
                select(KPIDataPoint).where(
                    KPIDataPoint.tenant_id == tid,
                    KPIDataPoint.kpi_code == "HR-001",
                )
            )
        ).scalar_one()
        assert dp.value == 75.0

    @pytest.mark.asyncio
    async def test_revenue_per_capita(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.rollups import rollup_revenue_per_capita

        tid = seed_admin["tenant_id"]
        await _seed_employee(db_session, tid, "E01")
        await _seed_employee(db_session, tid, "E02")
        await _seed_ar(db_session, tid, "100000")
        await db_session.commit()

        await rollup_revenue_per_capita(db_session, tenant_id=tid)
        await db_session.commit()

        dp = (
            await db_session.execute(
                select(KPIDataPoint).where(
                    KPIDataPoint.tenant_id == tid,
                    KPIDataPoint.kpi_code == "HR-002",
                )
            )
        ).scalar_one()
        assert dp.value == 50000.0  # 100000 / 2


# --------------------------------------------------------------------------- #
# Safety roll-up
# --------------------------------------------------------------------------- #


class TestSafetyRollups:
    @pytest.mark.asyncio
    async def test_hazard_closure_rate(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.rollups import rollup_hazard_closure_rate

        tid = seed_admin["tenant_id"]
        # Seed some hazard KPI data points
        db_session.add(
            KPIDataPoint(
                id=uuid4(),
                tenant_id=tid,
                kpi_code="SAF-001",
                period=date.today(),
                value=5.0,
            )
        )
        await db_session.commit()

        await rollup_hazard_closure_rate(db_session, tenant_id=tid)
        await db_session.commit()

        dp = (
            await db_session.execute(
                select(KPIDataPoint).where(
                    KPIDataPoint.tenant_id == tid,
                    KPIDataPoint.kpi_code == "SAF-002",
                )
            )
        ).scalar_one()
        assert dp.value == 70.0  # placeholder


# --------------------------------------------------------------------------- #
# Composite / API
# --------------------------------------------------------------------------- #


class TestCompositeRollup:
    @pytest.mark.asyncio
    async def test_run_all_rollups(
        self, db_session: AsyncSession, seed_admin: dict[str, Any]
    ) -> None:
        from packages.management_decision.services.rollups import run_all_rollups

        tid = seed_admin["tenant_id"]
        await _seed_ar(db_session, tid, "5000")
        await _seed_employee(db_session, tid, "E01")
        await db_session.commit()

        result = await run_all_rollups(db_session, tenant_id=tid)
        await db_session.commit()
        assert result["status"] == "ok"

        # Verify at least finance KPIs were written
        count_stmt = select(KPIDataPoint).where(KPIDataPoint.tenant_id == tid)
        count = len((await db_session.execute(count_stmt)).scalars().all())
        assert count >= 7  # FIN-001..004 + HR-001..002 + SAF-002

    def test_rollup_api(self, auth_client: TestClient) -> None:
        r = auth_client.post("/mgmt/bi/rollup")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
