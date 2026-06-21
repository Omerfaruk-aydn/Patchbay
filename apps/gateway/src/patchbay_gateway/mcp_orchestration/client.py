"""MCP Client — connects to MCP servers via stdio or SSE transport.

Implements the JSON-RPC 2.0 protocol used by MCP for:
  - tools/list: discover available tools
  - tools/call: invoke a tool
  - initialize: handshake with the server
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)


class MCPStdioClient:
    """Connects to an MCP server via stdin/stdout (subprocess)."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._command = command
        self._args = args or []
        self._env = env or {}
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._read_task: asyncio.Task | None = None
        self._initialized = False

    async def start(self) -> None:
        """Start the MCP server subprocess."""
        full_env = {**os.environ, **self._env}
        self._process = await asyncio.create_subprocess_exec(
            self._command,
            *self._args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
        )
        self._read_task = asyncio.create_task(self._read_loop())
        await self._initialize()

    async def stop(self) -> None:
        """Stop the subprocess."""
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()

    async def _read_loop(self) -> None:
        """Read JSON-RPC responses from stdout."""
        assert self._process and self._process.stdout
        buffer = ""
        while True:
            line = await self._process.stdout.readline()
            if not line:
                break
            text = line.decode().strip()
            if not text:
                continue
            try:
                msg = json.loads(text)
                req_id = msg.get("id")
                if req_id is not None and req_id in self._pending:
                    self._pending[req_id].set_result(msg)
                elif msg.get("method"):
                    await self._handle_notification(msg)
            except json.JSONDecodeError:
                logger.warning("mcp_non_json_line", extra={"line": text[:200]})

        for future in self._pending.values():
            if not future.done():
                future.set_exception(ConnectionError("Server process ended"))

    async def _handle_notification(self, msg: dict) -> None:
        """Handle server-initiated notifications."""
        method = msg.get("method", "")
        logger.debug("mcp_notification", extra={"method": method})

    async def _send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and wait for response."""
        assert self._process and self._process.stdin
        self._request_id += 1
        req_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params:
            request["params"] = params

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future

        data = json.dumps(request) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()

        try:
            response = await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise TimeoutError(f"MCP request timed out: {method}")

        self._pending.pop(req_id, None)

        if "error" in response:
            error = response["error"]
            raise RuntimeError(f"MCP error {error.get('code')}: {error.get('message')}")

        return response.get("result", {})

    async def _initialize(self) -> None:
        """Perform MCP initialize handshake."""
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "patchbay-gateway",
                "version": "0.1.0",
            },
        })
        self._initialized = True
        logger.info("mcp_initialized", extra={"server_capabilities": result.get("capabilities", {})})

        # Send initialized notification
        assert self._process and self._process.stdin
        notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self._process.stdin.write((json.dumps(notification) + "\n").encode())
        await self._process.stdin.drain()

    async def list_tools(self) -> list[dict]:
        """Discover available tools from the MCP server."""
        result = await self._send_request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Invoke a tool on the MCP server."""
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        return result.get("content", result)
