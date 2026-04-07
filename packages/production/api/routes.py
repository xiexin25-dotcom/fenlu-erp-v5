"""Lane: production · API routes (stub)。

Claude Code: replace this file with your real routers as you build out
the lane. Keep route paths under /mfg/ to match the Lane prefix
defined in apps/api_gateway/main.py.
"""

from __future__ import annotations

from fastapi import APIRouter

from packages.production.api.work_orders import router as wo_router

router = APIRouter(prefix="/mfg", tags=["production"])
router.include_router(wo_router)


@router.get("/health")
async def health() -> dict[str, str]:
    """Lane-level health probe."""
    return {"status": "ok", "lane": "production"}
