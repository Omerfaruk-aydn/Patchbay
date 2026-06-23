"""Blender MCP server — bridges Blender's socket API to MCP protocol.

Provides AI with FULL Blender access via execute_code tool.
Supports: object creation, materials, lighting, camera, mesh editing,
animation, physics, rendering, node editing, import/export, and more.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
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
        "name": "execute_code",
        "description": """Execute arbitrary Python code in Blender's context.
You have FULL access to Blender's Python API (bpy). You can:
- Create/delete/modify objects (meshes, curves, lights, cameras, empties)
- Apply materials, textures, shaders
- Set up lighting (point, sun, area, spot)
- Configure camera (focal length, DOF, ortho/perspective)
- Edit mesh geometry (vertices, edges, faces)
- Set up animations (keyframes, drivers, constraints)
- Configure physics (rigid body, cloth, fluid, particles)
- Render scenes (Cycles, EEVEE)
- Modify node trees (compositor, shader, geometry nodes)
- Import/export files (FBX, OBJ, GLTF, STL, etc.)
- Modify scene settings (render engine, resolution, world)
- Work with collections, groups, parent-child relationships
- Apply modifiers (subdivision, bevel, array, mirror, etc.)
- Create and manage constraints
- Work with drivers and custom properties
- Access and modify Blender preferences

Example: Create a sphere with red material
import bpy
bpy.ops.mesh.primitive_uv_sphere_add(location=(0,0,1))
obj = bpy.context.active_object
obj.name = "RedSphere"
mat = bpy.data.materials.new(name="Red")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs['Base Color'].default_value = (0.8, 0.1, 0.1, 1)
obj.data.materials.append(mat)
print("Red sphere created!")""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute in Blender"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "get_scene_info",
        "description": "Get information about the current Blender scene",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_object_info",
        "description": "Get detailed information about a specific object",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string"},
            },
            "required": ["object_name"],
        },
    },
    {
        "name": "get_viewport_screenshot",
        "description": "Capture a screenshot of the current 3D viewport",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_materials",
        "description": "List all materials in the Blender scene",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_cameras",
        "description": "List all cameras in the Blender scene",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_lights",
        "description": "List all lights in the Blender scene",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_collections",
        "description": "List all collections in the Blender scene",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_modifiers",
        "description": "List all modifiers on a specific object",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string"},
            },
            "required": ["object_name"],
        },
    },
]


class BlenderConnection:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    async def connect(self) -> bool:
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


# ─── MCP Endpoints ───

async def mcp_initialize(request: Request) -> JSONResponse:
    return JSONResponse({
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "blender-mcp", "version": "0.2.0"},
    })


async def mcp_tools_list(request: Request) -> JSONResponse:
    return JSONResponse({"tools": MCP_TOOLS})


async def mcp_tools_call(request: Request) -> JSONResponse:
    body = await request.json()
    tool_name = body.get("name", "")
    arguments = body.get("arguments", {})

    # Build command based on tool
    if tool_name == "execute_code":
        command = {"type": "execute_code", "params": {"code": arguments.get("code", "")}}
    elif tool_name == "get_scene_info":
        command = {"type": "get_scene_info"}
    elif tool_name == "get_object_info":
        command = {"type": "get_object_info", "params": arguments}
    elif tool_name == "get_viewport_screenshot":
        command = {"type": "get_viewport_screenshot", "params": arguments}
    elif tool_name == "list_materials":
        command = {"type": "execute_code", "params": {"code": (
            "import bpy\n"
            "materials = [{'name': m.name, 'users': m.users, 'use_nodes': m.use_nodes} "
            "for m in bpy.data.materials]\n"
            "print(__import__('json').dumps(materials))"
        )}}
    elif tool_name == "list_cameras":
        command = {"type": "execute_code", "params": {"code": (
            "import bpy\n"
            "cameras = [{'name': c.name, 'lens': c.lens, 'type': c.type} "
            "for c in bpy.data.cameras]\n"
            "print(__import__('json').dumps(cameras))"
        )}}
    elif tool_name == "list_lights":
        command = {"type": "execute_code", "params": {"code": (
            "import bpy\n"
            "lights = [{'name': l.name, 'type': l.type, 'energy': l.energy} "
            "for l in bpy.data.lights]\n"
            "print(__import__('json').dumps(lights))"
        )}}
    elif tool_name == "list_collections":
        command = {"type": "execute_code", "params": {"code": (
            "import bpy\n"
            "cols = [{'name': c.name, 'objects': len(c.objects)} "
            "for c in bpy.data.collections]\n"
            "print(__import__('json').dumps(cols))"
        )}}
    elif tool_name == "list_modifiers":
        obj_name = arguments.get("object_name", "")
        command = {"type": "execute_code", "params": {"code": (
            f"import bpy\n"
            f"obj = bpy.data.objects.get('{obj_name}')\n"
            f"if obj:\n"
            f"    mods = [{'name': m.name, 'type': m.type} for m in obj.modifiers]\n"
            f"    print(__import__('json').dumps(mods))\n"
            f"else:\n"
            f"    print('Object not found: {obj_name}')"
        )}}
    else:
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
    async def generator():
        yield {"event": "endpoint", "data": "/messages"}
        try:
            while True:
                await asyncio.sleep(30)
                yield {"event": "heartbeat", "data": "ok"}
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(generator())


async def mcp_messages(request: Request) -> JSONResponse:
    body = await request.json()
    method = body.get("method", "")

    if method == "initialize":
        return await mcp_initialize(request)
    elif method == "tools/list":
        return await mcp_tools_list(request)
    elif method == "tools/call":
        return await mcp_tools_call(request)
    else:
        return JSONResponse({"error": f"Unknown method: {method}"}, status_code=400)


# ─── App ───

app = Starlette(
    routes=[
        Route("/sse", mcp_sse, methods=["GET"]),
        Route("/messages", mcp_messages, methods=["POST"]),
        Route("/tools/call", mcp_tools_call, methods=["POST"]),
        Route("/tools/list", mcp_tools_list, methods=["GET"]),
    ],
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("blender_mcp_server_start", extra={"host": SSE_HOST, "port": SSE_PORT})
    uvicorn.run(app, host=SSE_HOST, port=SSE_PORT, log_level="info")
