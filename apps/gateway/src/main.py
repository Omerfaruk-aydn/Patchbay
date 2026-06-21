from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from patchbay_gateway.api.health import router as health_router
from patchbay_gateway.api.v1.router import router as v1_router
from patchbay_gateway.api.ws.live_metrics import router as ws_router
from patchbay_gateway.core.config import get_settings
from patchbay_gateway.core.database import engine
from patchbay_gateway.core.logging import setup_logging
from patchbay_gateway.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    import redis.asyncio as aioredis
    from patchbay_gateway.core.config import get_settings

    settings = get_settings()
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.close()
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(v1_router)
    app.include_router(ws_router)

    return app


app = create_app()
