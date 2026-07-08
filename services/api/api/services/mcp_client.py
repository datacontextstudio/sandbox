import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client


def _parse_servers(mcp_servers_json: str) -> list[dict]:
    try:
        return json.loads(mcp_servers_json)
    except json.JSONDecodeError:
        return []


@asynccontextmanager
async def _connect(server: dict):
    if server.get("type") == "sse":
        async with sse_client(server["url"]) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    else:
        params = StdioServerParameters(
            command=server["command"],
            args=server.get("args", []),
            env=server.get("env"),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


async def get_tools(mcp_servers_json: str) -> list[dict]:
    servers = _parse_servers(mcp_servers_json)
    ollama_tools: list[dict] = []
    for server in servers:
        try:
            async with _connect(server) as session:
                result = await session.list_tools()
                for tool in result.tools:
                    ollama_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                        },
                    })
        except Exception:
            pass
    return ollama_tools


async def call_tool(mcp_servers_json: str, tool_name: str, arguments: dict[str, Any]) -> str:
    servers = _parse_servers(mcp_servers_json)
    for server in servers:
        try:
            async with _connect(server) as session:
                tools = await session.list_tools()
                if any(t.name == tool_name for t in tools.tools):
                    result = await session.call_tool(tool_name, arguments)
                    parts = [c.text for c in result.content if hasattr(c, "text")]
                    return "\n".join(parts)
        except Exception:
            continue
    return f"Tool '{tool_name}' not found in any configured MCP server."
