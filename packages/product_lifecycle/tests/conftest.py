"""PLM test fixtures — re-export global fixtures + PLM-specific models registration."""

from __future__ import annotations

# Re-export all global fixtures so pytest discovers them
from tests.conftest import *  # noqa: F401, F403

import pytest

# Import once at module level so models register exactly once
import packages.product_lifecycle.models  # noqa: F401
