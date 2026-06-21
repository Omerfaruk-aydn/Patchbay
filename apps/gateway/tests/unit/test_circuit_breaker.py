from __future__ import annotations

import pytest
import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from tests.conftest import FakeRedis
from patchbay_gateway.routing.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def setup_method(self) -> None:
        self.redis = FakeRedis()
        self.breaker = CircuitBreaker(
            self.redis, failure_threshold=3, cooldown_seconds=1
        )

    @pytest.mark.asyncio
    async def test_starts_closed(self) -> None:
        state = await self.breaker.get_state("route-1")
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self) -> None:
        for _ in range(3):
            await self.breaker.record_failure("route-1")
        state = await self.breaker.get_state("route-1")
        assert state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_not_available_when_open(self) -> None:
        for _ in range(3):
            await self.breaker.record_failure("route-1")
        assert await self.breaker.is_available("route-1") is False

    @pytest.mark.asyncio
    async def test_success_resets_failures(self) -> None:
        await self.breaker.record_failure("route-1")
        await self.breaker.record_success("route-1")
        state = await self.breaker.get_state("route-1")
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_available_when_closed(self) -> None:
        assert await self.breaker.is_available("route-1") is True
