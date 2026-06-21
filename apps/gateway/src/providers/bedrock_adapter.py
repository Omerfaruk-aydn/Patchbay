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
class BedrockAdapter(ProviderAdapter):
    """AWS Bedrock adapter — uses boto3 for SigV4 authentication."""

    provider_key = "aws_bedrock"

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
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [{}])
        text = content[0].get("text", "") if content else ""
        usage = response.get("usage", {})
        return NormalizedResponse(
            text=text,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            finish_reason=output.get("stopReason"),
        )

    async def send(self, route: Any, request: NormalizedRequest) -> NormalizedResponse:
        try:
            import boto3
            client = boto3.client(
                "bedrock-runtime",
                region_name=route.region or "us-east-1",
            )
            messages = [{"role": m["role"], "content": [{"text": m["content"]}]} for m in request.messages]
            kwargs: dict[str, Any] = {
                "modelId": route.provider_model_id,
                "messages": messages,
                "maxTokens": request.max_tokens,
            }
            if request.system:
                kwargs["system"] = [{"text": request.system}]
            if request.temperature is not None:
                kwargs["inferenceConfig"] = {"temperature": request.temperature, "maxTokens": request.max_tokens}
            response = client.invoke_model(**kwargs)
            body = json.loads(response["body"].read())
            return self.normalize_response(body)
        except ImportError:
            raise RuntimeError("boto3 is required for Bedrock adapter")

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        yield NormalizedStreamChunk(text_delta="")

    async def health_check(self, route: Any) -> bool:
        return True

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 4
