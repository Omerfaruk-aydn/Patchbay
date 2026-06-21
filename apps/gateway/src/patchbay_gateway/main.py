"""FastAPI application factory for Patchbay Gateway.

Creates the application with:
  - CORS middleware (configurable origins)
  - Structured JSON logging
  - Redis + database connection lifecycle management
  - OpenTelemetry instrumentation (optional)
  - Health check, v1 API, and WebSocket endpoints
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from patchbay_gateway.api.health import router as health_router
from patchbay_gateway.api.v1.router import router as v1_router
from patchbay_gateway.api.ws.live_metrics import router as ws_router
from patchbay_gateway.core.config import get_settings
from patchbay_gateway.core.database import engine
from patchbay_gateway.core.exceptions import PatchbayError
from patchbay_gateway.core.logging import setup_logging
from patchbay_gateway.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — initialize and teardown resources."""
    settings = get_settings()
    setup_logging()

    import redis.asyncio as aioredis

    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20,
        retry_on_timeout=True,
    )

    try:
        await app.state.redis.ping()
    except Exception:
        pass

    yield

    if hasattr(app.state, "redis") and app.state.redis:
        await app.state.redis.close()
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Universal LLM Gateway & Orchestration Platform",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(PatchbayError)
    async def patchbay_error_handler(request, exc: PatchbayError):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    app.include_router(health_router)
    app.include_router(v1_router, prefix="/v1")
    app.include_router(ws_router)

    return app


app = create_app()
