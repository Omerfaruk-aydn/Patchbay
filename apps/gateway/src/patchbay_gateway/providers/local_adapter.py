"""Local provider adapter — Ollama, vLLM, LM Studio, llama.cpp server.

Supports:
  - OpenAI-compatible local servers (Ollama, vLLM)
  - LM Studio local API
  - Custom endpoints
  - Auto-detection of available models
"""

from __future__ import annotations

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


@ProviderRegistry.register
class LocalAdapter(ProviderAdapter):
    """Local LLM server adapter.

    Works with any OpenAI-compatible local server:
      - Ollama (http://localhost:11434)
      - vLLM (http://localhost:8000)
      - LM Studio (http://localhost:1234)
      - llama.cpp server (http://localhost:8080)

    The auth_credential_ref stores the base URL of the local server.
    """

    provider_key = "local"

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
            tool_calls.append(ToolCall(id=tc.get("id", ""), name=func.get("name", ""), arguments=parsed))

        usage = response.get("usage", {})
        return NormalizedResponse(
            text=message.get("content") or "",
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason"),
        )

    async def send(self, route: Any, request: NormalizedRequest) -> NormalizedResponse:
        base_url = route.auth_credential_ref
        payload = self._build_payload(request)

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            response = await client.post(f"{base_url}/v1/chat/completions", json_data=payload)
            response.raise_for_status()
            return self.normalize_response(response.json())

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        base_url = route.auth_credential_ref
        payload = self._build_payload(request)
        payload["stream"] = True

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream("POST", f"{base_url}/v1/chat/completions", json_data=payload) as response:
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
                        finish = choices[0].get("finish_reason")
                        if finish:
                            yield NormalizedStreamChunk(finish_reason=finish)

    async def health_check(self, route: Any) -> bool:
        try:
            base_url = route.auth_credential_ref
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                resp = await client.get(f"{base_url}/api/tags")
                if resp.status_code == 200:
                    return True
                resp = await client.get(f"{base_url}/v1/models")
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
        if request.tools:
            payload["tools"] = request.tools
        return payload

