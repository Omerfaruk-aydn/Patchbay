from __future__ import annotations

from typing import TYPE_CHECKING

from redis.asyncio import Redis

from patchbay_gateway.core.config import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_redis: Redis | None = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Dependency that provides a Redis connection."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield _redis


async def close_redis() -> None:
    """Close the Redis connection on shutdown."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
