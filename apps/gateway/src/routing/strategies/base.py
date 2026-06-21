"""Routing strategy base class and strategy interface.

All routing strategies implement this interface. The routing engine
selects a strategy based on the project's routing policy and calls
`select()` to choose the best route from healthy candidates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RoutingStrategy(ABC):
    """Abstract base class for routing strategies.

    Each strategy selects the best route from a list of healthy candidates
    based on different optimization criteria (cost, latency, semantic match).
    """

    @abstractmethod
    async def select(
        self,
        candidates: list[Any],
        request_context: dict[str, Any],
    ) -> Any:
        """Select the best route from healthy candidates.

        Args:
            candidates: List of healthy ProviderRoute objects.
            request_context: Full request context (model, messages, etc.).

        Returns:
            The selected ProviderRoute object.
        """
        ...
