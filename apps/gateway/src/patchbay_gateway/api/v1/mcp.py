"""MCP (Model Context Protocol) server management endpoints.

Provides CRUD operations for MCP server connections:
  - Register new MCP servers
  - List connected servers and their tools
  - Sync tool lists
  - Test connectivity
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.db.models import MCPServer

router = APIRouter()


class MCPServerCreate(BaseModel):
    """Request body for registering an MCP server."""

    project_id: uuid.UUID = Field(description="Project this server belongs to")
    name: str = Field(description="Human-readable server name")
    transport: str = Field(description="Transport type: stdio, streamable_http, or sse")
    connection_uri: str = Field(description="Server connection URI")


@router.post("/mcp/servers")
async def create_mcp_server(
    body: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new MCP server connection."""
    if body.transport not in ("stdio", "streamable_http", "sse"):
        raise HTTPException(status_code=422, detail="transport must be stdio, streamable_http, or sse")

    server = MCPServer(
        project_id=body.project_id,
        name=body.name,
        transport=body.transport,
        connection_uri=body.connection_uri,
    )
    db.add(server)
    await db.flush()

    return {
        "id": str(server.id),
        "name": server.name,
        "transport": server.transport,
        "connection_uri": server.connection_uri,
        "is_active": server.is_active,
        "discovered_via": server.discovered_via,
        "created_at": server.created_at.isoformat(),
    }


@router.get("/mcp/servers")
async def list_mcp_servers(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List MCP servers for a project."""
    result = await db.execute(
        select(MCPServer)
        .where(MCPServer.project_id == project_id)
        .order_by(MCPServer.created_at.desc())
    )
    servers = result.scalars().all()

    return {
        "object": "list",
        "data": [
            {
                "id": str(s.id),
                "name": s.name,
                "transport": s.transport,
                "connection_uri": s.connection_uri,
                "is_active": s.is_active,
                "discovered_via": s.discovered_via,
                "created_at": s.created_at.isoformat(),
            }
            for s in servers
        ],
    }


@router.delete("/mcp/servers/{server_id}")
async def delete_mcp_server(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disconnect and remove an MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    await db.delete(server)
    return {"deleted": True, "id": str(server_id)}
