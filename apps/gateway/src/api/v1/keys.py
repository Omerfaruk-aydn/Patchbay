from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.core.security import generate_virtual_key
from patchbay_gateway.db.models import VirtualKey

router = APIRouter()


class KeyCreate(BaseModel):
    name: str
    project_id: uuid.UUID
    scopes: list[str] = []
    rate_limit_rpm: int | None = None
    budget_usd_cents: int | None = None


@router.post("/keys")
async def create_key(
    body: KeyCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new virtual key."""
    raw_key, key_hash, prefix = generate_virtual_key()
    key = VirtualKey(
        project_id=body.project_id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=body.scopes,
        rate_limit_rpm=body.rate_limit_rpm,
        budget_usd_cents=body.budget_usd_cents,
    )
    db.add(key)
    await db.flush()
    return {
        "id": str(key.id),
        "name": key.name,
        "key": raw_key,
        "key_prefix": prefix,
        "scopes": key.scopes,
        "rate_limit_rpm": key.rate_limit_rpm,
        "budget_usd_cents": key.budget_usd_cents,
        "created_at": key.created_at.isoformat(),
    }


@router.get("/keys")
async def list_keys(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List virtual keys for a project."""
    result = await db.execute(
        select(VirtualKey).where(VirtualKey.project_id == project_id)
    )
    keys = result.scalars().all()
    return {
        "object": "list",
        "data": [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat(),
            }
            for k in keys
        ],
    }


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a virtual key."""
    result = await db.execute(select(VirtualKey).where(VirtualKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    await db.delete(key)
    return {"deleted": True, "id": str(key_id)}
