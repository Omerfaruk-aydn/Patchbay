"""Redis connection management with connection pooling.

Provides:
  - Singleton Redis connection (lazy initialization)
  - Per-request dependency for FastAPI
  - Graceful shutdown

Connection pool:
  - max_connections: 20
  - retry_on_timeout: True
  - socket_connect_timeout: 5s
  - socket_timeout: 5s
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from patchbay_gateway.core.config import get_settings

_redis: aioredis.Redis | None = None


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency that provides a Redis connection from the pool."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    yield _redis


async def close_redis() -> None:
    """Close the Redis connection on application shutdown."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
