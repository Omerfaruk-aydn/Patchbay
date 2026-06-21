"""WebSocket endpoint for real-time metrics streaming.

Streams live metrics to the dashboard:
  - Request events (new request, completion, error)
  - Cost updates
  - Circuit breaker state changes
  - MCP tool call events
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

connected_clients: set[WebSocket] = set()


@router.websocket("/live")
async def live_metrics(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time dashboard metrics."""
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("ws_client_connected", extra={"total": len(connected_clients)})

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        logger.info("ws_client_disconnected", extra={"total": len(connected_clients)})
    except Exception as e:
        connected_clients.discard(websocket)
        logger.error("ws_error", extra={"error": str(e)})


async def broadcast_metric(metric: dict[str, Any]) -> None:
    """Broadcast a metric event to all connected WebSocket clients."""
    message = json.dumps(metric, default=str)
    disconnected: list[WebSocket] = []

    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        connected_clients.discard(client)


async def broadcast_request_event(
    event_type: str,
    request_id: str,
    provider: str,
    model: str,
    latency_ms: float | None = None,
    cost_usd_cents: float | None = None,
) -> None:
    """Broadcast a request lifecycle event."""
    await broadcast_metric({
        "type": event_type,
        "request_id": request_id,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "cost_usd_cents": cost_usd_cents,
    })
