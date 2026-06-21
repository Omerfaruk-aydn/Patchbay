"""Hard budget enforcement — blocks requests before they exceed budget.

Design principle: Budget checks are "hard" (pre-request blocking), not
"soft" (post-request logging). This prevents runaway costs from
application errors or unexpected traffic spikes.

Budget hierarchy (future):
  organization.monthly_budget → org-level cap
  project.monthly_budget → project-level cap
  virtual_key.budget_usd_cents → key-level cap
  The most restrictive limit applies.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from patchbay_gateway.core.exceptions import BudgetExceededError

logger = logging.getLogger(__name__)


class BudgetEnforcer:
    """Hard budget enforcement — checks budget before request is sent.

    Uses Redis INCRBYFLOAT for atomic spend tracking with per-month keys.
    Budget thresholds (80%, 100%) trigger alerts via AlertManager.
    """

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    def _spend_key(self, virtual_key_id: str) -> str:
        """Redis key for monthly spend counter."""
        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        return f"budget:{virtual_key_id}:{month}"

    async def get_month_to_date_spend(self, virtual_key_id: str) -> Decimal:
        """Get total spend for the current month."""
        key = self._spend_key(virtual_key_id)
        spend = await self._redis.get(key)
        return Decimal(spend or "0")

    async def check_and_reserve(self, virtual_key: Any, estimated_cost: Decimal) -> None:
        """Check if the request would exceed the budget.

        Raises:
            BudgetExceededError: If the budget would be exceeded.
        """
        if not virtual_key.budget_usd_cents:
            return

        current = await self.get_month_to_date_spend(str(virtual_key.id))
        if (current + estimated_cost) > virtual_key.budget_usd_cents:
            logger.warning(
                "budget_exceeded",
                extra={
                    "key_id": str(virtual_key.id),
                    "current_spend": float(current),
                    "budget": float(virtual_key.budget_usd_cents),
                    "estimated_cost": float(estimated_cost),
                },
            )
            raise BudgetExceededError(
                str(virtual_key.id),
                float(current),
                float(virtual_key.budget_usd_cents),
            )

    async def record_spend(self, virtual_key_id: str, cost: Decimal) -> None:
        """Record actual spend after a successful request."""
        key = self._spend_key(virtual_key_id)
        await self._redis.incrbyfloat(key, float(cost))

    async def get_budget_usage_percentage(self, virtual_key: Any) -> float:
        """Get budget usage as a percentage (0-100+)."""
        if not virtual_key.budget_usd_cents:
            return 0.0
        current = await self.get_month_to_date_spend(str(virtual_key.id))
        return float(current) / float(virtual_key.budget_usd_cents) * 100
