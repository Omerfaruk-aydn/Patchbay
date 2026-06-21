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
)
from patchbay_gateway.providers.registry import ProviderRegistry


@ProviderRegistry.register
class AzureOpenAIAdapter(ProviderAdapter):
    provider_key = "azure_openai"

    def normalize_request(self, req: dict) -> NormalizedRequest:
        return NormalizedRequest(
            messages=req.get("messages", []),
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
        endpoint = route.auth_credential_ref  # stored as endpoint URL
        client = httpx.AsyncClient(
            base_url=endpoint,
            headers={"api-key": route.auth_credential_ref},
            timeout=60.0,
        )
        payload: dict[str, Any] = {"model": route.provider_model_id, "messages": request.messages, "max_tokens": request.max_tokens}
        response = await client.post("/openai/deployments/{route.provider_model_id}/chat/completions?api-version=2024-02-01", json=payload)
        response.raise_for_status()
        return self.normalize_response(response.json())

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        yield NormalizedStreamChunk(text_delta="")

    async def health_check(self, route: Any) -> bool:
        return True

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4
