"""Token-bucket rate limiter using Redis Lua scripts for atomicity.

Rate limits are enforced per virtual key using a sliding window approach.
The Lua script ensures atomic INCR + EXPIRE operations to prevent race conditions.

Rate limit hierarchy:
  virtual_key.rate_limit_rpm → per-key limit
  (future: project-level, organization-level limits)
"""

from __future__ import annotations

import logging
from typing import Any

from patchbay_gateway.core.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)

# Lua script for atomic rate limit check:
# INCR the counter, set TTL on first request, check against limit
RATE_LIMIT_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end
if current > limit then
    return 0
else
    return 1
end
"""


class RateLimiter:
    """Redis-based rate limiter using Lua scripts for atomic operations.

    Each virtual key gets a Redis counter with a sliding window.
    The counter resets after the window expires.
    """

    def __init__(self, redis: Any) -> None:
        self._redis = redis
        self._script = None

    async def _ensure_script(self) -> None:
        if self._script is None:
            self._script = self._redis.register_script(RATE_LIMIT_LUA)

    def _key(self, virtual_key_id: str) -> str:
        return f"ratelimit:{virtual_key_id}"

    async def check(self, virtual_key: Any) -> None:
        """Check rate limit for a virtual key.

        Raises:
            RateLimitExceededError: If the rate limit is exceeded.
        """
        if not virtual_key.rate_limit_rpm:
            return

        await self._ensure_script()
        key = self._key(str(virtual_key.id))

        try:
            allowed = await self._script(
                keys=[key],
                args=[virtual_key.rate_limit_rpm, 60],
            )
        except Exception as e:
            logger.error("rate_limit_check_failed", extra={"key_id": str(virtual_key.id), "error": str(e)})
            return

        if not allowed:
            raise RateLimitExceededError(str(virtual_key.id), virtual_key.rate_limit_rpm)

    async def get_current_usage(self, virtual_key_id: str) -> int:
        """Get current request count in the window."""
        key = self._key(virtual_key_id)
        count = await self._redis.get(key)
        return int(count) if count else 0
