from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.db.models import LLMModel

router = APIRouter()


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)) -> dict:
    """List all active LLM models."""
    result = await db.execute(
        select(LLMModel).where(LLMModel.is_active.is_(True))
    )
    models = result.scalars().all()
    return {
        "object": "list",
        "data": [
            {
                "id": m.canonical_name,
                "object": "model",
                "created": int(m.id.time.timestamp()) if hasattr(m.id, "time") else 0,
                "owned_by": m.family,
                "capabilities": m.capabilities,
            }
            for m in models
        ],
    }
