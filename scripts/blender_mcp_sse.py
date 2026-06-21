"""BlenderMCP SSE Wrapper - exposes BlenderMCP as SSE endpoint for Patchbay."""
import asyncio
import json
import os
import sys
import subprocess
from pathlib import Path
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

BLENDER_HOST = os.getenv("BLENDER_HOST", "localhost")
BLENDER_PORT = int(os.getenv("BLENDER_PORT", "9876"))
SSE_HOST = os.getenv("SSE_HOST", "0.0.0.0")
SSE_PORT = int(os.getenv("SSE_PORT", "8456"))


async def sse_endpoint(request):
    """SSE endpoint that bridges MCP protocol over HTTP."""
    async def event_generator():
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "blender_mcp.server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "BLENDER_HOST": BLENDER_HOST, "BLENDER_PORT": str(BLENDER_PORT)},
        )

        async def read_stdout():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode().strip()
                if text:
                    yield {"event": "message", "data": text}

        async def read_stderr():
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                text = line.decode().strip()
                if text:
                    print(f"[blender-mcp] {text}", file=sys.stderr)

        stdout_task = asyncio.create_task(asyncio.coroutine(lambda: None)())

        async def stream_messages():
            try:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    text = line.decode().strip()
                    if text:
                        yield {"event": "message", "data": text}
            except asyncio.CancelledError:
                pass
            finally:
                if proc.returncode is None:
                    proc.terminate()

        return stream_messages()

    return EventSourceResponse(event_generator())


async def health(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok", "service": "blender-mcp-sse"})


app = Starlette(
    routes=[
        Route("/sse", endpoint=sse_endpoint),
        Route("/health", endpoint=health),
    ],
)

if __name__ == "__main__":
    print(f"BlenderMCP SSE wrapper starting on {SSE_HOST}:{SSE_PORT}")
    uvicorn.run(app, host=SSE_HOST, port=SSE_PORT, log_level="info")
