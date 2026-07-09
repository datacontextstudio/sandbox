import json

import httpx
from fastapi import APIRouter, HTTPException

from api.config import settings
from api.models import QueryRequest, QueryResponse, ToolResponse
from api.services import embedder
from api.services.mcp_client import call_tool, get_tools
from api.services.searcher import search_many

router = APIRouter()

_MAX_TOOL_ITERATIONS = 10

_BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer questions directly and concisely. "
    "Never mention or reference your own process: do not refer to 'the context', "
    "'the provided documents', 'the retrieved text', 'section X', "
    "tool names, function calls, or how you arrived at your answer, anywhere in your reply "
    "-- not just at the start. Do not narrate your own reasoning, self-corrections, or "
    "internal steps (for example, never say things like 'so I removed it from the list' "
    "or 'let me check that'). Just state the answer as fact, in your own words, as if you "
    "already knew it. You may use bullet points."
)

_TOOLS_NEEDED_SUFFIX = (
    "\n\nIf a tool is relevant to what the user is asking, based on that tool's description, "
    "you MUST call it and base your answer only on its result. Retrieved background documents "
    "are general reference material only -- they are never a substitute for a tool when a tool "
    "is available to answer the question directly, and must never be used to answer something a "
    "tool can answer instead. Never claim to have completed an action or retrieved a result "
    "unless a tool call actually confirmed it in this conversation."
)

_TOOLS_UNUSED_SUFFIX = (
    "\n\nNo tools were needed for this request. Answer using only the background context "
    "below and general knowledge. Never claim to have called a tool, retrieved live data via "
    "a tool, or taken an action through a tool."
)


async def _determine_tool_calls(
    client: httpx.AsyncClient, req: QueryRequest, tools: list[dict]
) -> dict | None:
    messages = [
        {
            "role": "system",
            "content": (
                "If the user's request requires calling one of the available tools to get "
                "live/current data or perform an action, call the appropriate tool. Otherwise, "
                "do not call any tool."
            ),
        },
        {"role": "user", "content": req.query},
    ]
    resp = await client.post(
        f"{settings.ollama_base_url}/api/chat",
        json={"model": req.llm_model, "messages": messages, "stream": False, "tools": tools},
    )
    resp.raise_for_status()
    msg = resp.json()["message"]
    return msg if msg.get("tool_calls") else None


async def _run_tool_calls(
    tool_calls: list[dict], messages: list[dict], tool_responses: list[ToolResponse]
) -> None:
    for tc in tool_calls:
        fn = tc["function"]
        name = fn["name"]
        args = fn.get("arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
        result = await call_tool(settings.mcp_servers, name, args)
        tool_responses.append(ToolResponse(tool=name, response=result))
        messages.append({"role": "tool", "content": result})


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    try:
        vector = await embedder.embed_text(req.query)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Embedding service error: {exc}")

    try:
        results = await search_many(req.collections, vector, req.top_k)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Search error: {exc}")

    answer: str | None = None
    tool_responses: list[ToolResponse] = []
    tools = await get_tools(settings.mcp_servers) if req.generate else []
    if req.generate and (results or tools):
        context = "\n\n".join(r.text for r in results) if results else ""
        user_content = (
            f"Background context (may or may not be relevant; do not treat as authoritative "
            f"for anything a tool could answer more accurately):\n"
            f"{context or '(no relevant documents retrieved for this query)'}\n\n"
            f"Question: {req.query}\n\n"
            f"Answer:"
        )

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                determination = await _determine_tool_calls(client, req, tools) if tools else None

                system_suffix = (
                    _TOOLS_NEEDED_SUFFIX if determination else (_TOOLS_UNUSED_SUFFIX if tools else "")
                )
                messages: list[dict] = [
                    {"role": "system", "content": _BASE_SYSTEM_PROMPT + system_suffix},
                    {"role": "user", "content": user_content},
                ]

                if determination:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": determination.get("content", ""),
                            "tool_calls": determination["tool_calls"],
                        }
                    )
                    await _run_tool_calls(determination["tool_calls"], messages, tool_responses)

                    for _ in range(_MAX_TOOL_ITERATIONS - 1):
                        payload = {
                            "model": req.llm_model,
                            "messages": messages,
                            "stream": False,
                            "tools": tools,
                        }
                        resp = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
                        resp.raise_for_status()
                        msg = resp.json()["message"]

                        tool_calls = msg.get("tool_calls")
                        if not tool_calls:
                            answer = msg["content"]
                            break

                        messages.append(
                            {"role": "assistant", "content": msg.get("content", ""), "tool_calls": tool_calls}
                        )
                        await _run_tool_calls(tool_calls, messages, tool_responses)
                else:
                    resp = await client.post(
                        f"{settings.ollama_base_url}/api/chat",
                        json={"model": req.llm_model, "messages": messages, "stream": False},
                    )
                    resp.raise_for_status()
                    answer = resp.json()["message"]["content"]
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"LLM service error: {exc}")

    return QueryResponse(
        query=req.query,
        results=results if req.include_results else None,
        answer=answer,
        tool_responses=tool_responses or None,
    )
