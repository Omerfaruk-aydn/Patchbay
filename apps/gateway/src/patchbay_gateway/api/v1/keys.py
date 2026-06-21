"""Virtual key management endpoints.

Implements the BYOK (Bring Your Own Key) model:
  - Users create virtual keys that map to their provider credentials
  - Real provider keys are stored in a secret manager (Vault/Doppler)
  - Virtual keys are used for authentication, rate limiting, and budget tracking
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.core.security import generate_virtual_key, verify_virtual_key
from patchbay_gateway.db.models import VirtualKey

router = APIRouter()


class KeyCreateRequest(BaseModel):
    """Request body for creating a virtual key."""

    name: str = Field(description="Human-readable key name")
    project_id: uuid.UUID = Field(description="Project this key belongs to")
    scopes: list[str] = Field(
        default=["chat:write"],
        description="Permission scopes (chat:write, admin:keys, etc.)",
    )
    rate_limit_rpm: int | None = Field(
        default=None,
        ge=1,
        description="Rate limit in requests per minute (null = unlimited)",
    )
    budget_usd_cents: int | None = Field(
        default=None,
        ge=0,
        description="Monthly budget in USD cents (null = unlimited)",
    )


class KeyResponse(BaseModel):
    """Response for a virtual key (without the raw key after creation)."""

    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    rate_limit_rpm: int | None
    budget_usd_cents: int | None
    created_at: str


@router.post("/keys", response_model=dict)
async def create_key(
    body: KeyCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new virtual API key.

    The raw key is returned ONLY in this response. It cannot be
    retrieved later — store it securely.
    """
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
        "warning": "Store this key securely. It cannot be retrieved later.",
    }


@router.get("/keys")
async def list_keys(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List virtual keys for a project.

    Returns key metadata without the raw key or hash.
    """
    result = await db.execute(
        select(VirtualKey)
        .where(VirtualKey.project_id == project_id)
        .order_by(VirtualKey.created_at.desc())
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
                "rate_limit_rpm": k.rate_limit_rpm,
                "budget_usd_cents": k.budget_usd_cents,
                "created_at": k.created_at.isoformat(),
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ],
    }


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a virtual key.

    The key immediately stops working for all future requests.
    """
    result = await db.execute(select(VirtualKey).where(VirtualKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    await db.delete(key)
    return {"deleted": True, "id": str(key_id)}


@router.patch("/keys/{key_id}/toggle")
async def toggle_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Toggle a virtual key's active state (enable/disable)."""
    result = await db.execute(select(VirtualKey).where(VirtualKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = not key.is_active
    return {"id": str(key.id), "is_active": key.is_active}
