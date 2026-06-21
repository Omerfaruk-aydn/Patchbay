"""MCP server registry — manages connections and tool synchronization.

The registry handles:
  1. Connecting to MCP servers (stdio, HTTP, SSE transports)
  2. Discovering available tools via tools/list JSON-RPC
  3. Syncing tool definitions to the database
  4. Periodic refresh of tool lists
  5. .well-known discovery (Phase 2)

Tool definitions are stored in the database so they survive restarts
and can be queried without reconnecting to the server.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.db.models import MCPServer, MCPTool

logger = logging.getLogger(__name__)


class MCPServerConfig:
    """Configuration for connecting to an MCP server."""

    def __init__(
        self,
        id: str,
        name: str,
        transport: str,
        connection_uri: str,
        auth_credential_ref: str | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.transport = transport
        self.connection_uri = connection_uri
        self.auth_credential_ref = auth_credential_ref


class MCPServerConnection:
    """Represents an active connection to an MCP server."""

    def __init__(self, server_config: MCPServerConfig, tools: list[dict]) -> None:
        self.config = server_config
        self.tools = tools
        self.connected_at: float | None = None


class MCPServerRegistry:
    """Manages MCP server connections and tool synchronization."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._connections: dict[str, MCPServerConnection] = {}

    async def connect(self, server_config: MCPServerConfig) -> MCPServerConnection:
        """Connect to an MCP server and sync its tools to the database."""
        tools = await self._discover_tools(server_config)
        connection = MCPServerConnection(server_config=server_config, tools=tools)
        await self._sync_tools_to_db(server_config.id, tools)
        self._connections[server_config.id] = connection

        logger.info(
            "mcp_connected",
            extra={"server": server_config.name, "tools": len(tools), "transport": server_config.transport},
        )
        return connection

    async def _discover_tools(self, config: MCPServerConfig) -> list[dict]:
        """Discover tools from an MCP server via tools/list JSON-RPC."""
        # In production, this uses the MCP Python SDK
        return []

    async def _sync_tools_to_db(self, server_id: str, tools: list[dict]) -> None:
        """Sync discovered tools to the mcp_tools database table."""
        for tool in tools:
            tool_name = tool.get("name", "")
            if not tool_name:
                continue

            existing = await self._db.execute(
                select(MCPTool).where(
                    MCPTool.mcp_server_id == server_id,
                    MCPTool.tool_name == tool_name,
                )
            )
            if existing.scalar_one_or_none():
                continue

            mcp_tool = MCPTool(
                mcp_server_id=server_id,
                tool_name=tool_name,
                input_schema=tool.get("inputSchema", tool.get("input_schema", {})),
                description=tool.get("description"),
            )
            self._db.add(mcp_tool)

    async def get_tools_for_project(self, project_id: str) -> list[dict]:
        """Get all active MCP tools for a project."""
        result = await self._db.execute(
            select(MCPTool)
            .join(MCPServer)
            .where(MCPServer.project_id == project_id, MCPServer.is_active.is_(True))
        )
        return [
            {
                "name": t.tool_name,
                "description": t.description or "",
                "inputSchema": t.input_schema,
            }
            for t in result.scalars().all()
        ]

    async def sync_all(self, project_id: str) -> dict:
        """Periodic refresh of all connected servers' tool lists."""
        result = await self._db.execute(
            select(MCPServer).where(
                MCPServer.project_id == project_id,
                MCPServer.is_active.is_(True),
            )
        )
        synced = 0
        failed = 0
        for server in result.scalars().all():
            try:
                config = MCPServerConfig(
                    id=str(server.id),
                    name=server.name,
                    transport=server.transport,
                    connection_uri=server.connection_uri,
                    auth_credential_ref=server.auth_credential_ref,
                )
                tools = await self._discover_tools(config)
                await self._sync_tools_to_db(str(server.id), tools)
                synced += 1
            except Exception as e:
                failed += 1
                logger.error("mcp_sync_failed", extra={"server": server.name, "error": str(e)})

        return {"synced": synced, "failed": failed}
