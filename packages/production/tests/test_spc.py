"""TASK-MFG-006 · SPC p-chart unit tests.

Uses textbook-style data:
    25 subgroups, each n=100.

    Defect counts: [12, 8, 6, 9, 10, 12, 11, 16, 10, 6,
                     20, 15, 9, 8, 6,  8, 10, 7,  5, 8,
                      5, 8, 10, 6, 9]
    Total defects = 234, total inspected = 2500
    p_bar = 234 / 2500 = 0.0936
    sigma = sqrt(0.0936 * 0.9064 / 100) = 0.02912...
    UCL = 0.0936 + 3 * 0.02912 = 0.18098...
    LCL = 0.0936 - 3 * 0.02912 = 0.00622...
"""

from __future__ import annotations

import math

import pytest

from packages.production.services.spc import SPCResult, compute_p_chart

# Montgomery textbook data
MONTGOMERY_DEFECTS = [
    12, 8, 6, 9, 10, 12, 11, 16, 10, 6,
    20, 15, 9, 8, 6, 8, 10, 7, 5, 8,
    5, 8, 10, 6, 9,
]
MONTGOMERY_N = 100
MONTGOMERY_SAMPLES = [(MONTGOMERY_N, d) for d in MONTGOMERY_DEFECTS]


def test_p_bar() -> None:
    result = compute_p_chart(MONTGOMERY_SAMPLES)
    expected_p_bar = sum(MONTGOMERY_DEFECTS) / (MONTGOMERY_N * len(MONTGOMERY_DEFECTS))
    assert result.p_bar == pytest.approx(expected_p_bar, abs=1e-5)
    assert result.p_bar == pytest.approx(0.0936, abs=1e-4)


def test_control_limits_constant_n() -> None:
    """With constant sample size, all points should have the same UCL/LCL."""
    result = compute_p_chart(MONTGOMERY_SAMPLES)
    p_bar = result.p_bar
    sigma = math.sqrt(p_bar * (1 - p_bar) / MONTGOMERY_N)
    expected_ucl = p_bar + 3 * sigma
    expected_lcl = max(0.0, p_bar - 3 * sigma)

    for pt in result.points:
        assert pt.ucl == pytest.approx(expected_ucl, abs=1e-4)
        assert pt.lcl == pytest.approx(expected_lcl, abs=1e-4)
        assert pt.cl == pytest.approx(p_bar, abs=1e-5)

    # Verify numeric values
    assert expected_ucl == pytest.approx(0.1810, abs=1e-3)
    assert expected_lcl == pytest.approx(0.0062, abs=1e-3)


def test_individual_point_values() -> None:
    result = compute_p_chart(MONTGOMERY_SAMPLES)
    # Point 0: 12 defects in 100 → p = 0.12
    assert result.points[0].p == pytest.approx(0.12, abs=1e-5)
    assert result.points[0].defect_count == 12
    # Point 10: 20 defects → p = 0.20, should be above UCL
    assert result.points[10].p == pytest.approx(0.20, abs=1e-5)
    assert result.points[10].p > result.points[10].ucl  # out of control


def test_variable_sample_sizes() -> None:
    """Different n per subgroup → different UCL/LCL per point."""
    samples = [(50, 5), (100, 8), (75, 6)]
    result = compute_p_chart(samples)
    total_d = 5 + 8 + 6
    total_n = 50 + 100 + 75
    assert result.p_bar == pytest.approx(total_d / total_n, abs=1e-5)
    # UCLs should differ since n differs
    ucls = [pt.ucl for pt in result.points]
    assert ucls[0] != ucls[1]  # n=50 vs n=100 → different sigma


def test_lcl_clamped_to_zero() -> None:
    """When p_bar is very small, LCL should not go below 0."""
    samples = [(1000, 1), (1000, 0), (1000, 1)]
    result = compute_p_chart(samples)
    for pt in result.points:
        assert pt.lcl >= 0.0


def test_all_zero_defects() -> None:
    """p_bar = 0, UCL = LCL = CL = 0."""
    samples = [(100, 0), (100, 0), (100, 0)]
    result = compute_p_chart(samples)
    assert result.p_bar == 0.0
    for pt in result.points:
        assert pt.ucl == 0.0
        assert pt.lcl == 0.0
        assert pt.cl == 0.0


def test_empty_samples_raises() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        compute_p_chart([])


def test_point_count() -> None:
    result = compute_p_chart(MONTGOMERY_SAMPLES)
    assert len(result.points) == 25
    assert result.total_inspected == 2500
    assert result.total_defects == 234
