from __future__ import annotations

from typing import Any

from patchbay_gateway.core.config import get_settings


class AlertManager:
    """Budget threshold alert manager.

    Sends webhook/email alerts when spending approaches budget limits.
    """

    def __init__(self, redis: Any) -> None:
        self._redis = redis
        self._settings = get_settings()

    async def check_and_alert(self, virtual_key: Any, current_spend: float) -> None:
        if not virtual_key.budget_usd_cents:
            return

        budget = float(virtual_key.budget_usd_cents)
        percentage = (current_spend / budget) * 100 if budget > 0 else 0

        thresholds = [80, 100]
        for threshold in thresholds:
            if percentage >= threshold:
                alert_key = f"alert:{virtual_key.id}:{threshold}"
                already_alerted = await self._redis.get(alert_key)
                if not already_alerted:
                    await self._alert(virtual_key, current_spend, budget, threshold)
                    await self._redis.setex(alert_key, 86400, "1")

    async def _alert(
        self, virtual_key: Any, current: float, budget: float, threshold: int
    ) -> None:
        # In production, send webhook or email
        pass
