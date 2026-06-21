"""Redis-backed circuit breaker with three states.

Implements the classic circuit breaker pattern:
  CLOSED  → Normal operation. Failures increment a counter.
  OPEN    → Route disabled. After cooldown, transitions to HALF_OPEN.
  HALF_OPEN → One test request allowed. Success → CLOSED, failure → OPEN.

State is stored in Redis hashes (`circuit:{route_id}`) so all gateway
instances share the same view — a single instance can't mask a failing
provider from others.

Configuration:
  - failure_threshold: Number of consecutive failures to trip the breaker (default: 5)
  - cooldown_seconds: Time to wait in OPEN before testing (default: 30)
  - half_open_max_requests: Requests allowed in HALF_OPEN (default: 1)
"""

from __future__ import annotations

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
    """Redis-backed circuit breaker with exponential backoff on repeated failures."""

    def __init__(
        self,
        redis: Any,
        failure_threshold: int = 5,
        cooldown_seconds: int = 30,
        max_cooldown_seconds: int = 300,
    ) -> None:
        self._redis = redis
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._max_cooldown = max_cooldown_seconds

    def _key(self, route_id: str) -> str:
        return f"circuit:{route_id}"

    async def get_state(self, route_id: str) -> CircuitState:
        key = self._key(route_id)
        state_str = await self._redis.hget(key, "state")
        if state_str is None:
            return CircuitState.CLOSED

        state = CircuitState(state_str)

        if state == CircuitState.OPEN:
            opened_at = await self._redis.hget(key, "opened_at")
            cooldown = await self._redis.hget(key, "cooldown")
            if opened_at and cooldown:
                elapsed = time.time() - float(opened_at)
                if elapsed >= float(cooldown):
                    await self._redis.hset(key, "state", CircuitState.HALF_OPEN)
                    await self._redis.hset(key, "half_open_requests", "0")
                    return CircuitState.HALF_OPEN

        return state

    async def record_success(self, route_id: str) -> None:
        key = self._key(route_id)
        current_state = await self.get_state(route_id)

        if current_state == CircuitState.HALF_OPEN:
            await self._redis.hset(key, "state", CircuitState.CLOSED)
            await self._redis.hset(key, "failures", "0")
            await self._redis.hset(key, "cooldown", str(self._cooldown_seconds))
            logger.info("circuit_closed_from_half_open", extra={"route_id": route_id})

        elif current_state == CircuitState.CLOSED:
            await self._redis.hset(key, "failures", "0")

    async def record_failure(self, route_id: str) -> None:
        key = self._key(route_id)
        failures = int(await self._redis.hget(key, "failures") or "0")
        failures += 1
        await self._redis.hset(key, "failures", str(failures))
        await self._redis.hset(key, "last_failure", str(time.time()))

        if failures >= self._failure_threshold:
            current_cooldown = int(await self._redis.hget(key, "cooldown") or self._cooldown_seconds)
            new_cooldown = min(current_cooldown * 2, self._max_cooldown)

            await self._redis.hset(key, "state", CircuitState.OPEN)
            await self._redis.hset(key, "opened_at", str(time.time()))
            await self._redis.hset(key, "cooldown", str(new_cooldown))

            logger.warning(
                "circuit_opened",
                extra={
                    "route_id": route_id,
                    "failures": failures,
                    "cooldown": new_cooldown,
                },
            )

    async def is_available(self, route_id: str) -> bool:
        state = await self.get_state(route_id)
        if state == CircuitState.OPEN:
            return False
        if state == CircuitState.HALF_OPEN:
            key = self._key(route_id)
            requests = int(await self._redis.hget(key, "half_open_requests") or "0")
            if requests >= 1:
                return False
            await self._redis.hinincrby(key, "half_open_requests", 1)
        return True

    async def get_metrics(self, route_id: str) -> dict[str, Any]:
        key = self._key(route_id)
        data = await self._redis.hgetall(key)
        return {
            "state": data.get("state", CircuitState.CLOSED),
            "failures": int(data.get("failures", 0)),
            "last_failure": data.get("last_failure"),
            "opened_at": data.get("opened_at"),
            "cooldown": int(data.get("cooldown", self._cooldown_seconds)),
        }
