"""BomClient · TASK-MFG-003。

跨 lane HTTP 调用 Lane 1 (PLM) 获取 BOM。
"""

from __future__ import annotations

import os
from uuid import UUID

import httpx

from packages.shared.contracts.product_lifecycle import BOMDTO

PLM_BASE_URL = os.getenv("PLM_BASE_URL", "http://localhost:8001")


class BomNotFoundError(Exception):
    def __init__(self, bom_id: UUID) -> None:
        self.bom_id = bom_id
        super().__init__(f"BOM {bom_id} not found in PLM")


class BomClient:
    """Async HTTP client for fetching BOMs from Lane 1."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def get_bom(self, bom_id: UUID) -> BOMDTO:
        client = self._client or httpx.AsyncClient(base_url=PLM_BASE_URL, timeout=10.0)
        should_close = self._client is None
        try:
            resp = await client.get(f"/plm/bom/{bom_id}")
            if resp.status_code == 404:
                raise BomNotFoundError(bom_id)
            resp.raise_for_status()
            return BOMDTO.model_validate(resp.json())
        finally:
            if should_close:
                await client.aclose()
