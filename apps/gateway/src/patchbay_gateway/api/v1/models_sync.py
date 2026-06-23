"""Sync models endpoint — fetches all models from OpenRouter API."""

from __future__ import annotations

import logging
import time

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.db.models import LLMModel, ProviderRoute

router = APIRouter()
logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"


async def fetch_openrouter_models() -> list[dict]:
    """Fetch all models from OpenRouter API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(OPENROUTER_API_URL)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])


@router.post("/models/sync")
async def sync_models(db: AsyncSession = Depends(get_db)) -> dict:
    """Fetch all models from OpenRouter and upsert into database.

    This replaces the hardcoded seed data with live API data.
    """
    remote_models = await fetch_openrouter_models()

    synced = 0
    created = 0
    skipped = 0

    for m in remote_models:
        model_id = m.get("id", "")
        if not model_id:
            skipped += 1
            continue

        # Skip aliases and free models
        if model_id.startswith("~") or ":free" in model_id:
            skipped += 1
            continue

        # Check if model exists
        result = await db.execute(
            select(LLMModel).where(LLMModel.canonical_name == model_id)
        )
        existing = result.scalar_one_or_none()

        ctx = m.get("context_length", 128000) or 128000

        if existing:
            # Update capabilities
            existing.capabilities = {
                "vision": ctx > 0,
                "tool_use": ctx > 0,
                "context_window": ctx,
                "max_output_tokens": min(ctx, 65536),
                "supports_streaming": True,
            }
            synced += 1
        else:
            # Create new model
            family = model_id.split("/")[0] if "/" in model_id else "unknown"
            model = LLMModel(
                canonical_name=model_id,
                family=family,
                capabilities={
                    "vision": ctx > 0,
                    "tool_use": ctx > 0,
                    "context_window": ctx,
                    "max_output_tokens": min(ctx, 65536),
                    "supports_streaming": True,
                },
            )
            db.add(model)
            await db.flush()

            # Create route
            route = ProviderRoute(
                model_id=model.id,
                provider_key="openrouter",
                provider_model_id=model_id,
                auth_credential_ref="env:OPENROUTER_API_KEY",
                is_active=True,
                pricing_input_per_million_cents=10,
                pricing_output_per_million_cents=30,
            )
            db.add(route)
            created += 1

    await db.commit()

    return {
        "status": "synced",
        "total_fetched": len(remote_models),
        "created": created,
        "updated": synced,
        "skipped": skipped,
    }
