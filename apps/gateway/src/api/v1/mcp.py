from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.core.database import get_db
from patchbay_gateway.db.models import MCPServer

router = APIRouter()


class MCPServerCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    transport: str
    connection_uri: str


@router.post("/mcp/servers")
async def create_mcp_server(
    body: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register an MCP server."""
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
        "is_active": server.is_active,
    }


@router.get("/mcp/servers")
async def list_mcp_servers(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List MCP servers for a project."""
    result = await db.execute(
        select(MCPServer).where(MCPServer.project_id == project_id)
    )
    servers = result.scalars().all()
    return {
        "object": "list",
        "data": [
            {
                "id": str(s.id),
                "name": s.name,
                "transport": s.transport,
                "is_active": s.is_active,
            }
            for s in servers
        ],
    }
