from qdrant_client import AsyncQdrantClient

from api.config import settings
from api.models import QueryResult

_client: AsyncQdrantClient | None = None


def _get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


async def search(collection_name: str, vector: list[float], top_k: int) -> list[QueryResult]:
    client = _get_client()
    hits = await client.query_points(
        collection_name=collection_name,
        query=vector,
        limit=top_k,
    )
    results = []
    for point in hits.points:
        payload = point.payload or {}
        known = {"text", "file_path", "chunk_index", "job_id"}
        metadata = {k: v for k, v in payload.items() if k not in known}
        results.append(
            QueryResult(
                text=payload.get("text", ""),
                score=point.score,
                file_path=payload.get("file_path"),
                chunk_index=payload.get("chunk_index"),
                metadata=metadata,
            )
        )
    return results
