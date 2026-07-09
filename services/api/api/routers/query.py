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
    if req.generate and results:
        context = "\n\n".join(r.text for r in results)
        user_content = (
            f"Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {req.query}\n\n"
            f"Answer:"
        )
        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Answer questions directly and concisely "
                    "using the provided context. Do not begin your answer with phrases like "
                    "'According to the context', 'Based on the context', or similar meta-references. "
                    "Just answer the question. You may use bullet points."
                ),
            },
            {"role": "user", "content": user_content},
        ]

        tools = await get_tools(settings.mcp_servers)

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
