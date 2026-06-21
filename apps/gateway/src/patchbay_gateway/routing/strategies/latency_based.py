"""Latency-based routing strategy — selects the fastest route.

Uses real-time latency metrics from Redis (sliding window p95)
to select the route with the lowest response time.

Best for:
  - Real-time applications (voice assistants, live coding)
  - User-facing chat where response time matters
  - Streaming workloads where first-token latency is critical
"""

from __future__ import annotations

import logging
from typing import Any

from patchbay_gateway.core.exceptions import NoHealthyRouteError
from patchbay_gateway.routing.strategies.base import RoutingStrategy

logger = logging.getLogger(__name__)


class LatencyBasedStrategy(RoutingStrategy):
    """Selects the route with lowest p95 latency.

    Latency data is stored in Redis as sorted sets with sliding windows.
    The routing engine updates these metrics after each request.
    """

    async def select(
        self,
        candidates: list[Any],
        request_context: dict[str, Any],
    ) -> Any:
        healthy = [r for r in candidates if r.is_healthy]
        if not healthy:
            raise NoHealthyRouteError(request_context.get("model", "unknown"))

        # Sort by average latency; routes without data get high default
        ranked = sorted(
            healthy,
            key=lambda r: r.avg_latency_ms if r.avg_latency_ms else 99999,
        )

        selected = ranked[0]
        logger.debug(
            "latency_strategy_selected",
            extra={
                "provider": selected.provider_key,
                "latency_ms": selected.avg_latency_ms or "unknown",
                "candidates": len(candidates),
            },
        )

        return selected
