"""Google Gemini provider adapter — full implementation with streaming and tool use.

Supports:
  - Gemini API (AI Studio) with API key auth
  - Streaming via SSE
  - Function calling with automatic schema translation
  - System instructions
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
class GoogleAdapter(ProviderAdapter):
    """Google Gemini API adapter.

    Handles Gemini model family with function calling, streaming,
    and system instructions. Translates between OpenAI's tool format
    and Gemini's functionDeclarations format.
    """

    provider_key = "google"
    _base_url = "https://generativelanguage.googleapis.com/v1beta"

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
            tools=self._translate_tools_to_gemini(req.get("tools")),
            stream=req.get("stream", False),
        )

    def _translate_tools_to_gemini(self, openai_tools: list[dict] | None) -> list[dict] | None:
        if not openai_tools:
            return None
        function_declarations = []
        for tool in openai_tools:
            func = tool.get("function", tool)
            function_declarations.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            })
        return [{"function_declarations": function_declarations}] if function_declarations else None

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
                    ToolCall(
                        id=fc.get("name", f"fc_{int(time.time() * 1000)}"),
                        name=fc.get("name", ""),
                        arguments=fc.get("args", {}),
                    )
                )

        usage = response.get("usageMetadata", {})
        finish_reason = candidate.get("finishReason", "STOP")
        finish_map = {"STOP": "stop", "MAX_TOKENS": "length", "SAFETY": "content_filter"}
        mapped_finish = finish_map.get(finish_reason, finish_reason.lower())

        return NormalizedResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            finish_reason=mapped_finish,
        )

    async def send(
        self, route: Any, request: NormalizedRequest
    ) -> NormalizedResponse:
        contents = self._build_contents(request.messages)
        payload = self._build_payload(request, contents)

        response_data = await self._request_with_retry(
            "POST",
            f"{self._base_url}/models/{route.provider_model_id}:generateContent?key={route.auth_credential_ref}",
            json_data=payload,
        )
        return self.normalize_response(response_data)

    async def stream(
        self, route: Any, request: NormalizedRequest
    ) -> AsyncIterator[NormalizedStreamChunk]:
        contents = self._build_contents(request.messages)
        payload = self._build_payload(request, contents)

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/models/{route.provider_model_id}:streamGenerateContent?key={route.auth_credential_ref}&alt=sse",
                json_data=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise Exception(f"Stream error {response.status_code}: {body.decode()[:200]}")

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            if "text" in part:
                                yield NormalizedStreamChunk(text_delta=part["text"])
                            if "function_call" in part:
                                fc = part["function_call"]
                                yield NormalizedStreamChunk(
                                    tool_call_delta={
                                        "name": fc.get("name", ""),
                                        "arguments": fc.get("args", {}),
                                    }
                                )

                    usage = data.get("usageMetadata")
                    if usage:
                        yield NormalizedStreamChunk(
                            usage={
                                "prompt_tokens": usage.get("promptTokenCount", 0),
                                "completion_tokens": usage.get("candidatesTokenCount", 0),
                            }
                        )

    async def health_check(self, route: Any) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.get(
                    f"{self._base_url}/models?key={route.auth_credential_ref}"
                )
                return resp.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return max(len(text) // 4, 1)

    def _build_contents(self, messages: list[dict]) -> list[dict]:
        contents = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
        return contents

    def _build_payload(self, request: NormalizedRequest, contents: list[dict]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
            },
        }
        if request.system:
            payload["systemInstruction"] = {"parts": [{"text": request.system}]}
        if request.temperature is not None:
            payload["generationConfig"]["temperature"] = request.temperature
        if request.top_p is not None:
            payload["generationConfig"]["topP"] = request.top_p
        if request.tools:
            payload["tools"] = request.tools
        return payload

    async def _request_with_retry(
        self, method: str, url: str, json_data: dict | None = None
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                    response = await client.request(method, url, json=json_data)
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

