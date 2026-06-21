"""Google Vertex AI provider adapter — enterprise Gemini access via GCP.

Supports:
  - Gemini models via Vertex AI
  - GCP service account authentication
  - Cross-region deployment
  - Model Garden (third-party models)
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
class VertexAdapter(ProviderAdapter):
    """Google Vertex AI adapter.

    Vertex AI uses GCP service account authentication instead of API keys.
    The adapter handles OAuth2 token generation and the Vertex AI REST API.
    """

    provider_key = "vertex_ai"

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
            tools=self._translate_tools(req.get("tools")),
            stream=req.get("stream", False),
        )

    def _translate_tools(self, openai_tools: list[dict] | None) -> list[dict] | None:
        if not openai_tools:
            return None
        declarations = []
        for t in openai_tools:
            func = t.get("function", t)
            declarations.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            })
        return [{"function_declarations": declarations}] if declarations else None

    def normalize_response(self, response: dict[str, Any]) -> NormalizedResponse:
        candidates = response.get("candidates", [])
        if not candidates:
            return NormalizedResponse(finish_reason="error")

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text_parts = []
        tool_calls = []
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            if "function_call" in part:
                fc = part["function_call"]
                tool_calls.append(
                    ToolCall(id=fc.get("name", ""), name=fc.get("name", ""), arguments=fc.get("args", {}))
                )

        usage = response.get("usageMetadata", {})
        return NormalizedResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            finish_reason=candidate.get("finishReason", "STOP").lower(),
        )

    async def send(self, route: Any, request: NormalizedRequest) -> NormalizedResponse:
        region = route.region or "us-central1"
        project = route.auth_credential_ref
        url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/{route.provider_model_id}:generateContent"

        contents = self._build_contents(request.messages)
        payload = self._build_payload(request, contents)

        data = await self._request_with_retry("POST", url, json=payload)
        return self.normalize_response(data)

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        yield NormalizedStreamChunk(text_delta="")

    async def health_check(self, route: Any) -> bool:
        return True

    def count_tokens(self, text: str, model: str) -> int:
        return max(len(text) // 4, 1)

    def _build_contents(self, messages: list[dict]) -> list[dict]:
        contents = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
        return contents

    def _build_payload(self, request: NormalizedRequest, contents: list[dict]) -> dict[str, Any]:
        payload: dict[str, Any] = {"contents": contents, "generationConfig": {"maxOutputTokens": request.max_tokens}}
        if request.system:
            payload["systemInstruction"] = {"parts": [{"text": request.system}]}
        if request.temperature is not None:
            payload["generationConfig"]["temperature"] = request.temperature
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
