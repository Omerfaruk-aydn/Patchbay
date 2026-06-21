from __future__ import annotations

from typing import Any

from patchbay_gateway.routing.strategies.base import RoutingStrategy


class LearnedRoutingStrategy(RoutingStrategy):
    """Phase 2 placeholder — interface only.

    In the future, this uses historical request data to learn
    optimal route selection via multi-armed bandit or gradient boosting.
    """

    async def select(
        self, candidates: list[Any], request_context: dict
    ) -> Any:
        raise NotImplementedError("Learned routing is a Phase 2 feature")
