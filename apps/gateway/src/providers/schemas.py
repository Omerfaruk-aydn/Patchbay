from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NormalizedRequest(BaseModel):
    messages: list[dict[str, Any]]
    system: str | None = None
    max_tokens: int = 4096
    temperature: float | None = None
    tools: list[dict[str, Any]] | None = None
    stream: bool = False
    provider_specific: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class NormalizedResponse(BaseModel):
    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str | None = None
    provider_specific: dict[str, Any] = Field(default_factory=dict)


class NormalizedStreamChunk(BaseModel):
    text_delta: str = ""
    tool_call_delta: dict[str, Any] | None = None
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
