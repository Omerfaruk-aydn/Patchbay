from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.db.seed import run_seed

router = APIRouter()


@router.post("/seed")
async def seed_data(db: AsyncSession = Depends(get_db)) -> dict:
    """Seed default organization, models, routes, and policies."""
    await run_seed(db)
    return {"status": "seeded"}
