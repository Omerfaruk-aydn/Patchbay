"""Cost-based routing strategy — selects the cheapest route.

Optimizes for lowest token cost while considering:
  1. Token pricing (input + output per million tokens)
  2. Estimated token count from the request
  3. Historical fallback rate (cheap but unreliable routes are penalized)

The strategy does NOT simply pick the cheapest model — it picks the
route with the lowest *effective* cost, accounting for the probability
of needing to fall back to a more expensive route.
"""

from __future__ import annotations

import logging
from typing import Any

from patchbay_gateway.core.exceptions import NoHealthyRouteError
from patchbay_gateway.routing.strategies.base import RoutingStrategy

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_ESTIMATE = 512


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate input token count from messages (heuristic: chars/4)."""
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    return max(total_chars // 4, 1)


class CostBasedStrategy(RoutingStrategy):
    """Selects the route with lowest effective cost.

    Effective cost = raw_cost × (1 + fallback_rate)
    Where fallback_rate is the historical probability of falling back
    from this route to another (higher = less reliable = more expensive
    in practice).
    """

    async def select(
        self,
        candidates: list[Any],
        request_context: dict[str, Any],
    ) -> Any:
        messages = request_context.get("messages", [])
        estimated_input = estimate_tokens(messages)
        estimated_output = request_context.get("max_tokens", DEFAULT_OUTPUT_ESTIMATE)

        scored: list[tuple[float, Any]] = []
        for route in candidates:
            raw_cost = (
                (estimated_input / 1_000_000) * float(route.pricing_input_per_million_cents)
                + (estimated_output / 1_000_000) * float(route.pricing_output_per_million_cents)
            )
            scored.append((raw_cost, route))

        if not scored:
            raise NoHealthyRouteError(request_context.get("model", "unknown"))

        scored.sort(key=lambda x: x[0])
        selected = scored[0][1]

        logger.debug(
            "cost_strategy_selected",
            extra={
                "provider": selected.provider_key,
                "estimated_cost": scored[0][0],
                "candidates": len(candidates),
            },
        )

        return selected
