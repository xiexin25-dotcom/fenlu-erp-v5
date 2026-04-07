"""维保工单自动生成服务 · TASK-MFG-007。

在实际部署中由 Celery beat 定时触发; 这里提供一个纯函数供端点/cron 调用。
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.production.models import MaintenanceLog, MaintenancePlan


async def generate_due_maintenance(
    session: AsyncSession,
    as_of: date | None = None,
) -> list[MaintenanceLog]:
    """扫描所有到期的维保计划,生成 MaintenanceLog 记录。

    Returns:
        新生成的 MaintenanceLog 列表。
    """
    today = as_of or date.today()

    stmt = select(MaintenancePlan).where(MaintenancePlan.is_active.is_(True))
    result = await session.execute(stmt)
    plans = list(result.scalars().all())

    generated: list[MaintenanceLog] = []
    for plan in plans:
        last = plan.last_generated
        if last is not None and (today - last).days < plan.interval_days:
            continue  # 还没到期

        log = MaintenanceLog(
            tenant_id=plan.tenant_id,
            equipment_id=plan.equipment_id,
            plan_id=plan.id,
            description=f"[Auto] {plan.name}",
            performed_at=today,  # type: ignore[arg-type]
            performed_by=plan.created_by or plan.tenant_id,  # fallback
        )
        session.add(log)
        plan.last_generated = today
        generated.append(log)

    if generated:
        await session.flush()

    return generated
