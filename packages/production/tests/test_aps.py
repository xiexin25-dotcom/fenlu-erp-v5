"""TASK-MFG-011 · APS FIFO scheduler unit tests.

Known-input scenarios:
    1. 3 orders, 1 workstation (cap=1) → sequential
    2. 3 orders, 1 workstation (cap=2) → first 2 parallel, third after earliest
    3. 2 orders, 2 workstations (cap=1 each) → parallel on different WS
    4. Empty inputs → empty output
    5. FIFO ordering respected (earliest delivery first)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from packages.production.services.aps import APSOrder, APSWorkstation, schedule_fifo

T0 = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
WS1 = uuid4()
WS2 = uuid4()
WO_A = uuid4()
WO_B = uuid4()
WO_C = uuid4()


def test_sequential_single_workstation() -> None:
    """3 orders × 1 WS (cap=1) → sequential, 4h each."""
    orders = [
        APSOrder(WO_A, T0 + timedelta(days=1), 4.0),
        APSOrder(WO_B, T0 + timedelta(days=2), 4.0),
        APSOrder(WO_C, T0 + timedelta(days=3), 4.0),
    ]
    ws = [APSWorkstation(WS1, capacity=1)]

    slots = schedule_fifo(orders, ws, T0)
    assert len(slots) == 3

    # All on WS1, sequential
    assert all(s.workstation_id == WS1 for s in slots)
    assert slots[0].planned_start == T0
    assert slots[0].planned_end == T0 + timedelta(hours=4)
    assert slots[1].planned_start == T0 + timedelta(hours=4)
    assert slots[1].planned_end == T0 + timedelta(hours=8)
    assert slots[2].planned_start == T0 + timedelta(hours=8)
    assert slots[2].planned_end == T0 + timedelta(hours=12)


def test_parallel_capacity() -> None:
    """3 orders × 1 WS (cap=2) → first 2 in parallel, third after."""
    orders = [
        APSOrder(WO_A, T0 + timedelta(days=1), 4.0),
        APSOrder(WO_B, T0 + timedelta(days=2), 4.0),
        APSOrder(WO_C, T0 + timedelta(days=3), 4.0),
    ]
    ws = [APSWorkstation(WS1, capacity=2)]

    slots = schedule_fifo(orders, ws, T0)
    assert len(slots) == 3

    # First two start at T0 (parallel)
    assert slots[0].planned_start == T0
    assert slots[1].planned_start == T0
    # Third starts at T0 + 4h (after first slot frees)
    assert slots[2].planned_start == T0 + timedelta(hours=4)


def test_multiple_workstations() -> None:
    """2 orders × 2 WS (cap=1 each) → parallel on different workstations."""
    orders = [
        APSOrder(WO_A, T0 + timedelta(days=1), 4.0),
        APSOrder(WO_B, T0 + timedelta(days=2), 4.0),
    ]
    ws = [
        APSWorkstation(WS1, capacity=1),
        APSWorkstation(WS2, capacity=1),
    ]

    slots = schedule_fifo(orders, ws, T0)
    assert len(slots) == 2

    # Both start at T0, on different workstations
    assert slots[0].planned_start == T0
    assert slots[1].planned_start == T0
    ws_ids = {s.workstation_id for s in slots}
    assert len(ws_ids) == 2


def test_fifo_ordering() -> None:
    """Orders sorted by delivery date, not insertion order."""
    late = APSOrder(WO_A, T0 + timedelta(days=10), 4.0)
    early = APSOrder(WO_B, T0 + timedelta(days=1), 4.0)
    mid = APSOrder(WO_C, T0 + timedelta(days=5), 4.0)
    ws = [APSWorkstation(WS1, capacity=1)]

    slots = schedule_fifo([late, early, mid], ws, T0)
    # early should be first
    assert slots[0].work_order_id == WO_B
    assert slots[1].work_order_id == WO_C
    assert slots[2].work_order_id == WO_A


def test_empty_orders() -> None:
    ws = [APSWorkstation(WS1, capacity=1)]
    assert schedule_fifo([], ws, T0) == []


def test_empty_workstations() -> None:
    orders = [APSOrder(WO_A, T0 + timedelta(days=1), 4.0)]
    assert schedule_fifo(orders, [], T0) == []


def test_no_overlap_single_ws() -> None:
    """Verify no time overlaps on a single-capacity workstation."""
    orders = [
        APSOrder(uuid4(), T0 + timedelta(days=i), 2.0)
        for i in range(5)
    ]
    ws = [APSWorkstation(WS1, capacity=1)]

    slots = schedule_fifo(orders, ws, T0)
    for i in range(1, len(slots)):
        assert slots[i].planned_start >= slots[i - 1].planned_end
