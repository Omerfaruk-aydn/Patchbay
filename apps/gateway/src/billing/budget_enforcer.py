from __future__ import annotations

from decimal import Decimal
from typing import Any

from patchbay_gateway.core.exceptions import BudgetExceededError


class BudgetEnforcer:
    """Hard budget enforcement — checks budget before request is sent."""

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    def _spend_key(self, virtual_key_id: str) -> str:
        return f"budget:{virtual_key_id}:monthly"

    async def get_month_to_date_spend(self, virtual_key_id: str) -> Decimal:
        spend = await self._redis.get(self._spend_key(virtual_key_id))
        return Decimal(spend or "0")

    async def check_and_reserve(self, virtual_key: Any, estimated_cost: Decimal) -> None:
        if not virtual_key.budget_usd_cents:
            return

        current = await self.get_month_to_date_spend(str(virtual_key.id))
        if (current + estimated_cost) > virtual_key.budget_usd_cents:
            raise BudgetExceededError(
                str(virtual_key.id),
                float(current),
                float(virtual_key.budget_usd_cents),
            )

    async def record_spend(self, virtual_key_id: str, cost: Decimal) -> None:
        key = self._spend_key(virtual_key_id)
        await self._redis.incrbyfloat(key, float(cost))
