from __future__ import annotations

import logging
from typing import Any

from patchbay_gateway.core.exceptions import (
    AllRoutesExhaustedError,
    ProviderServerError,
    ProviderTimeoutError,
)
from patchbay_gateway.providers.registry import ProviderRegistry
from patchbay_gateway.routing.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


async def execute_with_fallback(
    primary_route: Any,
    fallback_routes: list[Any],
    request_context: dict,
    circuit_breaker: CircuitBreaker,
) -> tuple[Any, list[str]]:
    """Execute request with fallback chain.

    Returns (response, attempted_route_ids).
    """
    attempted: list[str] = []

    for route in [primary_route, *fallback_routes]:
        if not await circuit_breaker.is_available(str(route.id)):
            continue

        attempted.append(str(route.id))
        try:
            adapter = ProviderRegistry.get_adapter(route.provider_key)
            normalized = adapter.normalize_request(request_context)
            response = await adapter.send(route, normalized)
            await circuit_breaker.record_success(str(route.id))
            return response, attempted
        except (ProviderTimeoutError, ProviderRateLimitError, ProviderServerError) as e:
            await circuit_breaker.record_failure(str(route.id))
            logger.warning(
                "route_failed",
                extra={"route_id": str(route.id), "error": str(e)},
            )
            continue

    raise AllRoutesExhaustedError(attempted)
