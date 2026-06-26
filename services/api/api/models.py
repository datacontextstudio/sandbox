from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class IngestJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str
    collection_name: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IngestResponse(BaseModel):
    job_id: str
    status: JobStatus
    file_path: str
    collection_name: str


class QueryRequest(BaseModel):
    query: str
    collections: list[str] = Field(default_factory=lambda: ["default"])
    top_k: int = 5
    generate: bool = False
    llm_model: str = "llama3"


class QueryResult(BaseModel):
    text: str
    score: float
    collection_name: str = ""
    file_path: str | None = None
    chunk_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    query: str
    results: list[QueryResult]
    answer: str | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    fields: dict[str, str] = Field(default_factory=dict)
