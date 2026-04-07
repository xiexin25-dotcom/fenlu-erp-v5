"""PLM test fixtures — re-export global fixtures + PLM-specific models registration."""

from __future__ import annotations

# Re-export all global fixtures so pytest discovers them
from tests.conftest import *  # noqa: F401, F403

import pytest


@pytest.fixture(autouse=True)
def _register_plm_models() -> None:
    """Ensure PLM models are imported so metadata.create_all picks them up."""
    import packages.product_lifecycle.models  # noqa: F401
