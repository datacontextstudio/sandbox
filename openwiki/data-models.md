# Data Models

## Overview

This document describes the main data structures used throughout DataContext Studio: request/response schemas, database tables, and task queue keys.

---

## API Models (Pydantic)

**Source**: `/services/api/api/models.py`

### Ingestion Models

#### JobStatus

```python
class JobStatus(str, Enum):
    pending = "pending"          # Job queued, waiting to be processed
    processing = "processing"    # Worker is actively processing
    completed = "completed"      # Successfully indexed
    failed = "failed"            # Failed after max retries, in dead-letter queue
```

**Usage**: Status field in IngestJob and IngestResponse

---

#### IngestJob

```python
class IngestJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str
    collection_name: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**Fields**:
- `job_id`: UUID string, unique identifier
- `file_path`: Path where file was saved (e.g., `/data/documents/{job_id}/file.pdf`)
- `collection_name`: Qdrant collection to index into (default: "default")
- `metadata`: Custom key-value data (passed through to Qdrant payload)
- `submitted_at`: UTC timestamp when job was created

**Source**: Sent via `POST /ingest`, serialized to JSON and stored in Valkey

**Example**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_path": "/data/documents/550e8400-e29b-41d4-a716-446655440000/policy.pdf",
  "collection_name": "finance-docs",
  "metadata": {"source": "compliance", "version": "2024-01"},
  "submitted_at": "2024-01-01T10:00:00+00:00"
}
```

---

#### IngestResponse

```python
class IngestResponse(BaseModel):
    job_id: str
    status: JobStatus
    file_path: str
    collection_name: str
```

**Response** (HTTP 202 Accepted):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "file_path": "/data/documents/550e8400-e29b-41d4-a716-446655440000/policy.pdf",
  "collection_name": "finance-docs"
}
```

---

### Query Models

#### QueryRequest

```python
class QueryRequest(BaseModel):
    query: str
    collections: list[str] = Field(default_factory=lambda: ["default"])
    top_k: int = 5
    generate: bool = False
    llm_model: str = "llama3.1"
    include_results: bool = True
```

**Fields**:
- `query`: User's search query text
- `collections`: Which Qdrant collections to search (default: ["default"])
- `top_k`: Number of results to return (default: 5)
- `generate`: Whether to generate LLM answer (default: false)
- `llm_model`: Which Ollama model to use (default: "llama3.1")
- `include_results`: Whether to include chunks in response (default: true)

**Example**:
```json
{
  "query": "What is the refund policy?",
  "collections": ["default", "faq"],
  "top_k": 10,
  "generate": true,
  "llm_model": "llama3.1",
  "include_results": true
}
```

---

#### QueryResult

```python
class QueryResult(BaseModel):
    text: str
    score: float
    collection_name: str = ""
    file_path: str | None = None
    chunk_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Fields**:
- `text`: The chunk text from the document
- `score`: Cosine similarity score (0-1)
- `collection_name`: Which Qdrant collection this result came from
- `file_path`: Original document file path
- `chunk_index`: Index of this chunk within the document
- `metadata`: Custom metadata from ingestion

**Example**:
```json
{
  "text": "Refunds are processed within 5-7 business days to the original payment method.",
  "score": 0.92,
  "collection_name": "default",
  "file_path": "/data/documents/550e8400-e29b-41d4-a716-446655440000/policy.pdf",
  "chunk_index": 3,
  "metadata": {"source": "compliance"}
}
```

---

#### QueryResponse

```python
class QueryResponse(BaseModel):
    query: str
    results: list[QueryResult] | None = None
    answer: str | None = None
```

**Fields**:
- `query`: Echo of the request query
- `results`: List of chunks (null if `include_results=false`)
- `answer`: LLM-generated answer (null if `generate=false` or no results)

**Example** (with results and answer):
```json
{
  "query": "What is the refund policy?",
  "results": [
    {
      "text": "Refunds are processed within 5-7 business days...",
      "score": 0.92,
      "collection_name": "default",
      "file_path": "/data/documents/.../policy.pdf",
      "chunk_index": 3,
      "metadata": {}
    }
  ],
  "answer": "Refunds are typically processed within 5-7 business days to the original payment method."
}
```

**Example** (answer only):
```json
{
  "query": "What is the refund policy?",
  "results": null,
  "answer": "Refunds are typically processed within 5-7 business days to the original payment method."
}
```

---

### Job Status Models

#### JobStatusResponse

```python
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    fields: dict[str, str] = Field(default_factory=dict)
```

**Response** (from `GET /jobs/{job_id}`):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "fields": {
    "submitted_at": "2024-01-01T10:00:00+00:00",
    "updated_at": "2024-01-01T10:05:30+00:00",
    "file_path": "/data/documents/550e8400-e29b-41d4-a716-446655440000/policy.pdf",
    "collection_name": "default",
    "chunks_indexed": "152",
    "error": ""
  }
}
```

---

### Collection & Document Models

#### CollectionsResponse

```python
class CollectionsResponse(BaseModel):
    collections: list[str]
```

**Response** (from `GET /collections`):
```json
{
  "collections": ["default", "finance-docs", "support-guides"]
}
```

---

#### DocumentInfo

```python
class DocumentInfo(BaseModel):
    job_id: str
    file_path: str
    chunk_count: int
```

**Fields**:
- `job_id`: UUID of the ingestion job that indexed this document
- `file_path`: Path to the original file
- `chunk_count`: Number of chunks indexed (from completed job)

---

#### DocumentsResponse

```python
class DocumentsResponse(BaseModel):
    collection_name: str
    documents: list[DocumentInfo]
```

**Response** (from `GET /collections/{name}/documents`):
```json
{
  "collection_name": "default",
  "documents": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "file_path": "/data/documents/550e8400-e29b-41d4-a716-446655440000/policy.pdf",
      "chunk_count": 152
    },
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440001",
      "file_path": "/data/documents/550e8400-e29b-41d4-a716-446655440001/faq.docx",
      "chunk_count": 48
    }
  ]
}
```

---

### Delete Models

#### DeleteResponse

```python
class DeleteResponse(BaseModel):
    deleted: bool
    detail: str
```

**Response** (from `DELETE /collections/{name}` or `DELETE /collections/{name}/documents/{job_id}`):
```json
{
  "deleted": true,
  "detail": "Collection 'default' deleted"
}
```

---

### Chat Models

#### TitleRequest

```python
class TitleRequest(BaseModel):
    query: str
    llm_model: str = "llama3.1"
```

**Request** (from `POST /title`, generates a title for a chat session):
```json
{
  "query": "What is the refund policy?",
  "llm_model": "llama3.1"
}
```

---

#### TitleResponse

```python
class TitleResponse(BaseModel):
    title: str
```

**Response**:
```json
{
  "title": "Refund Policy Overview"
}
```

---

## Internal API Models (Chat History)

**Source**: `/services/internal-api/api/models.py`

### Session Model

```python
class SessionCreateRequest(BaseModel):
    collections: list[str]

class SessionResponse(BaseModel):
    id: str  # UUID
    collections: list[str]
    created_at: datetime
```

**Request** (POST `/internal-api/sessions`):
```json
{
  "collections": ["default", "finance-docs"]
}
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "collections": ["default", "finance-docs"],
  "created_at": "2024-01-01T10:00:00+00:00"
}
```

---

### Message Model

```python
class MessageCreateRequest(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class MessageResponse(BaseModel):
    id: str  # UUID
    session_id: str  # UUID
    role: str
    content: str
    created_at: datetime
```

**Request** (POST `/internal-api/sessions/{session_id}/messages`):
```json
{
  "role": "user",
  "content": "What is the refund policy?"
}
```

**Response**:
```json
{
  "id": "msg-uuid-1",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "user",
  "content": "What is the refund policy?",
  "created_at": "2024-01-01T10:00:05+00:00"
}
```

---

## Database Schema

**Source**: `/services/internal-api/api/database.py`

### chatbot_sessions

```sql
CREATE TABLE chatbot_sessions (
  id UUID PRIMARY KEY,
  collections TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Purpose**: Store chat session metadata

**Columns**:
- `id`: UUID primary key
- `collections`: Array of Qdrant collection names to search
- `created_at`: Timestamp when session was created

**Indexes**: (implicit on id)

**Example data**:
```
id                                   | collections      | created_at
-------------------------------------+------------------+----------------------------
550e8400-e29b-41d4-a716-446655440000 | {default}        | 2024-01-01 10:00:00+00
550e8400-e29b-41d4-a716-446655440001 | {default,finance} | 2024-01-01 11:00:00+00
```

---

### chat_messages

```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES chatbot_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Purpose**: Store all messages in a session

**Columns**:
- `id`: UUID primary key
- `session_id`: Foreign key to chatbot_sessions (cascade delete)
- `role`: "user" or "assistant"
- `content`: Message text
- `created_at`: Timestamp when message was created

**Indexes**: (implicit on id, implicit foreign key on session_id)

**Example data**:
```
id     | session_id                           | role      | content                | created_at
-------|--------------------------------------+-----------+------------------------|----------------------------
uuid-1 | 550e8400-e29b-41d4-a716-446655440000 | user      | What is the policy?    | 2024-01-01 10:00:05+00
uuid-2 | 550e8400-e29b-41d4-a716-446655440000 | assistant | Refunds are processed..| 2024-01-01 10:00:08+00
```

---

## Valkey (Task Queue) Schema

**Source**: `/services/api/api/services/queue.py`, `/services/worker/worker/consumer.py`

### Ingestion Queue

**Key**: `dcs:queue:ingestion`

**Type**: Redis List (FIFO)

**Content**: JSON-serialized `IngestJob` objects

**Example**:
```
LRANGE dcs:queue:ingestion 0 -1
1) "{\"job_id\":\"uuid1\",\"file_path\":\"/data/...\",\"collection_name\":\"default\",\"metadata\":{},\"submitted_at\":\"2024-01-01T10:00:00+00:00\"}"
2) "{\"job_id\":\"uuid2\",\"file_path\":\"/data/...\",\"collection_name\":\"finance\",\"metadata\":{},\"submitted_at\":\"2024-01-01T10:01:00+00:00\"}"
```

**Operations**:
- **Enqueue**: `RPUSH dcs:queue:ingestion <job_json>`
- **Dequeue**: `BLPOP dcs:queue:ingestion 5` (blocks 5 seconds)

---

### Job Status Hash

**Key**: `dcs:job:{job_id}`

**Type**: Redis Hash

**Fields**:
- `status`: "pending" | "processing" | "completed" | "failed"
- `submitted_at`: ISO8601 timestamp
- `updated_at`: ISO8601 timestamp
- `file_path`: Document path
- `collection_name`: Qdrant collection
- `chunks_indexed`: Integer (set when completed)
- `error`: Error message (set if failed)

**Example**:
```
HGETALL dcs:job:550e8400-e29b-41d4-a716-446655440000
 1) "status"
 2) "completed"
 3) "submitted_at"
 4) "2024-01-01T10:00:00+00:00"
 5) "updated_at"
 6) "2024-01-01T10:05:30+00:00"
 7) "file_path"
 8) "/data/documents/550e8400-e29b-41d4-a716-446655440000/policy.pdf"
 9) "collection_name"
10) "default"
11) "chunks_indexed"
12) "152"
13) "error"
14) ""
```

**Operations**:
- **Create**: `HSET dcs:job:{id} status pending submitted_at <timestamp>`
- **Update**: `HSET dcs:job:{id} status processing`
- **Retrieve**: `HGETALL dcs:job:{id}`

---

### Dead-Letter Queue

**Key**: `dcs:dlq:ingestion`

**Type**: Redis List

**Content**: JSON-serialized `IngestJob` objects (jobs that failed after max retries)

**Operations**:
- **Push failed job**: `RPUSH dcs:dlq:ingestion <job_json>`
- **Inspect**: `LRANGE dcs:dlq:ingestion 0 -1`

**Manual recovery**:
```bash
# Move first job from DLQ back to main queue for retry
docker-compose exec valkey valkey-cli \
  RPUSH dcs:queue:ingestion "$(docker-compose exec valkey valkey-cli LPOP dcs:dlq:ingestion)"
```

---

## Qdrant Payload Structure

**Source**: `/services/worker/worker/indexer.py`

Each chunk is stored in Qdrant as a point with metadata payload.

### Point

**Point ID**: Deterministic SHA256 hash of `{file_path}:{chunk_index}`

```python
import hashlib
point_id = int(hashlib.sha256(f"{file_path}:{chunk_index}".encode()).hexdigest(), 16)
point_id = point_id % (2**63 - 1)
```

**Vector**: 384-dimensional embedding (from `nomic-embed-text`)

**Payload**:
```python
{
  "text": str,              # The chunk text
  "file_path": str,         # Original document path
  "chunk_index": int,       # 0-indexed chunk number
  "job_id": str,            # UUID of ingestion job
  "collection_name": str,   # Qdrant collection name
  "metadata": dict          # Custom metadata from ingest form
}
```

**Example**:
```json
{
  "text": "Refunds are processed within 5-7 business days to the original payment method.",
  "file_path": "/data/documents/550e8400-e29b-41d4-a716-446655440000/policy.pdf",
  "chunk_index": 3,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "collection_name": "default",
  "metadata": {"source": "compliance", "version": "2024-01"}
}
```

---

## Configuration Models

### Pydantic Settings (API)

**Source**: `/services/api/api/config.py`

```python
class Settings(BaseSettings):
    ollama_base_url: str
    qdrant_host: str
    qdrant_port: int
    valkey_url: str
    storage_path: str
```

**Environment variables** (from `.env`):
```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
QDRANT_HOST=qdrant
QDRANT_PORT=6333
VALKEY_URL=redis://valkey:6379
STORAGE_PATH=/data/documents
```

---

### Pydantic Settings (Worker)

**Source**: `/services/worker/worker/config.py`

```python
class Settings(BaseSettings):
    embed_model: str = "nomic-embed-text"
    chunk_size: int = 512
    chunk_overlap: int = 64
    embed_batch_size: int = 32
    max_retries: int = 3
    qdrant_host: str
    qdrant_port: int
    valkey_url: str
    ollama_base_url: str
```

**Environment variables** (from `.env` or defaults):
```env
EMBED_MODEL=nomic-embed-text
CHUNK_SIZE=512
CHUNK_OVERLAP=64
EMBED_BATCH_SIZE=32
MAX_RETRIES=3
QDRANT_HOST=qdrant
QDRANT_PORT=6333
VALKEY_URL=redis://valkey:6379
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

### Pydantic Settings (Internal API)

**Source**: `/services/internal-api/api/config.py`

```python
class Settings(BaseSettings):
    database_url: str
```

**Environment variable**:
```env
DATABASE_URL=postgresql+asyncpg://dcs:dcs_password@postgres:5432/datacontext
```

---

## Type Aliases

### UUID

All IDs (`job_id`, `session_id`, `message_id`) are **UUID strings**, generated as:

```python
import uuid
id_string = str(uuid.uuid4())  # e.g., "550e8400-e29b-41d4-a716-446655440000"
```

### Timestamp

All timestamps are **ISO8601 strings** in UTC:

```python
from datetime import datetime, timezone
ts = datetime.now(timezone.utc).isoformat()  # e.g., "2024-01-01T10:00:00+00:00"
```

### Collection Name

A **collection name** is a string identifier for a Qdrant collection (e.g., "default", "finance-docs").

- Alphanumeric characters, hyphens, underscores
- Length: 1-255 characters
- Case-sensitive

---

## Source References

- API models: `/services/api/api/models.py`
- Internal API models: `/services/internal-api/api/models.py`
- Database schema: `/services/internal-api/api/database.py`
- Queue operations: `/services/api/api/services/queue.py`
- Indexer: `/services/worker/worker/indexer.py`
- Config files: `/services/api/api/config.py`, `/services/worker/worker/config.py`, `/services/internal-api/api/config.py`
