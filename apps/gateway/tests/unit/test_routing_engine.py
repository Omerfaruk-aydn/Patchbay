from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from tests.conftest import FakeRoute, FakeRedis
from patchbay_gateway.routing.engine import RoutingEngine
from patchbay_gateway.routing.circuit_breaker import CircuitBreaker
from patchbay_gateway.core.exceptions import NoHealthyRouteError


class TestRoutingEngine:
    def setup_method(self) -> None:
        self.redis = FakeRedis()
        self.breaker = CircuitBreaker(self.redis)
        self.engine = RoutingEngine(self.breaker)

    @pytest.mark.asyncio
    async def test_selects_cheapest_route(self) -> None:
        routes = [
            FakeRoute(id="r1", pricing_input_per_million_cents=100),
            FakeRoute(id="r2", pricing_input_per_million_cents=10),
            FakeRoute(id="r3", pricing_input_per_million_cents=50),
        ]
        result = await self.engine.select_route(
            "gpt-4", routes, "cost_optimized",
            {"messages": [{"role": "user", "content": "hi"}]},
        )
        assert result.id == "r2"

    @pytest.mark.asyncio
    async def test_skips_unhealthy_routes(self) -> None:
        routes = [
            FakeRoute(id="r1", is_healthy=False),
            FakeRoute(id="r2", is_healthy=True),
        ]
        result = await self.engine.select_route("gpt-4", routes)
        assert result.id == "r2"

    @pytest.mark.asyncio
    async def test_raises_when_no_healthy(self) -> None:
        routes = [FakeRoute(id="r1", is_healthy=False)]
        with pytest.raises(NoHealthyRouteError):
            await self.engine.select_route("gpt-4", routes)
