"""Verify that all 4 lane stubs exist and import cleanly.

Once Claude Code starts filling in lanes, these tests will be replaced
with the lane's own test suites.
"""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("lane", "prefix"),
    [
        ("product_lifecycle", "/plm"),
        ("production", "/mfg"),
        ("supply_chain", "/scm"),
        ("management_decision", "/mgmt"),
    ],
)
def test_lane_router_imports(lane: str, prefix: str) -> None:
    module = __import__(f"packages.{lane}.api.routes", fromlist=["router"])
    assert module.router.prefix == prefix
