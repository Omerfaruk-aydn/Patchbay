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
class GoogleAdapter(ProviderAdapter):
    provider_key = "google"

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
                "function_declarations": [
                    {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "parameters": t["function"].get("parameters", {}),
                    }
                ]
            }
            for t in openai_tools
        ]

    def normalize_response(self, response: dict) -> NormalizedResponse:
        candidates = response.get("candidates", [{}])
        if not candidates:
            return NormalizedResponse()
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
                        id=fc.get("name", ""),
                        name=fc.get("name", ""),
                        arguments=fc.get("args", {}),
                    )
                )

        usage = response.get("usageMetadata", {})
        return NormalizedResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            finish_reason=candidate.get("finishReason"),
        )

    async def send(
        self, route: Any, request: NormalizedRequest
    ) -> NormalizedResponse:
        client = httpx.AsyncClient(
            base_url=f"https://generativelanguage.googleapis.com/v1beta",
            timeout=60.0,
        )
        contents = self._build_contents(request.messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": request.max_tokens},
        }
        if request.system:
            payload["systemInstruction"] = {"parts": [{"text": request.system}]}
        if request.temperature is not None:
            payload["generationConfig"]["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools

        response = await client.post(
            f"/models/{route.provider_model_id}:generateContent?key={route.auth_credential_ref}",
            json=payload,
        )
        response.raise_for_status()
        return self.normalize_response(response.json())

    async def stream(
        self, route: Any, request: NormalizedRequest
    ) -> AsyncIterator[NormalizedStreamChunk]:
        client = httpx.AsyncClient(
            base_url="https://generativelanguage.googleapis.com/v1beta",
            timeout=60.0,
        )
        contents = self._build_contents(request.messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": request.max_tokens},
        }
        if request.system:
            payload["systemInstruction"] = {"parts": [{"text": request.system}]}
        if request.temperature is not None:
            payload["generationConfig"]["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools

        async with client.stream(
            "POST",
            f"/models/{route.provider_model_id}:streamGenerateContent?key={route.auth_credential_ref}&alt=sse",
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                candidates = data.get("candidates", [{}])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "text" in part:
                            yield NormalizedStreamChunk(text_delta=part["text"])

    def _build_contents(self, messages: list[dict]) -> list[dict]:
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        return contents

    async def health_check(self, route: Any) -> bool:
        try:
            client = httpx.AsyncClient(timeout=10.0)
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={route.auth_credential_ref}"
            )
            return response.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4
