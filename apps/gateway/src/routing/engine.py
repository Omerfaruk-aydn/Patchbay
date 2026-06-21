from __future__ import annotations

import logging
from typing import Any

from patchbay_gateway.core.exceptions import NoHealthyRouteError
from patchbay_gateway.routing.circuit_breaker import CircuitBreaker
from patchbay_gateway.routing.strategies.base import RoutingStrategy
from patchbay_gateway.routing.strategies.cost_based import CostBasedStrategy
from patchbay_gateway.routing.strategies.latency_based import LatencyBasedStrategy
from patchbay_gateway.routing.strategies.semantic import SemanticRoutingStrategy

logger = logging.getLogger(__name__)

STRATEGIES: dict[str, type[RoutingStrategy]] = {
    "cost_optimized": CostBasedStrategy,
    "latency_optimized": LatencyBasedStrategy,
    "semantic": SemanticRoutingStrategy,
}


class RoutingEngine:
    """Core routing engine that selects the best provider route."""

    def __init__(self, circuit_breaker: CircuitBreaker) -> None:
        self._circuit_breaker = circuit_breaker

    async def select_route(
        self,
        model_name: str,
        routes: list[Any],
        strategy_name: str = "cost_optimized",
        request_context: dict | None = None,
    ) -> Any:
        """Select the best route for a given model.

        Args:
            model_name: The logical model name requested.
            routes: All available routes for this model.
            strategy_name: Which routing strategy to use.
            request_context: Full request context for strategy evaluation.

        Returns:
            The selected provider route.

        Raises:
            NoHealthyRouteError: If no healthy route is available.
        """
        healthy_routes = [
            r
            for r in routes
            if r.is_active and r.is_healthy and await self._circuit_breaker.is_available(str(r.id))
        ]

        if not healthy_routes:
            raise NoHealthyRouteError(model_name)

        strategy_cls = STRATEGIES.get(strategy_name, CostBasedStrategy)
        strategy = strategy_cls()
        return await strategy.select(healthy_routes, request_context or {})
