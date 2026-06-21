"""AWS Bedrock provider adapter — enterprise LLM access via AWS IAM.

Supports:
  - Anthropic Claude models via Bedrock
  - Meta Llama models via Bedrock
  - Mistral models via Bedrock
  - IAM SigV4 authentication (via boto3)
  - Cross-region model access
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from patchbay_gateway.providers.base import ProviderAdapter
from patchbay_gateway.providers.schemas import (
    NormalizedRequest,
    NormalizedResponse,
    NormalizedStreamChunk,
    ToolCall,
)
from patchbay_gateway.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


@ProviderRegistry.register
class BedrockAdapter(ProviderAdapter):
    """AWS Bedrock adapter using boto3 for SigV4 authentication.

    Bedrock requires IAM credentials (access_key, secret_key, session_token)
    instead of simple API keys. The adapter uses boto3 which handles
    SigV4 signing automatically.
    """

    provider_key = "aws_bedrock"

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
        )

    def normalize_response(self, response: dict[str, Any]) -> NormalizedResponse:
        output = response.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])

        text_parts = []
        tool_calls = []
        for block in content_blocks:
            if "text" in block:
                text_parts.append(block["text"])
            if "toolUse" in block:
                tu = block["toolUse"]
                tool_calls.append(
                    ToolCall(
                        id=tu.get("toolUseId", ""),
                        name=tu.get("name", ""),
                        arguments=tu.get("input", {}),
                    )
                )

        usage = response.get("usage", {})
        return NormalizedResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
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

            messages = []
            for m in request.messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                messages.append({"role": role, "content": [{"text": content}]})

            kwargs: dict[str, Any] = {
                "modelId": route.provider_model_id,
                "messages": messages,
                "maxTokens": request.max_tokens,
            }
            if request.system:
                kwargs["system"] = [{"text": request.system}]
            if request.temperature is not None:
                kwargs["inferenceConfig"] = {
                    "temperature": request.temperature,
                    "maxTokens": request.max_tokens,
                }

            response = client.invoke_model(
                body=json.dumps(kwargs),
                contentType="application/json",
                accept="application/json",
                modelId=route.provider_model_id,
            )
            body = json.loads(response["body"].read())
            return self.normalize_response(body)

        except ImportError:
            raise RuntimeError("boto3 is required for Bedrock adapter: pip install boto3")
        except Exception as e:
            logger.error("bedrock_error", extra={"error": str(e), "model": route.provider_model_id})
            raise

    async def stream(self, route: Any, request: NormalizedRequest) -> AsyncIterator[NormalizedStreamChunk]:
        yield NormalizedStreamChunk(text_delta="")

    async def health_check(self, route: Any) -> bool:
        try:
            import boto3
            client = boto3.client("bedrock", region_name=route.region or "us-east-1")
            client.list_foundation_models()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str, model: str) -> int:
        return max(len(text) // 4, 1)
