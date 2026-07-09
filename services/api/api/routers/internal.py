from fastapi import APIRouter
from pydantic import BaseModel

from api.services.mcp_client import introspect_server

router = APIRouter(prefix="/internal", tags=["internal"])


class IntrospectRequest(BaseModel):
    url: str


class IntrospectedTool(BaseModel):
    name: str
    description: str | None
    input_schema: dict | None


class IntrospectResponse(BaseModel):
    ok: bool
    tools: list[IntrospectedTool]
    error: str | None = None


@router.post("/mcp/introspect", response_model=IntrospectResponse)
async def introspect(req: IntrospectRequest) -> IntrospectResponse:
    try:
        tools = await introspect_server(req.url)
        return IntrospectResponse(ok=True, tools=tools)
    except Exception as exc:
        return IntrospectResponse(ok=False, tools=[], error=str(exc))
