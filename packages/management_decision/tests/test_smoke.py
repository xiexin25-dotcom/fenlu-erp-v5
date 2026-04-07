"""Smoke tests for management_decision lane."""

from __future__ import annotations


def test_router_imports() -> None:
    from packages.management_decision.api.routes import router

    assert router.prefix == "/mgmt"
