from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client


async def introspect_server(url: str) -> list[dict]:
    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or None,
                    "input_schema": tool.inputSchema or {"type": "object", "properties": {}},
                }
                for tool in result.tools
            ]


async def get_tools_for_selection(servers: list[dict]) -> list[dict]:
    """Build Ollama-shaped tool defs from already-known (server, tool) metadata.

    No live MCP connection is made here -- the tool metadata is resolved from
    internal-api's Postgres store ahead of time.
    """
    ollama_tools: list[dict] = []
    for server in servers:
        for tool in server["tools"]:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": f'{server["name"]}.{tool["name"]}',
                    "description": tool.get("description") or "",
                    "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
                },
            })
    return ollama_tools


async def call_tool_by_namespaced_name(
    servers: list[dict], namespaced_name: str, arguments: dict[str, Any]
) -> str:
    server_name, _, tool_name = namespaced_name.partition(".")
    server = next((s for s in servers if s["name"] == server_name), None)
    if server is None:
        return f"Tool '{namespaced_name}' not found: unknown server '{server_name}'."
    try:
        async with sse_client(server["url"]) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return "\n".join(c.text for c in result.content if hasattr(c, "text"))
    except Exception as exc:
        return f"Tool '{namespaced_name}' failed: {exc}"
