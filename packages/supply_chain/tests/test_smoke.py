"""Smoke tests for supply_chain lane."""

from __future__ import annotations


def test_router_imports() -> None:
    from packages.supply_chain.api.routes import router

    assert router.prefix == "/scm"
