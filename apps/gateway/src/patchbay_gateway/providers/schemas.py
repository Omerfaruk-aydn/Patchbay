"""Normalized request/response schemas for the provider adapter layer.

These schemas define the internal data format that flows between
the routing engine and provider adapters. They are designed as a
superset of OpenAI's Chat Completions format (the de facto standard),
with extensions for provider-specific features.

Design principle: "OpenAI-compatible, but not locked in."
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NormalizedRequest(BaseModel):
    """Unified request format across all providers.

    Based on OpenAI Chat Completions with extensions:
      - system: Top-level system prompt (extracted from messages)
      - provider_specific: Provider-only features (extended_thinking, etc.)
    """

    messages: list[dict[str, Any]] = Field(
        description="Chat messages (system messages excluded, stored in `system` field)"
    )
    system: str | None = Field(
        default=None,
        description="System prompt (extracted from messages by adapter)",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="Maximum tokens to generate",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, 2.0 = most random)",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling threshold",
    )
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="Tool definitions (OpenAI format, translated by adapter)",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response via SSE",
    )
    provider_specific: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-only features (extended_thinking, grounding, etc.)",
    )

    model_config = {"extra": "forbid"}


class ToolCall(BaseModel):
    """Normalized tool call from any provider.

    Every provider's tool call format is normalized to this structure
    before being returned to the routing engine or API layer.
    """

    id: str = Field(description="Unique tool call identifier")
    name: str = Field(description="Tool/function name")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Parsed tool arguments (JSON object)",
    )


class NormalizedResponse(BaseModel):
    """Unified response format across all providers.

    Contains the generated text, any tool calls, token usage,
    and provider-specific metadata that shouldn't be lost.
    """

    text: str = Field(default="", description="Generated text content")
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="Tool calls requested by the model",
    )
    input_tokens: int = Field(
        default=0,
        ge=0,
        description="Input/prompt tokens consumed",
    )
    output_tokens: int = Field(
        default=0,
        ge=0,
        description="Output/completion tokens generated",
    )
    finish_reason: str | None = Field(
        default=None,
        description="Why generation stopped: 'stop', 'length', 'tool_calls', 'content_filter'",
    )
    provider_specific: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-only data (extended_thinking, logprobs, citations, etc.)",
    )


class NormalizedStreamChunk(BaseModel):
    """A single chunk in a streaming response.

    Used for SSE streaming where each chunk contains either:
      - text_delta: Incremental text content
      - tool_call_delta: Incremental tool call data
      - finish_reason: Generation stopped
      - usage: Token usage (typically in the last chunk)
    """

    text_delta: str = Field(default="", description="Incremental text content")
    tool_call_delta: dict[str, Any] | None = Field(
        default=None,
        description="Incremental tool call data (id, name, partial arguments)",
    )
    finish_reason: str | None = Field(
        default=None,
        description="Why generation stopped",
    )
    usage: dict[str, int] | None = Field(
        default=None,
        description="Token usage (typically in the final chunk)",
    )
