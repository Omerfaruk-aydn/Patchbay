from __future__ import annotations

from typing import Any

from patchbay_gateway.core.exceptions import NoHealthyRouteError
from patchbay_gateway.routing.strategies.base import RoutingStrategy


class LatencyBasedStrategy(RoutingStrategy):
    """Selects the route with lowest p95 latency from Redis metrics."""

    async def select(
        self, candidates: list[Any], request_context: dict
    ) -> Any:
        healthy = [r for r in candidates if r.is_healthy]
        if not healthy:
            raise NoHealthyRouteError(request_context.get("model", "unknown"))

        # Sort by average latency, preferring routes with lower latency
        # Routes with no latency data get a high default
        ranked = sorted(
            healthy, key=lambda r: r.avg_latency_ms if r.avg_latency_ms else 99999
        )
        return ranked[0]
