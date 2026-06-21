from __future__ import annotations

from typing import Any

from patchbay_gateway.core.exceptions import RateLimitExceededError

RATE_LIMIT_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then redis.call('EXPIRE', key, window) end
if current > limit then return 0 else return 1 end
"""


class RateLimiter:
    """Redis token-bucket rate limiter using Lua script for atomicity."""

    def __init__(self, redis: Any) -> None:
        self._redis = redis
        self._script = self._redis.register_script(RATE_LIMIT_LUA)

    def _key(self, virtual_key_id: str) -> str:
        return f"ratelimit:{virtual_key_id}"

    async def check(self, virtual_key: Any) -> None:
        if not virtual_key.rate_limit_rpm:
            return

        key = self._key(str(virtual_key.id))
        allowed = await self._script(
            keys=[key],
            args=[virtual_key.rate_limit_rpm, 60],
        )
        if not allowed:
            raise RateLimitExceededError(
                str(virtual_key.id), virtual_key.rate_limit_rpm
            )
