from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Health check endpoint."""
    from sqlalchemy import text

    await db.execute(text("SELECT 1"))
    return {"status": "healthy", "service": "patchbay-gateway"}
