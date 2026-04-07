"""APS v1 · FIFO + capacity 排程算法。

TASK-MFG-011

算法:
    1. 工单按 planned_end (交期) 升序排列 (FIFO)
    2. 对每个工单,找到最早可用的工位 (earliest_available 最小)
    3. 在该工位上安排: planned_start = max(date_range_start, 工位最早可用时间)
    4. planned_end = planned_start + estimated_hours
    5. 更新该工位的最早可用时间

不使用 OR-Tools 或其他重型求解器。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID


@dataclass
class APSOrder:
    """排程输入: 一个待排工单。"""

    work_order_id: UUID
    planned_end: datetime  # 交期,越早越优先
    estimated_hours: float  # 预计加工时长


@dataclass
class APSWorkstation:
    """排程输入: 一个工位及其容量。"""

    workstation_id: UUID
    capacity: int  # 并行槽位数


@dataclass
class APSSlot:
    """排程输出: 一个已安排的时间槽。"""

    work_order_id: UUID
    workstation_id: UUID
    planned_start: datetime
    planned_end: datetime


def schedule_fifo(
    orders: list[APSOrder],
    workstations: list[APSWorkstation],
    range_start: datetime,
) -> list[APSSlot]:
    """FIFO 排程: 按交期排序,贪心分配到最早可用工位槽。

    Args:
        orders: 待排工单列表。
        workstations: 可用工位列表。
        range_start: 排程窗口起始时间。

    Returns:
        排好的时间槽列表。
    """
    if not orders or not workstations:
        return []

    # Sort by delivery date (FIFO)
    sorted_orders = sorted(orders, key=lambda o: o.planned_end)

    # Build slot pool: each workstation has `capacity` parallel slots,
    # each tracking its earliest available time.
    # slots[i] = (workstation_id, earliest_available)
    slots: list[tuple[UUID, datetime]] = []
    for ws in workstations:
        for _ in range(ws.capacity):
            slots.append((ws.workstation_id, range_start))

    result: list[APSSlot] = []
    for order in sorted_orders:
        # Find slot with earliest available time
        best_idx = min(range(len(slots)), key=lambda i: slots[i][1])
        ws_id, earliest = slots[best_idx]

        start = max(earliest, range_start)
        end = start + timedelta(hours=order.estimated_hours)

        result.append(APSSlot(
            work_order_id=order.work_order_id,
            workstation_id=ws_id,
            planned_start=start,
            planned_end=end,
        ))

        # Update slot availability
        slots[best_idx] = (ws_id, end)

    return result
