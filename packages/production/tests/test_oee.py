"""TASK-MFG-008 · OEE unit tests with known inputs.

Textbook scenario:
    Planned: 480 min (8h shift)
    Downtime: 60 min (故障停机)
    Available: 420 min
    Ideal cycle: 1 min/piece → theoretical output = 420 pcs
    Actual produced: 400 pcs (350 good + 20 scrap + 30 QC defects)
    Good units: 350

    Availability = 420 / 480 = 0.875
    Performance  = 400 / 420 = 0.952381
    Quality      = 350 / 400 = 0.875
    OEE          = 0.875 × 0.952381 × 0.875 = 0.729167
"""

from __future__ import annotations

import pytest

from packages.production.services.oee import OEERaw, OEEResult, compute_oee


def test_textbook_oee() -> None:
    raw = OEERaw(
        planned_minutes=480,
        downtime_minutes=60,
        total_produced=400,
        ideal_cycle_minutes=1.0,
        good_units=350,
    )
    result = compute_oee(raw)

    assert result.availability == pytest.approx(0.875, abs=1e-4)
    assert result.performance == pytest.approx(400 / 420, abs=1e-4)
    assert result.quality == pytest.approx(0.875, abs=1e-4)
    assert result.oee == pytest.approx(0.875 * (400 / 420) * 0.875, abs=1e-4)


def test_perfect_oee() -> None:
    """No downtime, perfect output, no defects → OEE = 1.0."""
    raw = OEERaw(
        planned_minutes=480,
        downtime_minutes=0,
        total_produced=480,  # 1 min/piece × 480 min
        ideal_cycle_minutes=1.0,
        good_units=480,
    )
    result = compute_oee(raw)
    assert result.availability == 1.0
    assert result.performance == 1.0
    assert result.quality == 1.0
    assert result.oee == 1.0


def test_zero_production() -> None:
    """Machine was planned but produced nothing."""
    raw = OEERaw(
        planned_minutes=480,
        downtime_minutes=480,
        total_produced=0,
        ideal_cycle_minutes=1.0,
        good_units=0,
    )
    result = compute_oee(raw)
    assert result.availability == 0.0
    assert result.performance == 0.0
    assert result.quality == 0.0
    assert result.oee == 0.0


def test_no_planned_time() -> None:
    """No planned production → all zeros."""
    raw = OEERaw(
        planned_minutes=0,
        downtime_minutes=0,
        total_produced=0,
        ideal_cycle_minutes=1.0,
        good_units=0,
    )
    result = compute_oee(raw)
    assert result.oee == 0.0


def test_clamped_performance() -> None:
    """If actual output exceeds theoretical, performance capped at 1.0."""
    raw = OEERaw(
        planned_minutes=480,
        downtime_minutes=0,
        total_produced=600,  # 超过理论 480
        ideal_cycle_minutes=1.0,
        good_units=600,
    )
    result = compute_oee(raw)
    assert result.performance == 1.0


def test_partial_quality() -> None:
    """Half the output is good."""
    raw = OEERaw(
        planned_minutes=100,
        downtime_minutes=0,
        total_produced=100,
        ideal_cycle_minutes=1.0,
        good_units=50,
    )
    result = compute_oee(raw)
    assert result.quality == pytest.approx(0.5, abs=1e-4)
    assert result.oee == pytest.approx(1.0 * 1.0 * 0.5, abs=1e-4)
