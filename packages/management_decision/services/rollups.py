"""
BI 聚合 roll-up 任务
======================

每个 roll-up 是一个 async 函数,从源表聚合数据后写入 kpi_data_points。
可被 Celery task 包装调用,也可直接 await (测试/手动触发)。

调度频率:
- hourly:   OEE / 日产量 / 工单完成率
- daily:    财务 (收入/应收/应付/现金流) / HR (出勤率/人均产值)
- realtime: 安全隐患 (由 event_consumer 实时写入,此处做日汇总修正)
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.ap_ar import APRecord, APStatus, ARRecord
from packages.management_decision.models.attendance import Attendance, AttendanceStatus
from packages.management_decision.models.hr import Employee
from packages.management_decision.models.kpi import KPIDataPoint
from packages.management_decision.services.event_consumer import _upsert_kpi_data_point


# --------------------------------------------------------------------------- #
# Finance roll-ups (daily)
# --------------------------------------------------------------------------- #


async def rollup_monthly_revenue(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> None:
    """FIN-001: 月度营业收入 = 本月已确认 AR total_amount 合计。"""
    today = as_of or date.today()
    first_of_month = today.replace(day=1)

    stmt = select(func.coalesce(func.sum(ARRecord.total_amount), 0)).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.created_at >= first_of_month,
    )
    result = await session.execute(stmt)
    total = float(result.scalar() or 0)

    await _upsert_kpi_data_point(
        session, tenant_id=tenant_id, kpi_code="FIN-001", period=today, value=total
    )


async def rollup_ar_turnover_days(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> None:
    """FIN-002: 应收账款周转天数 = AR 余额 / (月收入 / 30)。"""
    today = as_of or date.today()
    first_of_month = today.replace(day=1)

    # AR balance
    balance_stmt = select(
        func.coalesce(func.sum(ARRecord.total_amount - ARRecord.received_amount), 0)
    ).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.status.in_([APStatus.UNPAID, APStatus.PARTIAL]),
    )
    balance = float((await session.execute(balance_stmt)).scalar() or 0)

    # Monthly revenue
    rev_stmt = select(func.coalesce(func.sum(ARRecord.total_amount), 0)).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.created_at >= first_of_month,
    )
    revenue = float((await session.execute(rev_stmt)).scalar() or 0)
    daily_revenue = revenue / 30 if revenue > 0 else 1  # avoid div by zero
    days = balance / daily_revenue

    await _upsert_kpi_data_point(
        session, tenant_id=tenant_id, kpi_code="FIN-002", period=today, value=round(days, 1)
    )


async def rollup_ap_balance(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> None:
    """FIN-003: 应付账款余额。"""
    today = as_of or date.today()
    stmt = select(
        func.coalesce(func.sum(APRecord.total_amount - APRecord.paid_amount), 0)
    ).where(
        APRecord.tenant_id == tenant_id,
        APRecord.status.in_([APStatus.UNPAID, APStatus.PARTIAL, APStatus.OVERDUE]),
    )
    balance = float((await session.execute(stmt)).scalar() or 0)

    await _upsert_kpi_data_point(
        session, tenant_id=tenant_id, kpi_code="FIN-003", period=today, value=balance
    )


async def rollup_cash_flow(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> None:
    """FIN-004: 现金流净额 = 本月 AR received - AP paid。"""
    today = as_of or date.today()
    first_of_month = today.replace(day=1)

    received_stmt = select(func.coalesce(func.sum(ARRecord.received_amount), 0)).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.created_at >= first_of_month,
    )
    received = float((await session.execute(received_stmt)).scalar() or 0)

    paid_stmt = select(func.coalesce(func.sum(APRecord.paid_amount), 0)).where(
        APRecord.tenant_id == tenant_id,
        APRecord.created_at >= first_of_month,
    )
    paid = float((await session.execute(paid_stmt)).scalar() or 0)

    await _upsert_kpi_data_point(
        session,
        tenant_id=tenant_id,
        kpi_code="FIN-004",
        period=today,
        value=round(received - paid, 4),
    )


# --------------------------------------------------------------------------- #
# HR roll-ups (daily)
# --------------------------------------------------------------------------- #


async def rollup_attendance_rate(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> None:
    """HR-001: 员工出勤率 = 正常+迟到 / 总考勤记录 × 100。"""
    today = as_of or date.today()
    first_of_month = today.replace(day=1)

    total_stmt = select(func.count()).select_from(Attendance).where(
        Attendance.tenant_id == tenant_id,
        Attendance.work_date >= first_of_month,
        Attendance.work_date <= today,
    )
    total = (await session.execute(total_stmt)).scalar() or 0

    present_stmt = select(func.count()).select_from(Attendance).where(
        Attendance.tenant_id == tenant_id,
        Attendance.work_date >= first_of_month,
        Attendance.work_date <= today,
        Attendance.status.in_([AttendanceStatus.NORMAL, AttendanceStatus.LATE]),
    )
    present = (await session.execute(present_stmt)).scalar() or 0

    rate = (present / total * 100) if total > 0 else 100.0
    await _upsert_kpi_data_point(
        session, tenant_id=tenant_id, kpi_code="HR-001", period=today, value=round(rate, 2)
    )


async def rollup_revenue_per_capita(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> None:
    """HR-002: 人均产值 = 月收入 / 在册人数。"""
    today = as_of or date.today()
    first_of_month = today.replace(day=1)

    rev_stmt = select(func.coalesce(func.sum(ARRecord.total_amount), 0)).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.created_at >= first_of_month,
    )
    revenue = float((await session.execute(rev_stmt)).scalar() or 0)

    headcount_stmt = select(func.count()).select_from(Employee).where(
        Employee.tenant_id == tenant_id,
        Employee.is_active.is_(True),
    )
    headcount = (await session.execute(headcount_stmt)).scalar() or 1

    per_capita = revenue / headcount
    await _upsert_kpi_data_point(
        session,
        tenant_id=tenant_id,
        kpi_code="HR-002",
        period=today,
        value=round(per_capita, 2),
    )


# --------------------------------------------------------------------------- #
# Safety roll-up (daily summary / correction)
# --------------------------------------------------------------------------- #


async def rollup_hazard_closure_rate(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> None:
    """SAF-002: 隐患整改率 — 无直接隐患表,用 KPI data point 近似。

    读取 SAF-001 (隐患总数) 的累积值,假设关闭数 = 总数 × 0.7 (占位)。
    后续接入 MFG hazard 关闭事件后用真实数据。
    """
    today = as_of or date.today()

    stmt = select(func.coalesce(func.sum(KPIDataPoint.value), 0)).where(
        KPIDataPoint.tenant_id == tenant_id,
        KPIDataPoint.kpi_code == "SAF-001",
    )
    total_hazards = float((await session.execute(stmt)).scalar() or 0)

    # placeholder: 70% closure rate when there are hazards
    rate = 70.0 if total_hazards > 0 else 100.0
    await _upsert_kpi_data_point(
        session, tenant_id=tenant_id, kpi_code="SAF-002", period=today, value=rate
    )


# --------------------------------------------------------------------------- #
# Composite runners (called by Celery beat or manually)
# --------------------------------------------------------------------------- #


async def run_daily_finance_rollup(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> dict[str, str]:
    """日级财务 roll-up — 一次跑 4 个财务 KPI。"""
    await rollup_monthly_revenue(session, tenant_id=tenant_id, as_of=as_of)
    await rollup_ar_turnover_days(session, tenant_id=tenant_id, as_of=as_of)
    await rollup_ap_balance(session, tenant_id=tenant_id, as_of=as_of)
    await rollup_cash_flow(session, tenant_id=tenant_id, as_of=as_of)
    return {"status": "ok", "kpis": "FIN-001,FIN-002,FIN-003,FIN-004"}


async def run_daily_hr_rollup(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> dict[str, str]:
    """日级 HR roll-up。"""
    await rollup_attendance_rate(session, tenant_id=tenant_id, as_of=as_of)
    await rollup_revenue_per_capita(session, tenant_id=tenant_id, as_of=as_of)
    return {"status": "ok", "kpis": "HR-001,HR-002"}


async def run_daily_safety_rollup(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> dict[str, str]:
    """日级安全 roll-up。"""
    await rollup_hazard_closure_rate(session, tenant_id=tenant_id, as_of=as_of)
    return {"status": "ok", "kpis": "SAF-002"}


async def run_all_rollups(
    session: AsyncSession, *, tenant_id: UUID, as_of: date | None = None
) -> dict[str, str]:
    """跑全部 roll-up。"""
    await run_daily_finance_rollup(session, tenant_id=tenant_id, as_of=as_of)
    await run_daily_hr_rollup(session, tenant_id=tenant_id, as_of=as_of)
    await run_daily_safety_rollup(session, tenant_id=tenant_id, as_of=as_of)
    return {"status": "ok", "kpis": "FIN-001..004,HR-001..002,SAF-002"}
