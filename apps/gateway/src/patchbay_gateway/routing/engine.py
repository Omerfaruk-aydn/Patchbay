"""Routing engine — selects the optimal provider route for each request.

The engine implements a pipeline:
  1. Resolve logical model name → available provider routes
  2. Filter out unhealthy routes (circuit breaker)
  3. Apply routing strategy (cost, latency, semantic)
  4. Return selected route

Strategies are pluggable via the RoutingStrategy ABC. The engine
never makes HTTP calls itself — it delegates to ProviderAdapter.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from patchbay_gateway.core.exceptions import NoHealthyRouteError
from patchbay_gateway.routing.circuit_breaker import CircuitBreaker, CircuitState
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
    """Core routing engine that selects the best provider route.

    The engine is stateless — all state (circuit breaker, latency metrics)
    lives in Redis, enabling horizontal scaling of gateway instances.
    """

    def __init__(self, circuit_breaker: CircuitBreaker) -> None:
        self._circuit_breaker = circuit_breaker

    async def select_route(
        self,
        model_name: str,
        routes: list[Any],
        strategy_name: str = "cost_optimized",
        request_context: dict[str, Any] | None = None,
    ) -> Any:
        """Select the best route for a given model.

        Pipeline:
          1. Filter routes by is_active + is_healthy + circuit breaker state
          2. Sort remaining routes by priority (ascending)
          3. Apply routing strategy to select the best candidate

        Args:
            model_name: The logical model name requested by the client.
            routes: All available provider routes for this model.
            strategy_name: Which routing strategy to use.
            request_context: Full request context for strategy evaluation.

        Returns:
            The selected provider route object.

        Raises:
            NoHealthyRouteError: If no healthy route is available after filtering.
        """
        start = time.monotonic()

        healthy_routes: list[Any] = []
        circuit_open_count = 0

        for route in routes:
            if not route.is_active or not route.is_healthy:
                continue
            state = await self._circuit_breaker.get_state(str(route.id))
            if state == CircuitState.OPEN:
                circuit_open_count += 1
                continue
            healthy_routes.append(route)

        if not healthy_routes:
            logger.warning(
                "no_healthy_route",
                extra={
                    "model": model_name,
                    "total_routes": len(routes),
                    "circuit_open": circuit_open_count,
                },
            )
            raise NoHealthyRouteError(model_name)

        healthy_routes.sort(key=lambda r: getattr(r, "priority", 100))

        strategy_cls = STRATEGIES.get(strategy_name)
        if not strategy_cls:
            logger.warning(
                "unknown_strategy_fallback",
                extra={"strategy": strategy_name, "model": model_name},
            )
            strategy_cls = CostBasedStrategy

        strategy = strategy_cls()
        selected = await strategy.select(healthy_routes, request_context or {})

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "route_selected",
            extra={
                "model": model_name,
                "strategy": strategy_name,
                "provider": getattr(selected, "provider_key", "unknown"),
                "candidates": len(healthy_routes),
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )

        return selected
