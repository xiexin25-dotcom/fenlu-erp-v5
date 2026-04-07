"""
SCM · Lane 1 BOM 客户端
========================

通过 REST 调用 Lane 1 获取 BOM 详情。
遵循跨 lane 硬规则: 绝不直接 import Lane 1 SQLAlchemy 模型,
只使用 shared/contracts 中的 Pydantic DTO。

测试时注入 InMemoryBOMClient。
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

import httpx

from packages.shared.contracts.product_lifecycle import BOMDTO

PLM_BASE_URL = "http://localhost:8001"


class BOMClient(Protocol):
    """获取 BOM 详情的接口协议。"""

    async def get_bom(self, bom_id: UUID) -> BOMDTO | None: ...


class HttpBOMClient:
    """生产环境: 通过 HTTP 调用 Lane 1 PLM 服务。"""

    def __init__(self, base_url: str = PLM_BASE_URL) -> None:
        self._base_url = base_url

    async def get_bom(self, bom_id: UUID) -> BOMDTO | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/plm/boms/{bom_id}")
                if resp.status_code == 200:
                    return BOMDTO.model_validate(resp.json())
                return None
        except httpx.HTTPError:
            return None


class InMemoryBOMClient:
    """测试用: 预注册 BOM 数据。"""

    def __init__(self) -> None:
        self._store: dict[UUID, dict[str, Any]] = {}

    def register_bom(self, bom_data: dict[str, Any]) -> None:
        """注册一个 BOM (原始 dict,会在 get_bom 时校验)。"""
        bom_id = UUID(str(bom_data["id"]))
        self._store[bom_id] = bom_data

    async def get_bom(self, bom_id: UUID) -> BOMDTO | None:
        raw = self._store.get(bom_id)
        if raw is None:
            return None
        return BOMDTO.model_validate(raw)
