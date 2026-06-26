import asyncio

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from api.config import settings
from api.models import DocumentInfo, QueryResult

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
                collection_name=collection_name,
                file_path=payload.get("file_path"),
                chunk_index=payload.get("chunk_index"),
                metadata=metadata,
            )
        )
    return results


async def search_many(collections: list[str], vector: list[float], top_k: int) -> list[QueryResult]:
    per_collection = await asyncio.gather(*[search(c, vector, top_k) for c in collections])
    merged = [r for results in per_collection for r in results]
    merged.sort(key=lambda r: r.score, reverse=True)
    return merged[:top_k]


async def scroll_documents(collection_name: str) -> list[DocumentInfo]:
    client = _get_client()
    docs: dict[str, DocumentInfo] = {}
    offset = None
    while True:
        result, next_offset = await client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in result:
            payload = point.payload or {}
            job_id = payload.get("job_id", "")
            file_path = payload.get("file_path", "")
            if job_id in docs:
                docs[job_id] = DocumentInfo(
                    job_id=job_id,
                    file_path=file_path,
                    chunk_count=docs[job_id].chunk_count + 1,
                )
            else:
                docs[job_id] = DocumentInfo(job_id=job_id, file_path=file_path, chunk_count=1)
        if next_offset is None:
            break
        offset = next_offset
    return list(docs.values())


async def delete_document_chunks(collection_name: str, job_id: str) -> None:
    client = _get_client()
    await client.delete(
        collection_name=collection_name,
        points_selector=Filter(must=[FieldCondition(key="job_id", match=MatchValue(value=job_id))]),
    )


async def delete_collection_qdrant(collection_name: str) -> None:
    client = _get_client()
    await client.delete_collection(collection_name)
