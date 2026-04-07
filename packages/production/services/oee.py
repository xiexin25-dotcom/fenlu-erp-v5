"""OEE (Overall Equipment Effectiveness) 计算 · TASK-MFG-008。

OEE = Availability × Performance × Quality

数据来源:
    - Availability: 计划生产时间 vs FaultRecord 停机时间
    - Performance:  实际产出 (JobTicket) vs 理论产能
    - Quality:      良品数 / 总产出 (QCInspection)

本模块分为两层:
    1. compute_oee() — 纯函数,接受原始数值,返回 OEE; 方便单测
    2. OEEService.calculate() — 异步,从 DB 拉数据后调用 compute_oee()
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import FaultRecord, JobTicket, QCInspection, WorkOrder


# ── Pure calculation ────────────────────────────────────────────────────────── #


@dataclass
class OEERaw:
    """OEE 计算的原始输入。"""

    planned_minutes: float      # 计划生产总分钟 (如 8h = 480min)
    downtime_minutes: float     # 故障停机分钟
    total_produced: float       # 总产出数量 (completed + scrap)
    ideal_cycle_minutes: float  # 理论单件耗时 (分钟/件)
    good_units: float           # 良品数 (total - scrap - QC defects)


@dataclass
class OEEResult:
    availability: float
    performance: float
    quality: float
    oee: float


def compute_oee(raw: OEERaw) -> OEEResult:
    """纯函数 OEE 计算。所有输入 ≥ 0。

    Returns:
        OEEResult with values clamped to [0, 1].
    """
    # Availability
    if raw.planned_minutes <= 0:
        availability = 0.0
    else:
        available = raw.planned_minutes - raw.downtime_minutes
        availability = max(0.0, min(1.0, available / raw.planned_minutes))

    # Performance
    available_minutes = raw.planned_minutes - raw.downtime_minutes
    if available_minutes <= 0 or raw.ideal_cycle_minutes <= 0:
        performance = 0.0
    else:
        ideal_output = available_minutes / raw.ideal_cycle_minutes
        performance = max(0.0, min(1.0, raw.total_produced / ideal_output))

    # Quality
    if raw.total_produced <= 0:
        quality = 0.0
    else:
        quality = max(0.0, min(1.0, raw.good_units / raw.total_produced))

    oee = availability * performance * quality

    return OEEResult(
        availability=round(availability, 6),
        performance=round(performance, 6),
        quality=round(quality, 6),
        oee=round(oee, 6),
    )


# ── DB-backed service ──────────────────────────────────────────────────────── #


DEFAULT_PLANNED_MINUTES = 480.0       # 8 小时/天
DEFAULT_IDEAL_CYCLE_MINUTES = 1.0     # 1 分钟/件 (后续可配置到 Equipment 表)


async def calculate_oee(
    session: AsyncSession,
    equipment_id: UUID,
    target_date: date,
    planned_minutes: float = DEFAULT_PLANNED_MINUTES,
    ideal_cycle_minutes: float = DEFAULT_IDEAL_CYCLE_MINUTES,
) -> OEEResult:
    """从 DB 拉数据并计算指定设备某天的 OEE。"""

    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    # ── Downtime (fault_records 中当天有交叠的记录) ──────────────────────
    faults = (
        await session.execute(
            select(FaultRecord.started_at, FaultRecord.ended_at).where(
                FaultRecord.equipment_id == equipment_id,
                FaultRecord.started_at <= day_end,
                # ended_at is NULL (ongoing) or >= day_start
                (FaultRecord.ended_at.is_(None)) | (FaultRecord.ended_at >= day_start),
            )
        )
    ).all()

    downtime = 0.0
    for started, ended in faults:
        # Ensure tz-aware (SQLite returns naive datetimes)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if ended is not None and ended.tzinfo is None:
            ended = ended.replace(tzinfo=timezone.utc)
        s = max(started, day_start)
        e = min(ended, day_end) if ended else day_end
        minutes = (e - s).total_seconds() / 60
        downtime += max(0.0, minutes)

    # ── Production output (job_tickets reported today for WOs on this equipment) ──
    # JobTicket 不直接关联 equipment; 通过 WorkOrder 间接关联暂时不现实
    # (WorkOrder 没有 equipment_id 字段). 按 TASK 描述 "Pull data from job tickets",
    # 我们拉当天所有已报工的 ticket 汇总 (跨设备; 后续 MFG-011 APS 会给 WO 绑定设备).
    # 这里采用 "当天所有 job tickets" 作为该设备的产出近似.
    # TODO: 当 WorkOrder 有 equipment_id 后改为精确查询.
    completed_row = (
        await session.execute(
            select(
                func.coalesce(func.sum(JobTicket.completed_qty), 0),
                func.coalesce(func.sum(JobTicket.scrap_qty), 0),
            ).where(
                JobTicket.reported_at >= day_start,
                JobTicket.reported_at <= day_end,
            )
        )
    ).one()
    completed = float(completed_row[0])
    scrap = float(completed_row[1])
    total_produced = completed + scrap

    # ── Quality (QC defects for the day) ────────────────────────────────────
    defect_row = (
        await session.execute(
            select(func.coalesce(func.sum(QCInspection.defect_count), 0)).where(
                QCInspection.created_at >= day_start,
                QCInspection.created_at <= day_end,
            )
        )
    ).scalar_one()
    total_defects = float(defect_row)

    good_units = max(0.0, total_produced - scrap - total_defects)

    raw = OEERaw(
        planned_minutes=planned_minutes,
        downtime_minutes=downtime,
        total_produced=total_produced,
        ideal_cycle_minutes=ideal_cycle_minutes,
        good_units=good_units,
    )
    return compute_oee(raw)
