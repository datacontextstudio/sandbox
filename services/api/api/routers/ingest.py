import json
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile

from api.models import IngestJob, IngestResponse, JobStatus
from api.services import queue, storage

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest(
    file: UploadFile,
    collection_name: Annotated[str, Form()] = "default",
    metadata: Annotated[str | None, Form()] = None,
) -> IngestResponse:
    extra: dict = {}
    if metadata:
        try:
            extra = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="metadata must be valid JSON")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    job = IngestJob(
        file_path="",  # filled in after saving
        collection_name=collection_name,
        metadata=extra,
    )

    file_path = await storage.save_upload(job.job_id, file.filename or "upload", data)
    job.file_path = file_path

    await queue.enqueue(job)

    return IngestResponse(
        job_id=job.job_id,
        status=JobStatus.pending,
        file_path=file_path,
        collection_name=collection_name,
    )
