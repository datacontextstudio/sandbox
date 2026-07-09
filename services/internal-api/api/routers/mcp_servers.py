from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from api.config import settings
from api.database import McpTool, McpToolServer, get_session
from api.models import CreateMcpServerRequest, McpServerResponse

router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])


async def _introspect(url: str) -> tuple[bool, list[dict], str | None]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{settings.api_base_url}/internal/mcp/introspect", json={"url": url})
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach introspection service") from exc

    body = resp.json()
    return body["ok"], body["tools"], body.get("error")


def _server_query():
    return select(McpToolServer).options(selectinload(McpToolServer.tools))


@router.get("", response_model=list[McpServerResponse])
async def list_servers(db: AsyncSession = Depends(get_session)) -> list[McpServerResponse]:
    result = await db.execute(_server_query().order_by(McpToolServer.created_at))
    return [McpServerResponse.model_validate(s) for s in result.scalars().all()]


@router.post("", response_model=McpServerResponse, status_code=201)
async def create_server(
    body: CreateMcpServerRequest,
    db: AsyncSession = Depends(get_session),
) -> McpServerResponse:
    existing = await db.execute(select(McpToolServer).where(McpToolServer.name == body.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail=f"A tool server named '{body.name}' already exists")

    ok, tools, error = await _introspect(body.url)

    server = McpToolServer(
        name=body.name,
        url=body.url,
        status="ok" if ok else "unreachable",
        last_introspected_at=datetime.now(timezone.utc) if ok else None,
    )
    if ok:
        server.tools = [
            McpTool(name=t["name"], description=t.get("description"), input_schema=t.get("input_schema"))
            for t in tools
        ]
    db.add(server)
    await db.commit()
    await db.refresh(server, attribute_names=["tools"])

    response = McpServerResponse.model_validate(server)
    if not ok:
        response.detail = f"Server added, but could not connect: {error}"
    return response


@router.post("/{server_id}/refresh", response_model=McpServerResponse)
async def refresh_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> McpServerResponse:
    result = await db.execute(_server_query().where(McpToolServer.id == server_id))
    server = result.scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=404, detail="Tool server not found")

    ok, tools, error = await _introspect(server.url)

    server.tools = []
    await db.flush()
    if ok:
        server.tools = [
            McpTool(name=t["name"], description=t.get("description"), input_schema=t.get("input_schema"))
            for t in tools
        ]
    server.status = "ok" if ok else "unreachable"
    server.last_introspected_at = datetime.now(timezone.utc) if ok else server.last_introspected_at
    await db.commit()
    await db.refresh(server, attribute_names=["tools"])

    response = McpServerResponse.model_validate(server)
    if not ok:
        response.detail = f"Could not connect: {error}"
    return response


@router.get("/resolve")
async def resolve_tools(
    tools: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_session),
) -> dict:
    if not tools:
        return {"servers": []}

    requested_by_server: dict[str, set[str]] = {}
    for namespaced_id in tools:
        server_name, _, tool_name = namespaced_id.partition(".")
        requested_by_server.setdefault(server_name, set()).add(tool_name)

    result = await db.execute(
        _server_query().where(McpToolServer.name.in_(requested_by_server.keys()))
    )
    servers = []
    for server in result.scalars().all():
        requested_tool_names = requested_by_server[server.name]
        matched_tools = [t for t in server.tools if t.name in requested_tool_names]
        if not matched_tools:
            continue
        servers.append({
            "name": server.name,
            "url": server.url,
            "tools": [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in matched_tools
            ],
        })
    return {"servers": servers}


@router.get("/{server_id}", response_model=McpServerResponse)
async def get_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> McpServerResponse:
    result = await db.execute(_server_query().where(McpToolServer.id == server_id))
    server = result.scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=404, detail="Tool server not found")
    return McpServerResponse.model_validate(server)


@router.delete("/{server_id}", status_code=204)
async def delete_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    result = await db.execute(select(McpToolServer).where(McpToolServer.id == server_id))
    server = result.scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=404, detail="Tool server not found")
    await db.delete(server)
    await db.commit()
