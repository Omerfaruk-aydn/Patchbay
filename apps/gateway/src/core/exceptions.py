from __future__ import annotations


class PatchbayError(Exception):
    """Base exception for all Patchbay errors."""

    def __init__(self, message: str = "An error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class ProviderError(PatchbayError):
    """Base for provider-related errors."""


class ProviderTimeoutError(ProviderError):
    """Provider did not respond in time."""


class ProviderRateLimitError(ProviderError):
    """Provider returned rate limit (429)."""


class ProviderServerError(ProviderError):
    """Provider returned a 5xx error."""


class ProviderAuthError(ProviderError):
    """Provider authentication failed."""


class UnknownProviderError(ProviderError):
    """Requested provider key not found in registry."""


class RoutingError(PatchbayError):
    """Base for routing-related errors."""


class NoHealthyRouteError(RoutingError):
    """No healthy route available for the requested model."""

    def __init__(self, model: str) -> None:
        super().__init__(f"No healthy route available for model: {model}")
        self.model = model


class AllRoutesExhaustedError(RoutingError):
    """All fallback routes have been tried and failed."""

    def __init__(self, attempted: list[str]) -> None:
        self.attempted = attempted
        super().__init__(f"All routes exhausted: {attempted}")


class GuardrailError(PatchbayError):
    """Base for guardrail-related errors."""


class GuardrailBlockedError(GuardrailError):
    """Request blocked by a guardrail check."""

    def __init__(self, rule: str, detail: dict) -> None:
        self.rule = rule
        self.detail = detail
        super().__init__(f"Blocked by guardrail: {rule}")


class BudgetExceededError(PatchbayError):
    """Virtual key budget has been exceeded."""

    def __init__(self, key_id: str, current_spend: float, budget: float) -> None:
        self.key_id = key_id
        self.current_spend = current_spend
        self.budget = budget
        super().__init__(
            f"Budget exceeded for key {key_id}: {current_spend}/{budget} cents"
        )


class RateLimitExceededError(PatchbayError):
    """Rate limit exceeded for a virtual key."""

    def __init__(self, key_id: str, limit: int) -> None:
        self.key_id = key_id
        self.limit = limit
        super().__init__(f"Rate limit exceeded for key {key_id}: {limit} rpm")


class AuthenticationError(PatchbayError):
    """Authentication failed."""


class AuthorizationError(PatchbayError):
    """Authorization failed — insufficient scope."""


class MCPError(PatchbayError):
    """Base for MCP-related errors."""


class MCPConnectionError(MCPError):
    """Failed to connect to MCP server."""


class MCPToolExecutionError(MCPError):
    """MCP tool execution failed."""
