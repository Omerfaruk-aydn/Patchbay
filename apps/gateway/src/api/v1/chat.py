from __future__ import annotations

import time
import uuid
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
    PatchbayError,
)
from patchbay_gateway.db.models import ProviderRoute, LLMModel
from patchbay_gateway.providers.registry import ProviderRegistry
from patchbay_gateway.routing.engine import RoutingEngine
from patchbay_gateway.routing.circuit_breaker import CircuitBreaker
from patchbay_gateway.routing.fallback_chain import execute_with_fallback

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str | list[Any]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False


def _get_circuit_breaker(request: Request) -> CircuitBreaker:
    redis = request.app.state.redis
    return CircuitBreaker(redis)


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """OpenAI-compatible chat completions endpoint with routing."""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    start = time.monotonic()

    try:
        # Resolve model
        model_result = await db.execute(
            select(LLMModel).where(LLMModel.canonical_name == body.model, LLMModel.is_active.is_(True))
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {body.model}")

        # Get available routes
        routes_result = await db.execute(
            select(ProviderRoute).where(
                ProviderRoute.model_id == model.id,
                ProviderRoute.is_active.is_(True),
            )
        )
        routes = list(routes_result.scalars().all())
        if not routes:
            raise HTTPException(status_code=404, detail="No routes available for this model")

        # Route
        circuit_breaker = _get_circuit_breaker(request)
        engine = RoutingEngine(circuit_breaker)
        context = {
            "model": body.model,
            "messages": [m.model_dump() for m in body.messages],
            "max_tokens": body.max_tokens,
        }
        primary_route = await engine.select_route(body.model, routes, request_context=context)

        # Execute with fallback
        fallback_routes = [r for r in routes if r.id != primary_route.id]
        response, attempted = await execute_with_fallback(
            primary_route, fallback_routes, context, circuit_breaker
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        cost = (
            (response.input_tokens / 1_000_000) * float(primary_route.pricing_input_per_million_cents)
            + (response.output_tokens / 1_000_000) * float(primary_route.pricing_output_per_million_cents)
        )

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
                "cost_usd_cents": round(cost, 4),
                "latency_ms": latency_ms,
            },
        }

    except PatchbayError as e:
        raise HTTPException(status_code=502, detail=str(e))
