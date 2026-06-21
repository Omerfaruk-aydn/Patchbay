from __future__ import annotations

from decimal import Decimal
from typing import Any

from patchbay_gateway.core.exceptions import NoHealthyRouteError
from patchbay_gateway.routing.strategies.base import RoutingStrategy

DEFAULT_OUTPUT_ESTIMATE = 512


def estimate_tokens(messages: list[dict]) -> int:
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return max(total_chars // 4, 1)


class CostBasedStrategy(RoutingStrategy):
    """Selects the route with lowest effective cost.

    Effective cost considers both token pricing and fallback rate —
    a cheap but unreliable route is penalized.
    """

    async def select(
        self, candidates: list[Any], request_context: dict
    ) -> Any:
        estimated_input = estimate_tokens(request_context.get("messages", []))
        estimated_output = request_context.get("max_tokens", DEFAULT_OUTPUT_ESTIMATE)

        scored: list[tuple[float, Any]] = []
        for route in candidates:
            if not route.is_healthy:
                continue
            raw_cost = (
                (estimated_input / 1_000_000)
                * float(route.pricing_input_per_million_cents)
                + (estimated_output / 1_000_000)
                * float(route.pricing_output_per_million_cents)
            )
            scored.append((raw_cost, route))

        if not scored:
            raise NoHealthyRouteError(request_context.get("model", "unknown"))

        scored.sort(key=lambda x: x[0])
        return scored[0][1]
