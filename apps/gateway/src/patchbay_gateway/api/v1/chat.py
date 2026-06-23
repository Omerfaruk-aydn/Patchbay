from __future__ import annotations

import json
import time
import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.core.exceptions import (
    NoHealthyRouteError,
    AllRoutesExhaustedError,
    BudgetExceededError,
    RateLimitExceededError,
    GuardrailBlockedError,
    PatchbayError,
)
from patchbay_gateway.db.models import ProviderRoute, LLMModel
from patchbay_gateway.providers.registry import ProviderRegistry
from patchbay_gateway.providers.schemas import NormalizedRequest
from patchbay_gateway.routing.engine import RoutingEngine
from patchbay_gateway.routing.circuit_breaker import CircuitBreaker
from patchbay_gateway.routing.fallback_chain import execute_with_fallback
from patchbay_gateway.billing.budget_enforcer import BudgetEnforcer
from patchbay_gateway.billing.rate_limiter import RateLimiter
from patchbay_gateway.billing.cost_calculator import calculate_cost
from patchbay_gateway.guardrails.base import GuardrailPipeline
from patchbay_gateway.guardrails.pii_redaction import PIIRedactionCheck
from patchbay_gateway.guardrails.jailbreak_detector import JailbreakDetectionCheck
from patchbay_gateway.guardrails.content_filter import ContentPolicyCheck

router = APIRouter()

guardrail_pipeline = GuardrailPipeline(
    stages=[PIIRedactionCheck(), JailbreakDetectionCheck(), ContentPolicyCheck()]
)


class ChatMessage(BaseModel):
    role: str
    content: str | list[Any]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False


class EmbeddingRequest(BaseModel):
    model: str = "text-embedding-ada-002"
    input: str | list[str]


def _get_circuit_breaker(request: Request) -> CircuitBreaker:
    return CircuitBreaker(request.app.state.redis)


async def _run_guardrails(text: str) -> None:
    results = await guardrail_pipeline.run_input_checks(text)
    for r in results:
        if r.action == "block":
            raise GuardrailBlockedError(r.rule, r.detail)


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict | StreamingResponse:
    """OpenAI-compatible chat completions endpoint with full pipeline."""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    start = time.monotonic()

    try:
        last_user_msg = next(
            (m.content for m in reversed(body.messages) if m.role == "user" and isinstance(m.content, str)),
            "",
        )
        if last_user_msg:
            await _run_guardrails(last_user_msg)

        model_result = await db.execute(
            select(LLMModel).where(LLMModel.canonical_name == body.model, LLMModel.is_active.is_(True))
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {body.model}")

        routes_result = await db.execute(
            select(ProviderRoute).where(
                ProviderRoute.model_id == model.id,
                ProviderRoute.is_active.is_(True),
            )
        )
        routes = list(routes_result.scalars().all())
        if not routes:
            raise HTTPException(status_code=404, detail="No routes available")

        circuit_breaker = _get_circuit_breaker(request)
        engine = RoutingEngine(circuit_breaker)
        context = {
            "model": body.model,
            "messages": [m.model_dump() for m in body.messages],
            "max_tokens": body.max_tokens or 4096,
        }
        primary_route = await engine.select_route(body.model, routes, request_context=context)

        if body.stream:
            return StreamingResponse(
                _stream_response(request_id, primary_route, body, circuit_breaker, start),
                media_type="text/event-stream",
            )

        fallback_routes = [r for r in routes if r.id != primary_route.id]
        response, attempted = await execute_with_fallback(
            primary_route, fallback_routes, context, circuit_breaker
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        cost = calculate_cost(primary_route, response.input_tokens, response.output_tokens)

        return {
            "id": request_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response.text},
                    "finish_reason": response.finish_reason or "stop",
                }
            ],
            "usage": {
                "prompt_tokens": response.input_tokens,
                "completion_tokens": response.output_tokens,
                "total_tokens": response.input_tokens + response.output_tokens,
            },
            "gateway_metadata": {
                "selected_route": {
                    "provider": primary_route.provider_key,
                    "model": primary_route.provider_model_id,
                    "region": primary_route.region,
                },
                "routing_strategy": "cost_optimized",
                "fallback_chain": attempted,
                "cache_hit": False,
                "cost_usd_cents": float(cost),
                "latency_ms": latency_ms,
            },
        }

    except PatchbayError as e:
        raise HTTPException(status_code=502, detail=str(e))


async def _stream_response(
    request_id: str,
    route: Any,
    body: ChatCompletionRequest,
    circuit_breaker: CircuitBreaker,
    start: float,
):
    """Generate SSE streaming response."""
    adapter = ProviderRegistry.get_adapter(route.provider_key)
    normalized = NormalizedRequest(
        messages=[m.model_dump() for m in body.messages],
        max_tokens=body.max_tokens or 4096,
        temperature=body.temperature,
        stream=True,
    )

    try:
        async for chunk in adapter.stream(route, normalized):
            if chunk.text_delta:
                sse_data = json.dumps({
                    "id": request_id,
                    "choices": [{"index": 0, "delta": {"content": chunk.text_delta}, "finish_reason": None}],
                })
                yield f"data: {sse_data}\n\n"
            if chunk.finish_reason:
                latency_ms = int((time.monotonic() - start) * 1000)
                metadata = json.dumps({
                    "id": request_id,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": chunk.finish_reason}],
                    "gateway_metadata": {"latency_ms": latency_ms, "selected_route": {"provider": route.provider_key}},
                })
                yield f"data: {metadata}\n\n"
                yield "data: [DONE]\n\n"
        await circuit_breaker.record_success(str(route.id))
    except Exception as e:
        await circuit_breaker.record_failure(str(route.id))
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/messages")
async def anthropic_passthrough(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Anthropic Messages API passthrough endpoint."""
    body = await request.json()
    adapter = ProviderRegistry.get_adapter("anthropic")
    normalized = adapter.normalize_request(body)
    model_name = body.get("model", "claude-sonnet-4")

    model_result = await db.execute(select(LLMModel).where(LLMModel.canonical_name == model_name))
    model = model_result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

    routes_result = await db.execute(
        select(ProviderRoute).where(ProviderRoute.model_id == model.id, ProviderRoute.is_active.is_(True))
    )
    routes = list(routes_result.scalars().all())
    if not routes:
        raise HTTPException(status_code=404, detail="No routes available")

    response = await adapter.send(routes[0], normalized)
    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": response.text}],
        "model": body.get("model"),
        "stop_reason": response.finish_reason,
        "usage": {"input_tokens": response.input_tokens, "output_tokens": response.output_tokens},
    }


@router.post("/responses")
async def openai_responses_passthrough(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """OpenAI Responses API passthrough endpoint."""
    body = await request.json()
    model_name = body.get("model", "gpt-4o")

    model_result = await db.execute(select(LLMModel).where(LLMModel.canonical_name == model_name))
    model = model_result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

    routes_result = await db.execute(
        select(ProviderRoute).where(ProviderRoute.model_id == model.id, ProviderRoute.is_active.is_(True))
    )
    routes = list(routes_result.scalars().all())
    if not routes:
        raise HTTPException(status_code=404, detail="No routes available")

    adapter = ProviderRegistry.get_adapter(routes[0].provider_key)
    normalized = adapter.normalize_request({"messages": body.get("input", [])})
    response = await adapter.send(routes[0], normalized)

    return {
        "id": f"resp_{uuid.uuid4().hex[:12]}",
        "object": "response",
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": response.text}]}],
        "usage": {"input_tokens": response.input_tokens, "output_tokens": response.output_tokens},
    }


@router.post("/embeddings")
async def embeddings(
    body: EmbeddingRequest,
    request: Request,
) -> dict:
    """Embeddings endpoint — uses OpenAI's text-embedding-ada-002."""
    texts = [body.input] if isinstance(body.input, str) else body.input
    # Placeholder — real implementation calls embedding model
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "embedding": [0.0] * 1536, "index": i}
            for i, _ in enumerate(texts)
        ],
        "model": body.model,
        "usage": {"prompt_tokens": sum(len(t) // 4 for t in texts), "total_tokens": sum(len(t) // 4 for t in texts)},
    }
