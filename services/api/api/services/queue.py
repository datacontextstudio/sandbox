from datetime import datetime, timezone

import redis.asyncio as aioredis

from api.config import settings
from api.models import IngestJob, JobStatus

QUEUE_KEY = "dcs:queue:ingestion"


def _job_key(job_id: str) -> str:
    return f"dcs:job:{job_id}"


async def enqueue(job: IngestJob) -> None:
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        now = datetime.now(timezone.utc).isoformat()
        await r.hset(
            _job_key(job.job_id),
            mapping={
                "status": JobStatus.pending.value,
                "submitted_at": now,
                "updated_at": now,
                "file_path": job.file_path,
                "collection_name": job.collection_name,
            },
        )
        await r.rpush(QUEUE_KEY, job.model_dump_json())
    finally:
        await r.aclose()


async def get_job_fields(job_id: str) -> dict[str, str] | None:
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        fields = await r.hgetall(_job_key(job_id))
        return fields if fields else None
    finally:
        await r.aclose()


async def delete_job(job_id: str) -> None:
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.delete(_job_key(job_id))
    finally:
        await r.aclose()
