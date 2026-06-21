"""Learned routing strategy — Phase 2 placeholder.

Future implementation using:
  - Multi-armed bandit (Thompson Sampling or epsilon-greedy)
  - Gradient boosting on historical request data
  - Real-time quality feedback loop

Interface is defined now so the routing engine can reference it
without code changes when Phase 2 is implemented.
"""

from __future__ import annotations

from typing import Any

from patchbay_gateway.routing.strategies.base import RoutingStrategy


class LearnedRoutingStrategy(RoutingStrategy):
    """Phase 2 placeholder — not yet implemented.

    When implemented, this strategy will:
    1. Analyze historical request data (task category, route, cost, quality)
    2. Train a lightweight model to predict optimal route selection
    3. Continuously learn from new requests and feedback

    The strategy interface is defined now for forward compatibility.
    """

    async def select(
        self,
        candidates: list[Any],
        request_context: dict[str, Any],
    ) -> Any:
        raise NotImplementedError(
            "Learned routing is a Phase 2 feature. "
            "Use cost_optimized, latency_optimized, or semantic strategies instead."
        )
