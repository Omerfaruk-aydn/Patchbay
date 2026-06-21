"""Centralized exception hierarchy for the Patchbay Gateway.

Every exception in the system inherits from PatchbayError. Generic
Exception is never raised directly — this ensures consistent error
handling across all layers (API, routing, providers, guardrails).

Exception flow:
  ProviderError → ProviderTimeoutError / ProviderRateLimitError / ProviderServerError
  RoutingError  → NoHealthyRouteError / AllRoutesExhaustedError
  GuardrailError → GuardrailBlockedError
  MCPError → MCPConnectionError / MCPToolExecutionError
"""

from __future__ import annotations

from typing import Any


class PatchbayError(Exception):
    """Base exception for all Patchbay errors.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code for API responses.
        status_code: HTTP status code (default 500).
        metadata: Additional context for structured logging.
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.metadata = metadata or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "metadata": self.metadata,
            }
        }


# ── Provider Errors ──────────────────────────────────────────────

class ProviderError(PatchbayError):
    """Base for all provider-related errors."""

    code = "PROVIDER_ERROR"
    status_code = 502


class ProviderTimeoutError(ProviderError):
    """Provider did not respond within the configured timeout."""

    code = "PROVIDER_TIMEOUT"

    def __init__(self, provider: str, timeout: float, metadata: dict[str, Any] | None = None) -> None:
        self.provider = provider
        self.timeout = timeout
        super().__init__(
            f"Provider '{provider}' timed out after {timeout}s",
            metadata={**(metadata or {}), "provider": provider, "timeout": timeout},
        )


class ProviderRateLimitError(ProviderError):
    """Provider returned HTTP 429 (rate limit exceeded)."""

    code = "PROVIDER_RATE_LIMITED"

    def __init__(
        self,
        provider: str,
        retry_after: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Provider '{provider}' rate limited"
            + (f" — retry after {retry_after}s" if retry_after else ""),
            metadata={**(metadata or {}), "provider": provider, "retry_after": retry_after},
        )


class ProviderServerError(ProviderError):
    """Provider returned HTTP 5xx (server error)."""

    code = "PROVIDER_SERVER_ERROR"

    def __init__(self, provider: str, status_code: int, detail: str = "", metadata: dict[str, Any] | None = None) -> None:
        self.provider = provider
        self.upstream_status = status_code
        super().__init__(
            f"Provider '{provider}' returned {status_code}: {detail}",
            metadata={**(metadata or {}), "provider": provider, "upstream_status": status_code},
        )


class ProviderAuthError(ProviderError):
    """Provider authentication failed (HTTP 401/403)."""

    code = "PROVIDER_AUTH_ERROR"
    status_code = 401

    def __init__(self, provider: str, metadata: dict[str, Any] | None = None) -> None:
        self.provider = provider
        super().__init__(
            f"Authentication failed for provider '{provider}'",
            metadata={**(metadata or {}), "provider": provider},
        )


class UnknownProviderError(ProviderError):
    """Requested provider key not found in the registry."""

    code = "UNKNOWN_PROVIDER"
    status_code = 404

    def __init__(self, provider_key: str, metadata: dict[str, Any] | None = None) -> None:
        self.provider_key = provider_key
        super().__init__(
            f"Unknown provider: '{provider_key}'",
            metadata={**(metadata or {}), "provider_key": provider_key},
        )


# ── Routing Errors ───────────────────────────────────────────────

class RoutingError(PatchbayError):
    """Base for routing-related errors."""

    code = "ROUTING_ERROR"
    status_code = 503


class NoHealthyRouteError(RoutingError):
    """No healthy route available for the requested model."""

    code = "NO_HEALTHY_ROUTE"

    def __init__(self, model: str, metadata: dict[str, Any] | None = None) -> None:
        self.model = model
        super().__init__(
            f"No healthy route available for model '{model}'",
            metadata={**(metadata or {}), "model": model},
        )


class AllRoutesExhaustedError(RoutingError):
    """All fallback routes have been tried and failed."""

    code = "ALL_ROUTES_EXHAUSTED"

    def __init__(self, attempted: list[str], last_error: str = "", metadata: dict[str, Any] | None = None) -> None:
        self.attempted = attempted
        self.last_error = last_error
        super().__init__(
            f"All {len(attempted)} routes exhausted. Last error: {last_error}",
            metadata={**(metadata or {}), "attempted_routes": attempted, "last_error": last_error},
        )


# ── Guardrail Errors ─────────────────────────────────────────────

class GuardrailError(PatchbayError):
    """Base for guardrail-related errors."""

    code = "GUARDRAIL_ERROR"
    status_code = 403


class GuardrailBlockedError(GuardrailError):
    """Request blocked by a guardrail check."""

    code = "GUARDRAIL_BLOCKED"

    def __init__(self, rule: str, detail: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
        self.rule = rule
        self.detail = detail
        super().__init__(
            f"Request blocked by guardrail rule: {rule}",
            metadata={**(metadata or {}), "rule": rule, "detail": detail},
        )


# ── Billing Errors ───────────────────────────────────────────────

class BudgetExceededError(PatchbayError):
    """Virtual key budget has been exceeded."""

    code = "BUDGET_EXCEEDED"
    status_code = 402

    def __init__(self, key_id: str, current_spend: float, budget: float, metadata: dict[str, Any] | None = None) -> None:
        self.key_id = key_id
        self.current_spend = current_spend
        self.budget = budget
        super().__init__(
            f"Budget exceeded: {current_spend}/{budget} cents used for key '{key_id}'",
            metadata={**(metadata or {}), "key_id": key_id, "current_spend": current_spend, "budget": budget},
        )


class RateLimitExceededError(PatchbayError):
    """Rate limit exceeded for a virtual key."""

    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429

    def __init__(self, key_id: str, limit: int, metadata: dict[str, Any] | None = None) -> None:
        self.key_id = key_id
        self.limit = limit
        super().__init__(
            f"Rate limit exceeded for key '{key_id}': {limit} rpm",
            metadata={**(metadata or {}), "key_id": key_id, "limit": limit},
        )


# ── Auth Errors ──────────────────────────────────────────────────

class AuthenticationError(PatchbayError):
    """Authentication failed."""

    code = "AUTHENTICATION_ERROR"
    status_code = 401


class AuthorizationError(PatchbayError):
    """Authorization failed — insufficient scope."""

    code = "AUTHORIZATION_ERROR"
    status_code = 403

    def __init__(self, required_scope: str, metadata: dict[str, Any] | None = None) -> None:
        self.required_scope = required_scope
        super().__init__(
            f"Insufficient scope: '{required_scope}' required",
            metadata={**(metadata or {}), "required_scope": required_scope},
        )


# ── MCP Errors ───────────────────────────────────────────────────

class MCPError(PatchbayError):
    """Base for MCP-related errors."""

    code = "MCP_ERROR"
    status_code = 502


class MCPConnectionError(MCPError):
    """Failed to connect to MCP server."""

    code = "MCP_CONNECTION_ERROR"

    def __init__(self, server: str, detail: str = "", metadata: dict[str, Any] | None = None) -> None:
        self.server = server
        super().__init__(
            f"Failed to connect to MCP server '{server}': {detail}" if detail
            else f"Failed to connect to MCP server '{server}'",
            metadata={**(metadata or {}), "server": server},
        )


class MCPToolExecutionError(MCPError):
    """MCP tool execution failed."""

    code = "MCP_TOOL_EXECUTION_ERROR"

    def __init__(self, tool: str, server: str, detail: str = "", metadata: dict[str, Any] | None = None) -> None:
        self.tool = tool
        self.server = server
        super().__init__(
            f"MCP tool '{tool}' failed on server '{server}': {detail}" if detail
            else f"MCP tool '{tool}' failed on server '{server}'",
            metadata={**(metadata or {}), "tool": tool, "server": server},
        )


# ── Validation Errors ────────────────────────────────────────────

class ValidationError(PatchbayError):
    """Input validation failed."""

    code = "VALIDATION_ERROR"
    status_code = 422

    def __init__(self, field: str, detail: str, metadata: dict[str, Any] | None = None) -> None:
        self.field = field
        super().__init__(
            f"Validation error on field '{field}': {detail}",
            metadata={**(metadata or {}), "field": field},
        )
