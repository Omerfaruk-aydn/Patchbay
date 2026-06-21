from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RoutingStrategy(ABC):
    """Abstract base for routing strategies."""

    @abstractmethod
    async def select(
        self, candidates: list[Any], request_context: dict
    ) -> Any:
        """Select the best route from healthy candidates."""
        ...
