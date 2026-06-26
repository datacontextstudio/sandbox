import hashlib
import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from worker.config import settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def _ensure_collection(collection_name: str, vector_size: int) -> None:
    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s' (dim=%d)", collection_name, vector_size)


def _chunk_id(file_path: str, chunk_index: int) -> str:
    digest = hashlib.sha256(f"{file_path}:{chunk_index}".encode()).hexdigest()
    return str(uuid.UUID(digest[:32]))


def upsert_chunks(
    collection_name: str,
    chunks: list[str],
    embeddings: list[list[float]],
    job_id: str,
    file_path: str,
    metadata: dict[str, Any],
) -> int:
    if not chunks:
        return 0

    vector_size = len(embeddings[0])
    _ensure_collection(collection_name, vector_size)

    points = [
        PointStruct(
            id=_chunk_id(file_path, i),
            vector=embedding,
            payload={
                "text": chunk,
                "job_id": job_id,
                "file_path": file_path,
                "chunk_index": i,
                **metadata,
            },
        )
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]

    _get_client().upsert(collection_name=collection_name, points=points, wait=True)
    logger.info("Upserted %d points into '%s'", len(points), collection_name)
    return len(points)
