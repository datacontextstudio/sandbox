import httpx
from fastapi import APIRouter, HTTPException

from api.config import settings
from api.models import QueryRequest, QueryResponse
from api.services import embedder
from api.services.searcher import search_many

router = APIRouter()


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
    if req.generate and results:
        context = "\n\n".join(r.text for r in results)
        prompt = (
            f"Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {req.query}\n\n"
            f"Answer:"
        )
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json={
                        "model": req.llm_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a helpful assistant. Answer questions directly and concisely "
                                    "using the provided context. Do not begin your answer with phrases like "
                                    "'According to the context', 'Based on the context', or similar meta-references. "
                                    "Just answer the question."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                answer = resp.json()["message"]["content"]
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"LLM service error: {exc}")

    return QueryResponse(
        query=req.query,
        results=results if req.include_results else None,
        answer=answer,
    )
