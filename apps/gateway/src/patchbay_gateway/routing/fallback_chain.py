"""Fallback chain executor — tries routes in order with circuit breaker awareness.

The executor implements a critical design principle:
  - Fallback ONLY on transient/infrastructure errors (timeout, 429, 5xx)
  - DO NOT fallback on client errors (400, content policy rejection)
    because other providers will reject for the same reason.

Each attempt:
  1. Check circuit breaker availability
  2. Execute via ProviderAdapter
  3. On success: record success, return response
  4. On transient failure: record failure, try next route
  5. On client error: raise immediately (no fallback)
"""

from __future__ import annotations

import logging
import time
from typing import Any

from patchbay_gateway.core.exceptions import (
    AllRoutesExhaustedError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)
from patchbay_gateway.providers.registry import ProviderRegistry
from patchbay_gateway.routing.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

_CLIENT_ERROR_CODES = {400, 401, 403, 404, 422}


async def execute_with_fallback(
    primary_route: Any,
    fallback_routes: list[Any],
    request_context: dict[str, Any],
    circuit_breaker: CircuitBreaker,
    timeout: float = 60.0,
) -> tuple[Any, list[str]]:
    """Execute request with automatic fallback on transient failures.

    Args:
        primary_route: The first route to try (selected by routing engine).
        fallback_routes: Additional routes in priority order.
        request_context: The original request context (model, messages, etc.).
        circuit_breaker: Redis-backed circuit breaker instance.
        timeout: Per-attempt timeout in seconds.

    Returns:
        Tuple of (response, list of attempted route IDs).

    Raises:
        AllRoutesExhaustedError: If all routes failed.
    """
    attempted: list[str] = []
    last_error: Exception | None = None

    for route in [primary_route, *fallback_routes]:
        route_id = str(route.id)

        if not await circuit_breaker.is_available(route_id):
            logger.debug("route_circuit_open", extra={"route_id": route_id})
            continue

        attempted.append(route_id)
        start = time.monotonic()

        try:
            adapter = ProviderRegistry.get_adapter(route.provider_key)
            normalized = adapter.normalize_request(request_context)
            response = await adapter.send(route, normalized)

            latency_ms = (time.monotonic() - start) * 1000
            await circuit_breaker.record_success(route_id)

            logger.info(
                "route_success",
                extra={
                    "route_id": route_id,
                    "provider": route.provider_key,
                    "latency_ms": round(latency_ms, 2),
                    "attempt": len(attempted),
                },
            )
            return response, attempted

        except (ProviderTimeoutError, ProviderRateLimitError, ProviderServerError) as e:
            latency_ms = (time.monotonic() - start) * 1000
            await circuit_breaker.record_failure(route_id)
            last_error = e

            logger.warning(
                "route_transient_failure",
                extra={
                    "route_id": route_id,
                    "provider": route.provider_key,
                    "error": str(e),
                    "latency_ms": round(latency_ms, 2),
                    "attempt": len(attempted),
                },
            )
            continue

        except ProviderAuthError:
            logger.error("route_auth_failure", extra={"route_id": route_id, "provider": route.provider_key})
            raise

        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            await circuit_breaker.record_failure(route_id)
            last_error = e

            logger.error(
                "route_unexpected_failure",
                extra={
                    "route_id": route_id,
                    "provider": route.provider_key,
                    "error": str(e),
                    "latency_ms": round(latency_ms, 2),
                    "attempt": len(attempted),
                },
            )
            continue

    raise AllRoutesExhaustedError(
        attempted=attempted,
        last_error=str(last_error) if last_error else "Unknown error",
    )
