from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.db.models import Request

router = APIRouter()


@router.get("/usage")
async def get_usage(
    virtual_key_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Query usage and cost information."""
    query = select(Request)
    count_query = select(
        func.count(Request.id),
        func.coalesce(func.sum(Request.cost_usd_cents), 0),
        func.coalesce(func.sum(Request.input_tokens), 0),
        func.coalesce(func.sum(Request.output_tokens), 0),
        func.avg(Request.latency_ms),
    )

    if virtual_key_id:
        query = query.where(Request.virtual_key_id == virtual_key_id)
        count_query = count_query.where(Request.virtual_key_id == virtual_key_id)
    if start_date:
        query = query.where(Request.created_at >= start_date)
        count_query = count_query.where(Request.created_at >= start_date)
    if end_date:
        query = query.where(Request.created_at <= end_date)
        count_query = count_query.where(Request.created_at <= end_date)

    stats = await db.execute(count_query)
    row = stats.one()

    return {
        "total_requests": row[0],
        "total_cost_usd_cents": float(row[1]),
        "total_input_tokens": row[2],
        "total_output_tokens": row[3],
        "avg_latency_ms": float(row[4]) if row[4] else 0,
    }
