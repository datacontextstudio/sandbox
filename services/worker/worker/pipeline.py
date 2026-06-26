import logging

from worker.chunker import recursive_split
from worker.embedder import embed_chunks
from worker.indexer import upsert_chunks
from worker.models import IngestJob
from worker.parser import parse_document

logger = logging.getLogger(__name__)


def process(job: IngestJob) -> int:
    logger.info("[%s] Starting pipeline for %s", job.job_id, job.file_path)

    text = parse_document(job.file_path)
    if not text.strip():
        logger.warning("[%s] Document produced no text, skipping", job.job_id)
        return 0

    chunks = recursive_split(text)
    logger.info("[%s] Split into %d chunks", job.job_id, len(chunks))

    embeddings = embed_chunks(chunks)
    logger.info("[%s] Embedded %d chunks", job.job_id, len(embeddings))

    count = upsert_chunks(
        collection_name=job.collection_name,
        chunks=chunks,
        embeddings=embeddings,
        job_id=job.job_id,
        file_path=job.file_path,
        metadata=job.metadata,
    )

    logger.info("[%s] Indexed %d chunks into '%s'", job.job_id, count, job.collection_name)
    return count
