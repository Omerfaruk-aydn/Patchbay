"""Blender MCP server — bridges Blender's socket API to MCP protocol.

Runs as a standalone SSE server that Patchbay gateway can connect to.
Exposes Blender tools (get_scene_info, execute_code, etc.) as MCP tools.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import sys
from typing import Any

import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger("blender-mcp-server")

BLENDER_HOST = os.getenv("BLENDER_HOST", "localhost")
BLENDER_PORT = int(os.getenv("BLENDER_PORT", "9876"))
SSE_HOST = os.getenv("SSE_HOST", "0.0.0.0")
SSE_PORT = int(os.getenv("SSE_PORT", "8456"))

MCP_TOOLS = [
    {
        "name": "get_scene_info",
        "description": "Get detailed information about the current Blender scene including objects, materials, and settings",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_object_info",
        "description": "Get detailed information about a specific object in the Blender scene",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "description": "Name of the object to get info about"},
            },
            "required": ["object_name"],
        },
    },
    {
        "name": "execute_code",
        "description": "Execute arbitrary Python code in Blender's context. Can modify scenes, create objects, change materials, etc.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute in Blender"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "get_viewport_screenshot",
        "description": "Capture a screenshot of the current Blender 3D viewport",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


class BlenderConnection:
    """Direct socket connection to Blender addon."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    async def connect(self) -> bool:
        """Connect to Blender's socket server."""
        try:
            loop = asyncio.get_event_loop()
            self._sock = await loop.run_in_executor(None, self._create_socket)
            return True
        except Exception as e:
            logger.error("blender_connect_failed", extra={"error": str(e)})
            return False

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect((self._host, self._port))
        return sock

    async def execute(self, command: dict) -> dict:
        """Send a command to Blender and return the response."""
        if not self._sock:
            connected = await self.connect()
            if not connected:
                return {"status": "error", "message": "Not connected to Blender"}

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._send_command, command)
        except Exception as e:
            self._sock = None
            return {"status": "error", "message": str(e)}

    def _send_command(self, command: dict) -> dict:
        """Send command and receive response (blocking)."""
        assert self._sock
        data = json.dumps(command).encode("utf-8")
        self._sock.sendall(data)

        self._sock.settimeout(30.0)
        chunks = []
        while True:
            chunk = self._sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                full = b"".join(chunks)
                return json.loads(full.decode("utf-8"))
            except json.JSONDecodeError:
                continue

        raise ConnectionError("Empty response from Blender")

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None


blender_conn = BlenderConnection(BLENDER_HOST, BLENDER_PORT)


async def mcp_initialize(request: Request) -> JSONResponse:
    """MCP initialize endpoint."""
    return JSONResponse({
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "blender-mcp", "version": "0.1.0"},
    })


async def mcp_tools_list(request: Request) -> JSONResponse:
    """List available Blender tools."""
    return JSONResponse({"tools": MCP_TOOLS})


async def mcp_tools_call(request: Request) -> JSONResponse:
    """Call a Blender tool."""
    body = await request.json()
    tool_name = body.get("name", "")
    arguments = body.get("arguments", {})

    cmd_map = {
        "get_scene_info": {"type": "get_scene_info"},
        "get_object_info": {"type": "get_object_info", "params": arguments},
        "execute_code": {"type": "execute_code", "params": arguments},
        "get_viewport_screenshot": {"type": "get_viewport_screenshot"},
    }

    command = cmd_map.get(tool_name)
    if not command:
        return JSONResponse({"error": f"Unknown tool: {tool_name}"}, status_code=400)

    result = await blender_conn.execute(command)

    content = []
    if isinstance(result.get("result"), dict):
        content.append({"type": "text", "text": json.dumps(result["result"], indent=2)})
    elif isinstance(result.get("result"), str):
        content.append({"type": "text", "text": result["result"]})
    else:
        content.append({"type": "text", "text": json.dumps(result, indent=2)})

    return JSONResponse({"content": content})


async def mcp_sse(request: Request) -> EventSourceResponse:
    """MCP SSE transport endpoint."""
    async def generator():
        # Send endpoint event for streamable HTTP clients
        yield {"event": "endpoint", "data": "/messages"}
        # Keep connection alive
        try:
            while True:
                await asyncio.sleep(30)
                yield {"event": "heartbeat", "data": "ok"}
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(generator())


async def health(request: Request) -> JSONResponse:
    """Health check."""
    return JSONResponse({"status": "ok", "service": "blender-mcp-server"})


app = Starlette(
    routes=[
        Route("/health", health),
        Route("/sse", mcp_sse),
        Route("/initialize", mcp_initialize, methods=["POST"]),
        Route("/tools/list", mcp_tools_list, methods=["POST"]),
        Route("/tools/call", mcp_tools_call, methods=["POST"]),
    ],
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"BlenderMCP SSE server starting on {SSE_HOST}:{SSE_PORT}")
    print(f"Connecting to Blender at {BLENDER_HOST}:{BLENDER_PORT}")
    uvicorn.run(app, host=SSE_HOST, port=SSE_PORT, log_level="info")
