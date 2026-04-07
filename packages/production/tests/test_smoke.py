"""Smoke tests for production lane."""

from __future__ import annotations


def test_router_imports() -> None:
    from packages.production.api.routes import router

    assert router.prefix == "/mfg"
