from fastapi import APIRouter, HTTPException

from api.models import JobStatusResponse
from api.services import queue

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    fields = await queue.get_job_fields(job_id)
    if fields is None:
        raise HTTPException(status_code=404, detail="Job not found")
    status = fields.pop("status", "unknown")
    return JobStatusResponse(job_id=job_id, status=status, fields=fields)
