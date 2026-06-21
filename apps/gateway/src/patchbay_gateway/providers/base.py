"""Abstract provider adapter interface.

Every LLM provider (OpenAI, Anthropic, Google, etc.) implements this
interface. The routing engine and API layer interact ONLY through
this abstraction — they never know provider-specific details.

Contract:
  - normalize_request: Convert OpenAI-format input to provider format
  - normalize_response: Convert provider output to unified format
  - send: Execute a synchronous completion request
  - stream: Execute a streaming completion request
  - health_check: Lightweight connectivity check for circuit breaker
  - count_tokens: Provider-specific token counting for cost estimation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field


class NormalizedRequest(BaseModel):
    """Unified request format across all providers."""

    messages: list[dict[str, Any]]
    system: str | None = None
    max_tokens: int = 4096
    temperature: float | None = None
    top_p: float | None = None
    tools: list[dict[str, Any]] | None = None
    stream: bool = False
    provider_specific: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """Normalized tool call from any provider."""

    id: str
    name: str
    arguments: dict[str, Any]


class NormalizedResponse(BaseModel):
    """Unified response format across all providers."""

    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str | None = None
    provider_specific: dict[str, Any] = Field(default_factory=dict)


class NormalizedStreamChunk(BaseModel):
    """A single chunk in a streaming response."""

    text_delta: str = ""
    tool_call_delta: dict[str, Any] | None = None
    finish_reason: str | None = None
    usage: dict[str, int] | None = None


class ProviderAdapter(ABC):
    """Abstract adapter interface for all LLM providers.

    Every provider adapter must implement all 6 methods:
      1. normalize_request — Convert OpenAI-format to provider format
      2. normalize_response — Convert provider format to unified format
      3. send — Synchronous completion request
      4. stream — Streaming completion request (SSE)
      5. health_check — Lightweight connectivity check
      6. count_tokens — Provider-specific token counting

    The routing engine and API layer NEVER call provider APIs directly.
    They always go through this interface.
    """

    provider_key: str

    @abstractmethod
    async def send(
        self, route: Any, request: NormalizedRequest
    ) -> NormalizedResponse:
        """Execute a synchronous (non-streaming) completion request.

        Args:
            route: Provider route object with auth credentials and model info.
            request: Normalized request with messages, tools, and parameters.

        Returns:
            Normalized response with text, tool calls, and usage.
        """
        ...

    @abstractmethod
    async def stream(
        self, route: Any, request: NormalizedRequest
    ) -> AsyncIterator[NormalizedStreamChunk]:
        """Execute a streaming completion request via SSE.

        Yields chunks as they arrive from the provider. Each chunk
        contains either text_delta, tool_call_delta, finish_reason, or usage.

        The caller should handle ProviderTimeoutError and retry if needed.
        """
        ...

    @abstractmethod
    async def health_check(self, route: Any) -> bool:
        """Lightweight health check called by the circuit breaker.

        Should make a minimal API call (e.g., GET /models) to verify
        connectivity and authentication. Must not generate tokens.
        """
        ...

    @abstractmethod
    def normalize_request(self, openai_format_request: dict[str, Any]) -> NormalizedRequest:
        """Convert OpenAI-format request to provider-specific format.

        Extracts system prompt, translates tool definitions, and
        maps provider-specific parameters.
        """
        ...

    @abstractmethod
    def normalize_response(self, provider_response: Any) -> NormalizedResponse:
        """Convert provider-specific response to unified format.

        Normalizes tool calls, extracts usage metrics, and maps
        provider-specific finish reasons to standard values.
        """
        ...

    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens using provider-specific tokenizer.

        Used for cost estimation before sending the request.
        The actual token count from the provider response is authoritative.
        """
        ...
