import httpx
from fastapi import APIRouter, HTTPException

from api.config import settings
from api.models import QueryRequest, QueryResponse
from api.services import embedder, searcher

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    try:
        vector = await embedder.embed_text(req.query)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Embedding service error: {exc}")

    try:
        results = await searcher.search(req.collection_name, vector, req.top_k)
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
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                answer = resp.json()["message"]["content"]
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"LLM service error: {exc}")

    return QueryResponse(query=req.query, results=results, answer=answer)
