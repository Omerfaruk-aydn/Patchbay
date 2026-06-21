from __future__ import annotations

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


@ProviderRegistry.register
class OpenAIAdapter(ProviderAdapter):
    provider_key = "openai"

    def normalize_request(self, req: dict) -> NormalizedRequest:
        return NormalizedRequest(
            messages=req.get("messages", []),
            system=next(
                (m["content"] for m in req.get("messages", []) if m["role"] == "system"),
                None,
            ),
            max_tokens=req.get("max_tokens", 4096),
            temperature=req.get("temperature"),
            tools=req.get("tools"),
            stream=req.get("stream", False),
        )

    def normalize_response(self, response: dict) -> NormalizedResponse:
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        tool_calls = []
        for tc in message.get("tool_calls", []):
            func = tc.get("function", {})
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=func.get("name", ""),
                    arguments=func.get("arguments", {}),
                )
            )

        usage = response.get("usage", {})
        return NormalizedResponse(
            text=message.get("content", ""),
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason"),
        )

    async def send(
        self, route: Any, request: NormalizedRequest
    ) -> NormalizedResponse:
        client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {route.auth_credential_ref}"},
            timeout=60.0,
        )
        messages = list(request.messages)
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})

        payload: dict[str, Any] = {
            "model": route.provider_model_id,
            "messages": messages,
            "max_tokens": request.max_tokens,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return self.normalize_response(response.json())

    async def stream(
        self, route: Any, request: NormalizedRequest
    ) -> AsyncIterator[NormalizedStreamChunk]:
        client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {route.auth_credential_ref}"},
            timeout=60.0,
        )
        messages = list(request.messages)
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})

        payload: dict[str, Any] = {
            "model": route.provider_model_id,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools

        async with client.stream("POST", "/chat/completions", json=payload) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                import json

                chunk = json.loads(data)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield NormalizedStreamChunk(text_delta=content)
                finish = chunk.get("choices", [{}])[0].get("finish_reason")
                if finish:
                    yield NormalizedStreamChunk(finish_reason=finish)

    async def health_check(self, route: Any) -> bool:
        try:
            client = httpx.AsyncClient(
                base_url="https://api.openai.com/v1",
                headers={"Authorization": f"Bearer {route.auth_credential_ref}"},
                timeout=10.0,
            )
            response = await client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4
