import asyncio
import httpx
from sqlalchemy import select
from patchbay_gateway.core.database import async_session_factory
from patchbay_gateway.db.models import MCPServer, MCPTool

async def main():
    async with async_session_factory() as session:
        result = await session.execute(
            select(MCPServer).where(MCPServer.name == "Blender")
        )
        server = result.scalar_one_or_none()
        if not server:
            print("Blender MCP server not found")
            return

        r = httpx.post("http://host.docker.internal:8456/tools/list", json={}, timeout=5)
        tools = r.json().get("tools", [])
        print(f"Discovered {len(tools)} tools from Blender MCP")

        for tool in tools:
            existing = await session.execute(
                select(MCPTool).where(
                    MCPTool.mcp_server_id == server.id,
                    MCPTool.tool_name == tool["name"],
                )
            )
            if existing.scalar_one_or_none():
                print(f"  Tool {tool['name']} already exists, skipping")
                continue

            mcp_tool = MCPTool(
                mcp_server_id=server.id,
                tool_name=tool["name"],
                input_schema=tool.get("inputSchema", {}),
                description=tool.get("description", ""),
            )
            session.add(mcp_tool)
            print(f"  Added tool: {tool['name']}")

        await session.commit()
        print("Sync complete!")

asyncio.run(main())
