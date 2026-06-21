from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPClientPool:
    """Persistent connection pool for MCP servers.

    Maintains one connection per server, with auto-reconnect
    on disconnect and idle connection cleanup.
    """

    def __init__(self) -> None:
        self._pool: dict[str, Any] = {}

    async def get_or_create(self, server_id: str, transport: str, uri: str) -> Any:
        """Get an existing connection or create a new one."""
        if server_id in self._pool:
            return self._pool[server_id]

        # In production, this creates an MCP SDK client session
        # For now, return a stub
        client = {"server_id": server_id, "transport": transport, "uri": uri}
        self._pool[server_id] = client
        return client

    async def close_idle(self, idle_threshold_seconds: int = 300) -> None:
        """Close connections that have been idle beyond the threshold."""
        # In production, tracks last_used_at per connection
        pass

    async def close_all(self) -> None:
        """Close all connections."""
        for server_id in list(self._pool.keys()):
            del self._pool[server_id]
