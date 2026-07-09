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
            f"for live/current data such as transaction status):\n"
            f"{context or '(no relevant documents retrieved for this query)'}\n\n"
            f"Question: {req.query}\n\n"
            f"Answer:"
        )
        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Answer questions directly and concisely. "
                    "Never mention or reference your own process: do not refer to 'the context', "
                    "'the provided documents', 'the retrieved text', 'section X', 'the transaction log', "
                    "tool names, function calls, or how you arrived at your answer, anywhere in your reply "
                    "-- not just at the start. Do not narrate your own reasoning, self-corrections, or "
                    "internal steps (for example, never say things like 'so I removed it from the list' "
                    "or 'let me check that'). Just state the answer as fact, in your own words, as if you "
                    "already knew it. You may use bullet points.\n\n"
                    "When tools are available: if the user asks about a specific transaction's current "
                    "status, asks you to list or look up transactions, or asks you to perform an action "
                    "such as issuing a refund, you MUST call the appropriate tool and base your answer "
                    "only on that tool's result. Retrieved background documents (policy text, sample "
                    "reports, FAQs) are general reference material only -- they are never a source of "
                    "truth for a specific transaction's live status, and must never be used to answer "
                    "questions that a tool can answer. Never claim an action such as a refund was "
                    "completed, and never state a transaction's status, unless a tool call actually "
                    "confirmed it in this conversation. If a required tool call fails or a tool is "
                    "unavailable, say so plainly instead of guessing or inventing a result."
                ),
            },
            {"role": "user", "content": user_content},
        ]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for _ in range(_MAX_TOOL_ITERATIONS):
                    payload: dict = {
                        "model": req.llm_model,
                        "messages": messages,
                        "stream": False,
                    }
                    if tools:
                        payload["tools"] = tools

                    resp = await client.post(
                        f"{settings.ollama_base_url}/api/chat",
                        json=payload,
                    )
                    resp.raise_for_status()
                    msg = resp.json()["message"]

                    tool_calls = msg.get("tool_calls")
                    if not tool_calls:
                        answer = msg["content"]
                        break

                    # Append assistant turn (with tool_calls) then execute each call
                    messages.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": tool_calls})
                    for tc in tool_calls:
                        fn = tc["function"]
                        name = fn["name"]
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            args = json.loads(args)
                        result = await call_tool(settings.mcp_servers, name, args)
                        tool_responses.append(ToolResponse(tool=name, response=result))
                        messages.append({"role": "tool", "content": result})
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"LLM service error: {exc}")

    return QueryResponse(
        query=req.query,
        results=results if req.include_results else None,
        answer=answer,
        tool_responses=tool_responses or None,
    )
