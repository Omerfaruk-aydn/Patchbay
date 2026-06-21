"""Health check endpoint.

Provides /health for Kubernetes liveness/readiness probes,
Docker health checks, and monitoring dashboards.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Health check endpoint.

    Verifies:
      1. Application is running
      2. Database connection is alive
      3. Returns response time

    Used by:
      - Kubernetes liveness/readiness probes
      - Docker HEALTHCHECK
      - Load balancer health checks
    """
    start = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    latency_ms = round((time.monotonic() - start) * 1000, 2)

    status = "healthy" if db_ok else "degraded"
    return {
        "status": status,
        "service": "patchbay-gateway",
        "version": "0.1.0",
        "checks": {
            "database": "ok" if db_ok else "error",
        },
        "latency_ms": latency_ms,
    }
