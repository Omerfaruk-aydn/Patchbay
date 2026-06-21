"""Anthropic provider adapter — full implementation with streaming, retries, and tool use.

Supports:
  - Messages API (Claude Opus, Sonnet, Haiku)
  - Streaming via SSE (content_block_delta events)
  - Tool use with automatic JSON parsing
  - Extended thinking (provider_specific passthrough)
  - Prompt caching hints
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from patchbay_gateway.providers.base import ProviderAdapter
from patchbay_gateway.providers.schemas import (
    NormalizedRequest,
    NormalizedResponse,
    NormalizedStreamChunk,
    ToolCall,
)
from patchbay_gateway.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY_BASE = 1.0
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503}
_API_VERSION = "2023-06-01"


@ProviderRegistry.register
class AnthropicAdapter(ProviderAdapter):
    """Anthropic Messages API adapter.

    Handles Claude model family with native tool use, extended thinking,
    and streaming. The adapter translates between OpenAI's tool format
    and Anthropic's tool format transparently.
    """

    provider_key = "anthropic"
    _base_url = "https://api.anthropic.com/v1"

    def normalize_request(self, req: dict[str, Any]) -> NormalizedRequest:
        messages = req.get("messages", [])
        system_msg = None
        non_system = []
        for m in messages:
            if m.get("role") == "system" and system_msg is None:
                system_msg = m.get("content", "")
            else:
                non_system.append(m)

        return NormalizedRequest(
            messages=non_system,
            system=system_msg,
            max_tokens=req.get("max_tokens", 4096),
            temperature=req.get("temperature"),
            top_p=req.get("top_p"),
            tools=self._translate_tools_to_anthropic(req.get("tools")),
            stream=req.get("stream", False),
            provider_specific={
                "thinking": req.get("thinking"),
                "metadata": req.get("metadata"),
            },
        )

    def _translate_tools_to_anthropic(self, openai_tools: list[dict] | None) -> list[dict] | None:
        if not openai_tools:
            return None
        translated = []
        for tool in openai_tools:
            func = tool.get("function", tool)
            translated.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", func.get("input_schema", {})),
            })
        return translated if translated else None

    def normalize_response(self, response: dict[str, Any]) -> NormalizedResponse:
        content_blocks = response.get("content", [])
        text_parts = []
        tool_calls = []
        thinking = None

        for block in content_blocks:
            block_type = block.get("type", "")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", f"toolu_{int(time.time() * 1000)}"),
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                    )
                )
            elif block_type == "thinking":
                thinking = block.get("thinking")

        usage = response.get("usage", {})
        provider_specific: dict[str, Any] = {}
        if thinking:
            provider_specific["extended_thinking"] = thinking
        if usage.get("cache_creation_input_tokens"):
            provider_specific["cache_creation_tokens"] = usage["cache_creation_input_tokens"]
        if usage.get("cache_read_input_tokens"):
            provider_specific["cache_read_tokens"] = usage["cache_read_input_tokens"]

        return NormalizedResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            finish_reason=response.get("stop_reason"),
            provider_specific=provider_specific,
        )

    async def send(
        self, route: Any, request: NormalizedRequest
    ) -> NormalizedResponse:
        payload = self._build_payload(request)
        response_data = await self._request_with_retry(
            "POST",
            f"{self._base_url}/messages",
            json=payload,
            headers={
                "x-api-key": route.auth_credential_ref,
                "anthropic-version": _API_VERSION,
                "content-type": "application/json",
            },
        )
        return self.normalize_response(response_data)

    async def stream(
        self, route: Any, request: NormalizedRequest
    ) -> AsyncIterator[NormalizedStreamChunk]:
        payload = self._build_payload(request)
        payload["stream"] = True

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/messages",
                json=payload,
                headers={
                    "x-api-key": route.auth_credential_ref,
                    "anthropic-version": _API_VERSION,
                },
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise Exception(f"Stream error {response.status_code}: {body.decode()[:200]}")

                current_tool_id = ""
                current_tool_name = ""
                current_tool_input = ""

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    try:
                        event = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("type", "")

                    if event_type == "content_block_start":
                        block = event.get("content_block", {})
                        if block.get("type") == "tool_use":
                            current_tool_id = block.get("id", "")
                            current_tool_name = block.get("name", "")
                            current_tool_input = ""

                    elif event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        delta_type = delta.get("type", "")

                        if delta_type == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield NormalizedStreamChunk(text_delta=text)

                        elif delta_type == "input_json_delta":
                            current_tool_input += delta.get("partial_json", "")

                    elif event_type == "content_block_stop":
                        if current_tool_name:
                            try:
                                parsed = json.loads(current_tool_input) if current_tool_input else {}
                            except json.JSONDecodeError:
                                parsed = {}
                            yield NormalizedStreamChunk(
                                tool_call_delta={
                                    "id": current_tool_id,
                                    "name": current_tool_name,
                                    "arguments": parsed,
                                }
                            )
                            current_tool_id = ""
                            current_tool_name = ""
                            current_tool_input = ""

                    elif event_type == "message_delta":
                        delta = event.get("delta", {})
                        stop_reason = delta.get("stop_reason")
                        if stop_reason:
                            yield NormalizedStreamChunk(finish_reason=stop_reason)
                        usage = event.get("usage")
                        if usage:
                            yield NormalizedStreamChunk(
                                usage={"output_tokens": usage.get("output_tokens", 0)}
                            )

                    elif event_type == "message_stop":
                        return

    async def health_check(self, route: Any) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.post(
                    f"{self._base_url}/messages",
                    headers={
                        "x-api-key": route.auth_credential_ref,
                        "anthropic-version": _API_VERSION,
                    },
                    json={
                        "model": route.provider_model_id,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                return resp.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return max(len(text) // 4, 1)

    def _build_payload(self, request: NormalizedRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": request.messages,
            "max_tokens": request.max_tokens,
        }
        if request.system:
            payload["system"] = request.system
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.tools:
            payload["tools"] = request.tools

        thinking = request.provider_specific.get("thinking")
        if thinking:
            payload["thinking"] = thinking

        return payload

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                    response = await client.request(method, url, headers=headers, json=json_data)

                    if response.status_code in _RETRYABLE_STATUS_CODES:
                        retry_after = float(response.headers.get("retry-after", _RETRY_DELAY_BASE * (2 ** attempt)))
                        logger.warning(
                            "anthropic_retry",
                            extra={"status": response.status_code, "attempt": attempt + 1, "retry_after": retry_after},
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning("anthropic_timeout", extra={"attempt": attempt + 1})
                await asyncio.sleep(_RETRY_DELAY_BASE * (2 ** attempt))
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in _RETRYABLE_STATUS_CODES:
                    raise
                last_error = e
                await asyncio.sleep(_RETRY_DELAY_BASE * (2 ** attempt))

        raise last_error or Exception("Max retries exceeded")
