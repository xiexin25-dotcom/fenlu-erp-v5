"""分路链式 V5.0 API Gateway 入口。

启动:
    uv run uvicorn apps.api_gateway.main:app --reload --port 8000
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from packages.management_decision.api.routes import router as mgmt_router
from packages.product_lifecycle.api.routes import router as plm_router
from packages.production.api.routes import router as mfg_router
from packages.supply_chain.api.routes import router as scm_router

from apps.api_gateway.routers import auth, health, orgs
from apps.api_gateway.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动时可在此预热缓存、连接池
    yield
    # 关闭时清理
    from packages.shared.db import get_engine

    await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="分路链式工业互联网系统 V5.0",
        version="0.1.0",
        description="工信部 2024 版三级集成级 · 16 场景全覆盖",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(orgs.router)
    # Lane routers (stubs until each lane is built out)
    app.include_router(plm_router)
    app.include_router(mfg_router)
    app.include_router(scm_router)
    app.include_router(mgmt_router)
    return app


app = create_app()
