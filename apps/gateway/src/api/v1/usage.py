"""Usage and cost tracking endpoints.

Provides queryable usage data:
  - Total requests, tokens, and cost per key/project/time range
  - Per-provider breakdown
  - Cache hit rate
  - Latency percentiles
"""

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
    virtual_key_id: uuid.UUID | None = Query(None, description="Filter by virtual key"),
    start_date: datetime | None = Query(None, description="Start of time range"),
    end_date: datetime | None = Query(None, description="End of time range"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Query usage and cost information.

    Returns aggregated metrics for the specified time range and key.
    """
    query = select(
        func.count(Request.id).label("total_requests"),
        func.coalesce(func.sum(Request.cost_usd_cents), 0).label("total_cost"),
        func.coalesce(func.sum(Request.input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(Request.output_tokens), 0).label("total_output_tokens"),
        func.avg(Request.latency_ms).label("avg_latency_ms"),
        func.count(Request.id).filter(Request.cache_hit.is_(True)).label("cache_hits"),
    )

    if virtual_key_id:
        query = query.where(Request.virtual_key_id == virtual_key_id)
    if start_date:
        query = query.where(Request.created_at >= start_date)
    if end_date:
        query = query.where(Request.created_at <= end_date)

    result = await db.execute(query)
    row = result.one()

    total = row.total_requests or 0
    cache_hits = row.cache_hits or 0

    return {
        "total_requests": total,
        "total_cost_usd_cents": float(row.total_cost),
        "total_input_tokens": row.total_input_tokens or 0,
        "total_output_tokens": row.total_output_tokens or 0,
        "avg_latency_ms": round(float(row.avg_latency_ms), 2) if row.avg_latency_ms else 0,
        "cache_hit_rate": round(cache_hits / total * 100, 2) if total > 0 else 0,
        "cache_hits": cache_hits,
    }
