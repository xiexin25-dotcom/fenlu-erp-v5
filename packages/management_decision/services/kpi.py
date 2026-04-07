"""
KPI service · 定义注册 + 种子数据
==================================
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.management_decision.models.kpi import KPIDataPoint, KPIDefinition

# --------------------------------------------------------------------------- #
# 种子 KPI (~20 条,覆盖工信部 16 场景)
# --------------------------------------------------------------------------- #

SEED_KPIS: list[dict] = [
    # ── 财务 (financial) — 场景: 财务管理 ★ ──
    {"code": "FIN-001", "name": "月度营业收入", "category": "financial", "unit": "元", "source_lane": "mgmt", "aggregation": "sum", "description": "当月 AR 确认收入合计"},
    {"code": "FIN-002", "name": "应收账款周转天数", "category": "financial", "unit": "天", "source_lane": "mgmt", "aggregation": "latest", "description": "AR 余额 / 日均收入"},
    {"code": "FIN-003", "name": "应付账款余额", "category": "financial", "unit": "元", "source_lane": "mgmt", "aggregation": "latest", "description": "未结 AP 总额"},
    {"code": "FIN-004", "name": "现金流净额", "category": "financial", "unit": "元", "source_lane": "mgmt", "aggregation": "sum", "description": "当月收款 - 付款"},
    # ── 运营 (operations) — 场景: 生产管控★/计划排程/产品设计★/营销管理★ ──
    {"code": "OPS-001", "name": "设备综合效率 OEE", "category": "operations", "unit": "%", "source_lane": "mfg", "aggregation": "avg", "description": "可用率 × 性能率 × 良品率"},
    {"code": "OPS-002", "name": "工单按时完成率", "category": "operations", "unit": "%", "source_lane": "mfg", "aggregation": "avg", "description": "按时完工工单 / 总工单"},
    {"code": "OPS-003", "name": "日产量", "category": "operations", "unit": "件", "source_lane": "mfg", "aggregation": "sum", "description": "当日完工入库数量"},
    {"code": "OPS-004", "name": "订单交付准时率", "category": "operations", "unit": "%", "source_lane": "plm", "aggregation": "avg", "description": "准时交付订单 / 总订单"},
    # ── 质量 (quality) — 场景: 质量管理★ ──
    {"code": "QUA-001", "name": "一次合格率 FPY", "category": "quality", "unit": "%", "source_lane": "mfg", "aggregation": "avg", "description": "首检合格数 / 送检总数"},
    {"code": "QUA-002", "name": "客户投诉率", "category": "quality", "unit": "‰", "source_lane": "plm", "aggregation": "avg", "description": "投诉单数 / 发货批次 ×1000"},
    {"code": "QUA-003", "name": "不良品率", "category": "quality", "unit": "%", "source_lane": "mfg", "aggregation": "avg", "description": "不良品数 / 生产总数"},
    # ── 人力 (hr) — 场景: 人力资源 ──
    {"code": "HR-001", "name": "员工出勤率", "category": "hr", "unit": "%", "source_lane": "mgmt", "aggregation": "avg", "description": "实际出勤天数 / 应出勤天数"},
    {"code": "HR-002", "name": "人均产值", "category": "hr", "unit": "元/人", "source_lane": "mgmt", "aggregation": "latest", "description": "月产值 / 在册人数"},
    {"code": "HR-003", "name": "离职率", "category": "hr", "unit": "%", "source_lane": "mgmt", "aggregation": "latest", "description": "月离职人数 / 平均在册人数"},
    # ── 安全 (safety) — 场景: 安全生产★ ──
    {"code": "SAF-001", "name": "安全隐患数", "category": "safety", "unit": "件", "source_lane": "mfg", "aggregation": "sum", "description": "当月新报隐患"},
    {"code": "SAF-002", "name": "隐患整改率", "category": "safety", "unit": "%", "source_lane": "mfg", "aggregation": "avg", "description": "已关闭隐患 / 总隐患"},
    {"code": "SAF-003", "name": "连续安全生产天数", "category": "safety", "unit": "天", "source_lane": "mfg", "aggregation": "latest", "description": "距上次安全事故的天数"},
    # ── 能耗 (energy) — 场景: 能耗管理★ ──
    {"code": "ENG-001", "name": "万元产值综合能耗", "category": "energy", "unit": "tce/万元", "source_lane": "mfg", "aggregation": "latest", "description": "综合能耗(吨标煤) / 万元产值"},
    {"code": "ENG-002", "name": "月度用电量", "category": "energy", "unit": "kWh", "source_lane": "mfg", "aggregation": "sum", "description": "当月总用电"},
    {"code": "ENG-003", "name": "单位产品能耗", "category": "energy", "unit": "kWh/件", "source_lane": "mfg", "aggregation": "avg", "description": "月用电 / 月产量"},
]


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #


async def seed_kpi_definitions(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    created_by: UUID | None = None,
) -> int:
    """种子化 KPI 定义。跳过已存在的 code。返回新增数量。"""
    existing = await session.execute(
        select(KPIDefinition.code).where(KPIDefinition.tenant_id == tenant_id)
    )
    existing_codes = {row[0] for row in existing.all()}

    count = 0
    for kpi in SEED_KPIS:
        if kpi["code"] in existing_codes:
            continue
        defn = KPIDefinition(
            id=uuid4(),
            tenant_id=tenant_id,
            code=kpi["code"],
            name=kpi["name"],
            category=kpi["category"],
            unit=kpi["unit"],
            source_lane=kpi["source_lane"],
            aggregation=kpi["aggregation"],
            description=kpi.get("description"),
            created_by=created_by,
        )
        session.add(defn)
        count += 1

    if count > 0:
        await session.flush()
    return count


async def list_kpi_definitions(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    category: str | None = None,
) -> list[KPIDefinition]:
    stmt = (
        select(KPIDefinition)
        .where(KPIDefinition.tenant_id == tenant_id, KPIDefinition.is_active.is_(True))
        .order_by(KPIDefinition.code)
    )
    if category:
        stmt = stmt.where(KPIDefinition.category == category)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_kpi_definition_by_code(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    code: str,
) -> KPIDefinition | None:
    stmt = select(KPIDefinition).where(
        KPIDefinition.tenant_id == tenant_id,
        KPIDefinition.code == code,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_kpi_data_points(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    kpi_code: str,
    limit: int = 30,
) -> list[KPIDataPoint]:
    stmt = (
        select(KPIDataPoint)
        .where(KPIDataPoint.tenant_id == tenant_id, KPIDataPoint.kpi_code == kpi_code)
        .order_by(KPIDataPoint.period.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
