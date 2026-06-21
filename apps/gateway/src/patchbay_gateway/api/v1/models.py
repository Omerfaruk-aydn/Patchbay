"""Model catalog endpoint — lists available LLM models and their capabilities.

Returns the model catalog from the database, including:
  - Canonical model name (e.g., "gpt-4o")
  - Model family (e.g., "openai", "claude", "gemini")
  - Capabilities (vision, tool_use, context_window, etc.)
  - Available provider routes and pricing
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.db.models import LLMModel

router = APIRouter()


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)) -> dict:
    """List all active LLM models.

    Returns OpenAI-compatible model list format with additional
    Patchbay-specific metadata (family, capabilities).
    """
    result = await db.execute(
        select(LLMModel).where(LLMModel.is_active.is_(True)).order_by(LLMModel.family, LLMModel.canonical_name)
    )
    models = result.scalars().all()

    return {
        "object": "list",
        "data": [
            {
                "id": m.canonical_name,
                "object": "model",
                "created": 0,
                "owned_by": m.family,
                "capabilities": m.capabilities,
                "patchbay": {
                    "family": m.family,
                    "context_window": m.capabilities.get("context_window"),
                    "max_output_tokens": m.capabilities.get("max_output_tokens"),
                    "supports_vision": m.capabilities.get("vision", False),
                    "supports_tools": m.capabilities.get("tool_use", False),
                    "supports_streaming": m.capabilities.get("supports_streaming", False),
                },
            }
            for m in models
        ],
    }
