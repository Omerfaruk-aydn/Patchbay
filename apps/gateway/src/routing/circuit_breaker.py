from __future__ import annotations

import json
import logging
import time
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Redis-backed circuit breaker with three states.

    CLOSED → normal operation
    OPEN → route disabled, waiting for cooldown
    HALF_OPEN → testing with a single request
    """

    def __init__(self, redis: Any, failure_threshold: int = 5, cooldown_seconds: int = 30) -> None:
        self._redis = redis
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds

    def _key(self, route_id: str) -> str:
        return f"circuit:{route_id}"

    async def get_state(self, route_id: str) -> CircuitState:
        data = await self._redis.hget(self._key(route_id), "state")
        if data is None:
            return CircuitState.CLOSED
        state = CircuitState(data)
        if state == CircuitState.OPEN:
            opened_at = await self._redis.hget(self._key(route_id), "opened_at")
            if opened_at and (time.time() - float(opened_at)) > self._cooldown_seconds:
                await self._redis.hset(self._key(route_id), "state", CircuitState.HALF_OPEN)
                return CircuitState.HALF_OPEN
        return state

    async def record_success(self, route_id: str) -> None:
        await self._redis.hset(self._key(route_id), "state", CircuitState.CLOSED)
        await self._redis.hset(self._key(route_id), "failures", "0")

    async def record_failure(self, route_id: str) -> None:
        failures = int(await self._redis.hget(self._key(route_id), "failures") or "0")
        failures += 1
        await self._redis.hset(self._key(route_id), "failures", str(failures))

        if failures >= self._failure_threshold:
            await self._redis.hset(self._key(route_id), "state", CircuitState.OPEN)
            await self._redis.hset(self._key(route_id), "opened_at", str(time.time()))
            logger.warning("circuit_opened", extra={"route_id": route_id, "failures": failures})

    async def is_available(self, route_id: str) -> bool:
        state = await self.get_state(route_id)
        return state != CircuitState.OPEN
