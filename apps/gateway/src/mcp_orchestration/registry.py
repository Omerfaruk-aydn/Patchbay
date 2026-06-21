from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.db.models import MCPServer, MCPTool

logger = logging.getLogger(__name__)


class MCPServerConfig:
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


class MCPServer:
    def __init__(self, server_config: MCPServerConfig, tools: list[dict]) -> None:
        self.config = server_config
        self.tools = tools


class MCPServerRegistry:
    """Manages MCP server connections and tool synchronization.

    Supports manual registration, .well-known discovery, and
    periodic tool list refresh.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._connections: dict[str, MCPServer] = {}

    async def connect(self, server_config: MCPServerConfig) -> MCPServer:
        """Connect to an MCP server and sync its tools."""
        # In production, this would use the MCP Python SDK
        # For now, create a stub connection
        tools = await self._discover_tools(server_config)
        server = MCPServer(server_config=server_config, tools=tools)

        # Sync tools to database
        await self._sync_tools_to_db(server_config.id, tools)

        self._connections[server_config.id] = server
        logger.info("mcp_connected", extra={"server": server_config.name, "tools": len(tools)})
        return server

    async def _discover_tools(self, config: MCPServerConfig) -> list[dict]:
        """Discover tools from an MCP server.

        In production, this sends a tools/list JSON-RPC request.
        """
        # Placeholder — real implementation uses MCP SDK
        return []

    async def _sync_tools_to_db(self, server_id: str, tools: list[dict]) -> None:
        """Sync discovered tools to the mcp_tools table."""
        for tool in tools:
            existing = await self._db.execute(
                select(MCPTool).where(
                    MCPTool.mcp_server_id == server_id,
                    MCPTool.tool_name == tool["name"],
                )
            )
            if existing.scalar_one_or_none():
                continue

            mcp_tool = MCPTool(
                mcp_server_id=server_id,
                tool_name=tool["name"],
                input_schema=tool.get("inputSchema", {}),
                description=tool.get("description"),
            )
            self._db.add(mcp_tool)

    async def get_tools_for_project(self, project_id: str) -> list[dict]:
        """Get all tools for a project's connected MCP servers."""
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

    async def sync_all(self, project_id: str) -> None:
        """Periodic refresh of all connected servers' tool lists."""
        result = await self._db.execute(
            select(MCPServer).where(
                MCPServer.project_id == project_id,
                MCPServer.is_active.is_(True),
            )
        )
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
            except Exception as e:
                logger.error("mcp_sync_failed", extra={"server": server.name, "error": str(e)})
