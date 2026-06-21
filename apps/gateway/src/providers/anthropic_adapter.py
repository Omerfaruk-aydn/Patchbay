from __future__ import annotations

import json
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


@ProviderRegistry.register
class AnthropicAdapter(ProviderAdapter):
    provider_key = "anthropic"

    def normalize_request(self, req: dict) -> NormalizedRequest:
        system_msg = next(
            (m["content"] for m in req.get("messages", []) if m["role"] == "system"),
            None,
        )
        non_system = [m for m in req.get("messages", []) if m["role"] != "system"]
        return NormalizedRequest(
            messages=non_system,
            system=system_msg,
            max_tokens=req.get("max_tokens", 4096),
            temperature=req.get("temperature"),
            tools=self._translate_tools(req.get("tools", [])),
            stream=req.get("stream", False),
        )

    def _translate_tools(self, openai_tools: list[dict]) -> list[dict]:
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "input_schema": t["function"].get("parameters", {}),
            }
            for t in openai_tools
        ]

    def normalize_response(self, response: dict) -> NormalizedResponse:
        content_blocks = response.get("content", [])
        text_parts = []
        tool_calls = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                    )
                )

        usage = response.get("usage", {})
        return NormalizedResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            finish_reason=response.get("stop_reason"),
        )

    async def send(
        self, route: Any, request: NormalizedRequest
    ) -> NormalizedResponse:
        client = httpx.AsyncClient(
            base_url="https://api.anthropic.com/v1",
            headers={
                "x-api-key": route.auth_credential_ref,
                "anthropic-version": "2023-06-01",
            },
            timeout=60.0,
        )
        payload: dict[str, Any] = {
            "model": route.provider_model_id,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
        }
        if request.system:
            payload["system"] = request.system
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools

        response = await client.post("/messages", json=payload)
        response.raise_for_status()
        return self.normalize_response(response.json())

    async def stream(
        self, route: Any, request: NormalizedRequest
    ) -> AsyncIterator[NormalizedStreamChunk]:
        client = httpx.AsyncClient(
            base_url="https://api.anthropic.com/v1",
            headers={
                "x-api-key": route.auth_credential_ref,
                "anthropic-version": "2023-06-01",
            },
            timeout=60.0,
        )
        payload: dict[str, Any] = {
            "model": route.provider_model_id,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if request.system:
            payload["system"] = request.system
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools

        async with client.stream("POST", "/messages", json=payload) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                event_type = data.get("type", "")
                if event_type == "content_block_delta":
                    delta = data.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        yield NormalizedStreamChunk(text_delta=text)
                elif event_type == "message_stop":
                    yield NormalizedStreamChunk(finish_reason="end_turn")

    async def health_check(self, route: Any) -> bool:
        try:
            client = httpx.AsyncClient(
                base_url="https://api.anthropic.com/v1",
                headers={
                    "x-api-key": route.auth_credential_ref,
                    "anthropic-version": "2023-06-01",
                },
                timeout=10.0,
            )
            response = await client.post(
                "/messages",
                json={
                    "model": route.provider_model_id,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            return response.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4
