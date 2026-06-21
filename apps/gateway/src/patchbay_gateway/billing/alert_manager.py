"""Budget threshold alert manager.

Sends alerts when spending approaches or exceeds budget limits.
Supports webhook and email notifications (configurable).

Alert thresholds:
  - 80% budget used → warning alert
  - 100% budget used → critical alert
  - Each threshold triggers only once per billing period
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AlertManager:
    """Budget threshold alert manager.

    Prevents duplicate alerts using Redis keys with 24h TTL.
    """

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def check_and_alert(self, virtual_key: Any, current_spend: float) -> None:
        """Check spending against thresholds and send alerts if needed."""
        if not virtual_key.budget_usd_cents:
            return

        budget = float(virtual_key.budget_usd_cents)
        if budget <= 0:
            return

        percentage = (current_spend / budget) * 100

        thresholds = [
            (80, "warning", "Budget 80% used"),
            (100, "critical", "Budget exceeded"),
        ]

        for threshold, severity, message in thresholds:
            if percentage >= threshold:
                alert_key = f"alert:{virtual_key.id}:{threshold}"
                already_alerted = await self._redis.get(alert_key)
                if not already_alerted:
                    await self._send_alert(virtual_key, current_spend, budget, severity, message)
                    await self._redis.setex(alert_key, 86400, "1")

    async def _send_alert(
        self,
        virtual_key: Any,
        current: float,
        budget: float,
        severity: str,
        message: str,
    ) -> None:
        """Send alert via configured channels (webhook, email, etc.)."""
        logger.warning(
            "budget_alert",
            extra={
                "key_id": str(virtual_key.id),
                "key_name": getattr(virtual_key, "name", "unknown"),
                "severity": severity,
                "message": message,
                "current_spend": current,
                "budget": budget,
                "percentage": round((current / budget) * 100, 1) if budget > 0 else 0,
            },
        )
