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

    Every provider adapter must implement all methods. The routing engine
    and API layer only interact with providers through this interface.
    """

    provider_key: str

    @abstractmethod
    async def send(
        self, route: Any, request: NormalizedRequest
    ) -> NormalizedResponse:
        """Send a synchronous (non-streaming) completion request."""
        ...

    @abstractmethod
    async def stream(
        self, route: Any, request: NormalizedRequest
    ) -> AsyncIterator[NormalizedStreamChunk]:
        """Send a streaming completion request via SSE."""
        ...

    @abstractmethod
    async def health_check(self, route: Any) -> bool:
        """Lightweight health check called by the circuit breaker."""
        ...

    @abstractmethod
    def normalize_request(self, openai_format_request: dict) -> NormalizedRequest:
        """Convert OpenAI-format request to provider-specific format."""
        ...

    @abstractmethod
    def normalize_response(self, provider_response: Any) -> NormalizedResponse:
        """Convert provider-specific response to unified format."""
        ...

    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens using provider-specific tokenizer for cost estimation."""
        ...
