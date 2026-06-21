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
class DeepSeekAdapter(ProviderAdapter):
    provider_key = "deepseek"

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
        usage = response.get("usage", {})
        return NormalizedResponse(
            text=message.get("content", ""),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason"),
        )

    async def send(self, route: Any, request: NormalizedRequest) -> NormalizedResponse:
        client = httpx.AsyncClient(
            base_url="https://api.deepseek.com/v1",
            headers={"Authorization": f"Bearer {route.auth_credential_ref}"},
            timeout=60.0,
        )
        messages = list(request.messages)
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        payload = {"model": route.provider_model_id, "messages": messages, "max_tokens": request.max_tokens}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return self.normalize_response(response.json())

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        yield NormalizedStreamChunk(text_delta="")

    async def health_check(self, route: Any) -> bool:
        try:
            client = httpx.AsyncClient(base_url="https://api.deepseek.com/v1", headers={"Authorization": f"Bearer {route.auth_credential_ref}"}, timeout=10.0)
            response = await client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4
