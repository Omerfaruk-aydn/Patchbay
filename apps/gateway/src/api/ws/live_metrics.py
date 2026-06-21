from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

connected_clients: set[WebSocket] = set()


@router.websocket("/live")
async def live_metrics(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time metrics."""
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            # Keep connection alive, receive pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        connected_clients.discard(websocket)


async def broadcast_metric(metric: dict) -> None:
    """Broadcast a metric to all connected WebSocket clients."""
    message = json.dumps(metric)
    disconnected: list[WebSocket] = []
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        connected_clients.discard(client)
