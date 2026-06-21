from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from tests.conftest import FakeRoute
from patchbay_gateway.routing.strategies.cost_based import CostBasedStrategy, estimate_tokens


class TestEstimateTokens:
    def test_empty_messages(self) -> None:
        assert estimate_tokens([]) == 1

    def test_single_message(self) -> None:
        assert estimate_tokens([{"role": "user", "content": "hello world"}) == 2

    def test_multiple_messages(self) -> None:
        msgs = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        assert estimate_tokens(msgs) == 4  # "You are helpful" (16) + "Hello" (5) = 21 chars / 4 = 5


class TestCostBasedStrategy:
    def setup_method(self) -> None:
        self.strategy = CostBasedStrategy()

    @pytest.mark.asyncio
    async def test_selects_cheapest_healthy_route(self) -> None:
        cheap = FakeRoute(
            id="cheap",
            pricing_input_per_million_cents=10,
            pricing_output_per_million_cents=30,
        )
        expensive = FakeRoute(
            id="expensive",
            pricing_input_per_million_cents=100,
            pricing_output_per_million_cents=300,
        )
        result = await self.strategy.select(
            [cheap, expensive],
            {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 100},
        )
        assert result.id == "cheap"

    @pytest.mark.asyncio
    async def test_skips_unhealthy_routes(self) -> None:
        unhealthy = FakeRoute(id="unhealthy", is_healthy=False)
        healthy = FakeRoute(id="healthy")
        result = await self.strategy.select(
            [unhealthy, healthy],
            {"messages": [{"role": "user", "content": "hi"}]},
        )
        assert result.id == "healthy"

    @pytest.mark.asyncio
    async def test_raises_when_no_healthy(self) -> None:
        from patchbay_gateway.core.exceptions import NoHealthyRouteError

        with pytest.raises(NoHealthyRouteError):
            await self.strategy.select(
                [FakeRoute(id="x", is_healthy=False)],
                {"messages": [], "model": "test"},
            )
