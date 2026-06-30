import json
import logging
from datetime import datetime, timezone

import redis as redis_lib
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from worker import pipeline
from worker.config import settings
from worker.models import IngestJob, JobStatus

logger = logging.getLogger(__name__)

QUEUE_KEY = "dcs:queue:ingestion"
DLQ_KEY = "dcs:dlq:ingestion"
BLPOP_TIMEOUT = 5


def _job_key(job_id: str) -> str:
    return f"dcs:job:{job_id}"


def _set_status(r: redis_lib.Redis, job_id: str, status: JobStatus, **extra: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    r.hset(
        _job_key(job_id),
        mapping={"status": status.value, "updated_at": now, **extra},
    )


@retry(
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _process_with_retries(job: IngestJob) -> int:
    return pipeline.process(job)


def _handle_message(r: redis_lib.Redis, raw: bytes) -> None:
    try:
        job = IngestJob.model_validate_json(raw)
    except Exception as exc:
        logger.error("Invalid job payload: %s — %s", raw[:200], exc)
        return

    _set_status(r, job.job_id, JobStatus.processing, created_at=datetime.now(timezone.utc).isoformat())

    try:
        count = _process_with_retries(job)
        _set_status(r, job.job_id, JobStatus.completed, chunks_indexed=str(count))
    except Exception as exc:
        logger.error("[%s] Job failed after retries: %s", job.job_id, exc)
        _set_status(r, job.job_id, JobStatus.failed, error=str(exc))
        r.rpush(DLQ_KEY, raw)


def run(stop_event=None) -> None:
    r = redis_lib.from_url(
        settings.valkey_url,
        decode_responses=False,
        socket_timeout=BLPOP_TIMEOUT + 1,
        socket_connect_timeout=5,
    )
    logger.info("Worker listening on %s", QUEUE_KEY)

    while stop_event is None or not stop_event.is_set():
        result = r.blpop(QUEUE_KEY, timeout=BLPOP_TIMEOUT)
        if result is None:
            continue
        _, raw = result
        _handle_message(r, raw)
