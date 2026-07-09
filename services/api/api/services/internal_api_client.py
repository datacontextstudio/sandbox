import httpx

from api.config import settings


async def resolve_selected_tools(tool_ids: list[str]) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.internal_api_base_url}/mcp-servers/resolve",
            params=[("tools", t) for t in tool_ids],
        )
        resp.raise_for_status()
        return resp.json()["servers"]
