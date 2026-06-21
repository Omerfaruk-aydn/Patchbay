from __future__ import annotations

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
class LocalAdapter(ProviderAdapter):
    """Adapter for local LLM servers (Ollama, vLLM, LM Studio).

    These typically expose OpenAI-compatible APIs on localhost.
    """

    provider_key = "local"

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
        base_url = route.auth_credential_ref  # stored as base URL (e.g., http://localhost:11434)
        client = httpx.AsyncClient(base_url=base_url, timeout=120.0)
        payload: dict[str, Any] = {"model": route.provider_model_id, "messages": request.messages, "max_tokens": request.max_tokens}
        response = await client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        return self.normalize_response(response.json())

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        yield NormalizedStreamChunk(text_delta="")

    async def health_check(self, route: Any) -> bool:
        try:
            client = httpx.AsyncClient(base_url=route.auth_credential_ref, timeout=5.0)
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4
