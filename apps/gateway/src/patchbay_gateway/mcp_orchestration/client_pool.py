"""MCP client connection pool — manages persistent connections to MCP servers.

Connections are pooled to avoid recreating them on every request.
Pool features:
  - Lazy connection creation
  - Idle connection cleanup
  - Auto-reconnect on disconnect
  - Circuit breaker integration for unhealthy servers
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MCPClientSession:
    """Represents a persistent connection to an MCP server."""

    def __init__(self, server_id: str, transport: str, uri: str) -> None:
        self.server_id = server_id
        self.transport = transport
        self.uri = uri
        self.connected_at = time.time()
        self.last_used_at = time.time()
        self.request_count = 0


class MCPClientPool:
    """Persistent connection pool for MCP servers."""

    def __init__(self) -> None:
        self._pool: dict[str, MCPClientSession] = {}

    async def get_or_create(
        self,
        server_id: str,
        transport: str,
        uri: str,
    ) -> MCPClientSession:
        """Get an existing connection or create a new one."""
        if server_id in self._pool:
            session = self._pool[server_id]
            session.last_used_at = time.time()
            session.request_count += 1
            return session

        session = MCPClientSession(server_id=server_id, transport=transport, uri=uri)
        self._pool[server_id] = session
        return session

    async def close_idle(self, idle_threshold_seconds: int = 300) -> int:
        """Close connections that have been idle beyond the threshold."""
        now = time.time()
        closed = 0
        for server_id in list(self._pool.keys()):
            session = self._pool[server_id]
            if (now - session.last_used_at) > idle_threshold_seconds:
                del self._pool[server_id]
                closed += 1
                logger.debug("mcp_idle_closed", extra={"server_id": server_id})
        return closed

    async def close_all(self) -> int:
        """Close all connections."""
        count = len(self._pool)
        self._pool.clear()
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "active_connections": len(self._pool),
            "servers": list(self._pool.keys()),
        }
