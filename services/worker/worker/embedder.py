import logging

import httpx

from worker.config import settings

logger = logging.getLogger(__name__)


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    batch_size = settings.embed_batch_size

    with httpx.Client(timeout=120.0) as client:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            response = client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.embed_model, "input": batch},
            )
            response.raise_for_status()
            data = response.json()
            embeddings.extend(data["embeddings"])
            logger.debug("Embedded batch %d-%d", i, i + len(batch))

    return embeddings
