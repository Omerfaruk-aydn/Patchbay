"""DeepSeek provider adapter — cost-effective coding and reasoning models.

Supports:
  - DeepSeek Chat API (OpenAI-compatible endpoint)
  - DeepSeek Coder and Reasoner models
  - Streaming via SSE
  - Tool/function calling
  - Agentic coding with extended context
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


@ProviderRegistry.register
class DeepSeekAdapter(ProviderAdapter):
    """DeepSeek API adapter.

    DeepSeek uses an OpenAI-compatible API, but with its own model
    identifiers and pricing. The adapter handles the translation and
    provides accurate token counting for cost estimation.
    """

    provider_key = "deepseek"
    _base_url = "https://api.deepseek.com"

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
            tools=self._normalize_tools(req.get("tools")),
            stream=req.get("stream", False),
        )

    def _normalize_tools(self, tools: list[dict] | None) -> list[dict] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.get("function", t).get("name", ""),
                    "description": t.get("function", t).get("description", ""),
                    "parameters": t.get("function", t).get("parameters", {}),
                },
            }
            for t in tools
        ]

    def normalize_response(self, response: dict[str, Any]) -> NormalizedResponse:
        choices = response.get("choices", [])
        if not choices:
            return NormalizedResponse(finish_reason="error")

        choice = choices[0]
        message = choice.get("message", {})
        tool_calls = []
        for tc in message.get("tool_calls", []):
            func = tc.get("function", {})
            args = func.get("arguments", "{}")
            try:
                parsed = json.loads(args) if isinstance(args, str) else args
            except (json.JSONDecodeError, TypeError):
                parsed = {}
            tool_calls.append(
                ToolCall(id=tc.get("id", ""), name=func.get("name", ""), arguments=parsed)
            )

        usage = response.get("usage", {})
        return NormalizedResponse(
            text=message.get("content") or "",
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason"),
            provider_specific={"reasoning_content": message.get("reasoning_content")},
        )

    async def send(self, route: Any, request: NormalizedRequest) -> NormalizedResponse:
        payload = self._build_payload(request)
        data = await self._request_with_retry(
            "POST",
            f"{self._base_url}/chat/completions",
            json_data=payload,
            headers={"Authorization": f"Bearer {route.auth_credential_ref}"},
        )
        return self.normalize_response(data)

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        payload = self._build_payload(request)
        payload["stream"] = True

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json_data=payload,
                headers={"Authorization": f"Bearer {route.auth_credential_ref}"},
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise Exception(f"Stream error {response.status_code}: {body.decode()[:200]}")

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        yield NormalizedStreamChunk(finish_reason="stop")
                        return
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield NormalizedStreamChunk(text_delta=content)
                        reasoning = delta.get("reasoning_content")
                        if reasoning:
                            yield NormalizedStreamChunk(text_delta=reasoning)
                        finish = choices[0].get("finish_reason")
                        if finish:
                            yield NormalizedStreamChunk(finish_reason=finish)

    async def health_check(self, route: Any) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {route.auth_credential_ref}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return max(len(text) // 4, 1)

    def _build_payload(self, request: NormalizedRequest) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.extend(request.messages)
        payload: dict[str, Any] = {"messages": messages, "max_tokens": request.max_tokens}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.tools:
            payload["tools"] = request.tools
        return payload

    async def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                    response = await client.request(method, url, **kwargs)
                    if response.status_code in _RETRYABLE_STATUS_CODES:
                        retry_after = float(response.headers.get("retry-after", _RETRY_DELAY_BASE * (2 ** attempt)))
                        await asyncio.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    return response.json()
            except httpx.TimeoutException as e:
                last_error = e
                await asyncio.sleep(_RETRY_DELAY_BASE * (2 ** attempt))
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in _RETRYABLE_STATUS_CODES:
                    raise
                last_error = e
                await asyncio.sleep(_RETRY_DELAY_BASE * (2 ** attempt))
        raise last_error or Exception("Max retries exceeded")

