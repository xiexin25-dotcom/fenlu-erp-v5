"""
领导驾驶舱 · Executive Dashboard
==================================

聚合 KPI 数据点 + 源表,生成结构化 payload 供前端渲染。
这是工信部「决策支持 三级」的核心交付物。
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.ap_ar import APRecord, APStatus, ARRecord
from packages.management_decision.models.kpi import KPIDataPoint


async def get_executive_dashboard(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> dict:
    """生成领导驾驶舱数据。"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # 本周一

    revenue = await _today_revenue(session, tenant_id, today)
    production = await _weekly_production(session, tenant_id, week_start, today)
    safety = await _open_safety_hazards(session, tenant_id)
    energy = await _energy_trend(session, tenant_id, today)
    cash = await _cash_position(session, tenant_id, today)

    return {
        "as_of": today.isoformat(),
        "revenue": revenue,
        "production": production,
        "safety": safety,
        "energy": energy,
        "cash": cash,
    }


# --------------------------------------------------------------------------- #
# 今日营收 (from AR)
# --------------------------------------------------------------------------- #


async def _today_revenue(
    session: AsyncSession, tenant_id: UUID, today: date
) -> dict:
    first_of_month = today.replace(day=1)

    # 今日新增 AR
    today_stmt = select(func.coalesce(func.sum(ARRecord.total_amount), 0)).where(
        ARRecord.tenant_id == tenant_id,
        func.date(ARRecord.created_at) == today,
    )
    today_val = float((await session.execute(today_stmt)).scalar() or 0)

    # 本月累计
    month_stmt = select(func.coalesce(func.sum(ARRecord.total_amount), 0)).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.created_at >= first_of_month,
    )
    month_val = float((await session.execute(month_stmt)).scalar() or 0)

    # AR 余额 (未收)
    balance_stmt = select(
        func.coalesce(func.sum(ARRecord.total_amount - ARRecord.received_amount), 0)
    ).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.status.in_([APStatus.UNPAID, APStatus.PARTIAL]),
    )
    balance = float((await session.execute(balance_stmt)).scalar() or 0)

    return {
        "today": today_val,
        "month_to_date": month_val,
        "ar_balance": balance,
        "unit": "CNY",
    }


# --------------------------------------------------------------------------- #
# 本周产量 + OEE
# --------------------------------------------------------------------------- #


async def _weekly_production(
    session: AsyncSession, tenant_id: UUID, week_start: date, today: date
) -> dict:
    # OPS-003 日产量 (本周累加)
    output_stmt = select(func.coalesce(func.sum(KPIDataPoint.value), 0)).where(
        KPIDataPoint.tenant_id == tenant_id,
        KPIDataPoint.kpi_code == "OPS-003",
        KPIDataPoint.period >= week_start,
        KPIDataPoint.period <= today,
    )
    output = float((await session.execute(output_stmt)).scalar() or 0)

    # OPS-001 OEE (本周平均)
    oee_stmt = select(func.avg(KPIDataPoint.value)).where(
        KPIDataPoint.tenant_id == tenant_id,
        KPIDataPoint.kpi_code == "OPS-001",
        KPIDataPoint.period >= week_start,
        KPIDataPoint.period <= today,
    )
    oee = float((await session.execute(oee_stmt)).scalar() or 0)

    # OPS-002 工单按时完成率 (最新)
    ontime_stmt = (
        select(KPIDataPoint.value)
        .where(
            KPIDataPoint.tenant_id == tenant_id,
            KPIDataPoint.kpi_code == "OPS-002",
        )
        .order_by(KPIDataPoint.period.desc())
        .limit(1)
    )
    ontime = float((await session.execute(ontime_stmt)).scalar() or 0)

    return {
        "weekly_output": output,
        "weekly_output_unit": "件",
        "oee_avg": round(oee, 2),
        "oee_unit": "%",
        "ontime_rate": round(ontime, 2),
    }


# --------------------------------------------------------------------------- #
# 开放安全隐患
# --------------------------------------------------------------------------- #


async def _open_safety_hazards(
    session: AsyncSession, tenant_id: UUID
) -> dict:
    # SAF-001 隐患总数 (累计)
    total_stmt = select(func.coalesce(func.sum(KPIDataPoint.value), 0)).where(
        KPIDataPoint.tenant_id == tenant_id,
        KPIDataPoint.kpi_code == "SAF-001",
    )
    total = float((await session.execute(total_stmt)).scalar() or 0)

    # SAF-002 整改率 (最新)
    rate_stmt = (
        select(KPIDataPoint.value)
        .where(
            KPIDataPoint.tenant_id == tenant_id,
            KPIDataPoint.kpi_code == "SAF-002",
        )
        .order_by(KPIDataPoint.period.desc())
        .limit(1)
    )
    closure_rate = float((await session.execute(rate_stmt)).scalar() or 0)

    # SAF-003 连续安全天数 (最新)
    days_stmt = (
        select(KPIDataPoint.value)
        .where(
            KPIDataPoint.tenant_id == tenant_id,
            KPIDataPoint.kpi_code == "SAF-003",
        )
        .order_by(KPIDataPoint.period.desc())
        .limit(1)
    )
    safe_days = float((await session.execute(days_stmt)).scalar() or 0)

    return {
        "total_hazards": int(total),
        "closure_rate": round(closure_rate, 1),
        "closure_rate_unit": "%",
        "consecutive_safe_days": int(safe_days),
    }


# --------------------------------------------------------------------------- #
# 能耗单耗趋势
# --------------------------------------------------------------------------- #


async def _energy_trend(
    session: AsyncSession, tenant_id: UUID, today: date
) -> dict:
    # ENG-002 月度用电量 (最近 7 天趋势)
    trend_stmt = (
        select(KPIDataPoint.period, KPIDataPoint.value)
        .where(
            KPIDataPoint.tenant_id == tenant_id,
            KPIDataPoint.kpi_code == "ENG-002",
            KPIDataPoint.period >= today - timedelta(days=6),
            KPIDataPoint.period <= today,
        )
        .order_by(KPIDataPoint.period)
    )
    rows = (await session.execute(trend_stmt)).all()
    trend = [{"date": r[0].isoformat(), "kwh": r[1]} for r in rows]

    # ENG-001 万元产值综合能耗 (最新)
    unit_stmt = (
        select(KPIDataPoint.value)
        .where(
            KPIDataPoint.tenant_id == tenant_id,
            KPIDataPoint.kpi_code == "ENG-001",
        )
        .order_by(KPIDataPoint.period.desc())
        .limit(1)
    )
    unit_consumption = float((await session.execute(unit_stmt)).scalar() or 0)

    # ENG-003 单位产品能耗 (最新)
    per_piece_stmt = (
        select(KPIDataPoint.value)
        .where(
            KPIDataPoint.tenant_id == tenant_id,
            KPIDataPoint.kpi_code == "ENG-003",
        )
        .order_by(KPIDataPoint.period.desc())
        .limit(1)
    )
    per_piece = float((await session.execute(per_piece_stmt)).scalar() or 0)

    return {
        "daily_trend": trend,
        "unit_consumption": round(unit_consumption, 4),
        "unit_consumption_unit": "tce/万元",
        "per_piece_energy": round(per_piece, 2),
        "per_piece_unit": "kWh/件",
    }


# --------------------------------------------------------------------------- #
# 现金头寸
# --------------------------------------------------------------------------- #


async def _cash_position(
    session: AsyncSession, tenant_id: UUID, today: date
) -> dict:
    first_of_month = today.replace(day=1)

    # 本月收款
    received_stmt = select(func.coalesce(func.sum(ARRecord.received_amount), 0)).where(
        ARRecord.tenant_id == tenant_id,
        ARRecord.created_at >= first_of_month,
    )
    received = float((await session.execute(received_stmt)).scalar() or 0)

    # 本月付款
    paid_stmt = select(func.coalesce(func.sum(APRecord.paid_amount), 0)).where(
        APRecord.tenant_id == tenant_id,
        APRecord.created_at >= first_of_month,
    )
    paid = float((await session.execute(paid_stmt)).scalar() or 0)

    # AP 待付总额
    ap_due_stmt = select(
        func.coalesce(func.sum(APRecord.total_amount - APRecord.paid_amount), 0)
    ).where(
        APRecord.tenant_id == tenant_id,
        APRecord.status.in_([APStatus.UNPAID, APStatus.PARTIAL, APStatus.OVERDUE]),
    )
    ap_due = float((await session.execute(ap_due_stmt)).scalar() or 0)

    return {
        "net_cash_flow": round(received - paid, 2),
        "month_received": received,
        "month_paid": paid,
        "ap_due": ap_due,
        "unit": "CNY",
    }
