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
class VertexAdapter(ProviderAdapter):
    """Google Vertex AI adapter — uses service account OAuth."""

    provider_key = "vertex_ai"

    def normalize_request(self, req: dict) -> NormalizedRequest:
        return NormalizedRequest(
            messages=req.get("messages", []),
            system=next(
                (m["content"] for m in req.get("messages", []) if m["role"] == "system"),
                None,
            ),
            max_tokens=req.get("max_tokens", 4096),
            temperature=req.get("temperature"),
        )

    def normalize_response(self, response: dict) -> NormalizedResponse:
        candidates = response.get("candidates", [{}])
        if not candidates:
            return NormalizedResponse()
        content = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in content if "text" in p)
        usage = response.get("usageMetadata", {})
        return NormalizedResponse(
            text=text,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            finish_reason=candidates[0].get("finishReason"),
        )

    async def send(self, route: Any, request: NormalizedRequest) -> NormalizedResponse:
        client = httpx.AsyncClient(timeout=60.0)
        contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in request.messages]
        payload: dict[str, Any] = {"contents": contents, "generationConfig": {"maxOutputTokens": request.max_tokens}}
        response = await client.post(
            f"https://{route.region}-aiplatform.googleapis.com/v1/projects/PROJECT/locations/{route.region}/publishers/google/models/{route.provider_model_id}:generateContent",
            json=payload,
        )
        response.raise_for_status()
        return self.normalize_response(response.json())

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        yield NormalizedStreamChunk(text_delta="")

    async def health_check(self, route: Any) -> bool:
        return True

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4
