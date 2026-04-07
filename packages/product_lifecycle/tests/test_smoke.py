"""Smoke tests for product_lifecycle lane."""

from __future__ import annotations


def test_router_imports() -> None:
    from packages.product_lifecycle.api.routes import router

    assert router.prefix == "/plm"
