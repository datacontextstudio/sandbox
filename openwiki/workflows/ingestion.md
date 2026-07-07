# Ingestion Workflow

## Overview

The ingestion pipeline processes uploaded documents asynchronously:

1. User uploads a file → API stores it and enqueues an ingestion job
2. Background worker polls the job queue, dequeues the job
3. Worker executes the pipeline: parse → chunk → embed → index
4. Worker updates job status (completed or failed)
5. User polls job status to monitor progress

---

## Step-by-Step Flow

### 1. File Upload (API)

**Endpoint**: `POST /ingest`

**Request**:
```
Content-Type: multipart/form-data
- file: (binary file: PDF, DOCX, PPTX, etc.)
- collection_name: (optional, default="default")
- metadata: (optional JSON string, e.g., '{"source":"sales-docs"}')
```

**Handler**: `/services/api/api/routers/ingest.py`

**Actions**:
1. Parse form data (file, collection_name, metadata)
2. Read file bytes
3. Create `IngestJob` object:
   - `job_id` = UUID
   - `file_path` = (empty, will be filled after save)
   - `collection_name` = provided or "default"
   - `metadata` = parsed JSON or empty dict
   - `submitted_at` = current UTC time
4. Call `storage.save_upload(job_id, filename, data)`:
   - Creates directory `/data/documents/{job_id}/`
   - Saves file as `/data/documents/{job_id}/{filename}`
   - Returns file_path
5. Update `job.file_path` with saved path
6. Call `queue.enqueue(job)`:
   - Serialize job to JSON
   - RPUSH to `dcs:queue:ingestion` list (Valkey)
   - Create hash `dcs:job:{job_id}` with fields: `status=pending`, `submitted_at`, `file_path`, `collection_name`
7. Return `202 Accepted` with job details:
   ```json
   {
     "job_id": "uuid-string",
     "status": "pending",
     "file_path": "/data/documents/{job_id}/{filename}",
     "collection_name": "default"
   }
   ```

**Source**: `/services/api/api/routers/ingest.py`, `/services/api/api/services/storage.py`, `/services/api/api/services/queue.py`

---

### 2. Job Queue (Valkey)

**Queue Key**: `dcs:queue:ingestion` (Valkey list, FIFO)

**Job State Hash**: `dcs:job:{job_id}` (Valkey hash, stores all job metadata)

**Fields in job hash**:
- `status` = `pending` | `processing` | `completed` | `failed`
- `submitted_at` = ISO8601 timestamp
- `updated_at` = ISO8601 timestamp (updated by worker)
- `file_path` = `/data/documents/{job_id}/{filename}`
- `collection_name` = collection name
- `chunks_indexed` = number of chunks successfully indexed (set after completion)
- `error` = error message (set if status=failed)

**Dead-Letter Queue**: `dcs:dlq:ingestion` (Valkey list, jobs that failed after max retries)

**Source**: `/services/api/api/services/queue.py`, `/services/worker/worker/consumer.py`

---

### 3. Worker Consumer Loop

**Entry**: `/services/worker/worker/main.py`

**Main Loop** (`consumer.py`):

```python
while True:
    # BLPOP: block until a job is available (5s timeout)
    job_json = BLPOP("dcs:queue:ingestion", timeout=5)
    
    if not job_json:
        # Timeout, loop again
        continue
    
    job = IngestJob.model_validate_json(job_json)
    
    try:
        # Update status to "processing"
        update_job_status(job.job_id, status="processing")
        
        # Run the pipeline
        chunks_indexed = process(job)
        
        # Update status to "completed"
        update_job_status(
            job.job_id,
            status="completed",
            chunks_indexed=chunks_indexed
        )
    except Exception as e:
        # Retry logic (up to MAX_RETRIES times)
        if retries_exceeded:
            # Push to dead-letter queue
            RPUSH("dcs:dlq:ingestion", job_json)
            # Update status to "failed"
            update_job_status(job.job_id, status="failed", error=str(e))
        else:
            # Re-enqueue for retry
            RPUSH("dcs:queue:ingestion", job_json)
```

**Configuration**:
- `MAX_RETRIES` = 3 (set in `/services/worker/worker/config.py`)

**Source**: `/services/worker/worker/consumer.py`, `/services/worker/worker/main.py`

---

### 4. Pipeline: Parse → Chunk → Embed → Index

**Entry**: `/services/worker/worker/pipeline.py`

#### 4.1 Parse (Docling)

**Function**: `parse_document(file_path: str) -> str`

**Handler**: `/services/worker/worker/parser.py`

**Actions**:
1. Use Docling library to convert document to markdown
2. Supported formats: PDF, DOCX, PPTX, HTML, RTF, and more
3. Includes OCR via Tesseract for image-heavy PDFs
4. Returns markdown text (or empty string if parsing fails)

**Output**: Full markdown text (may be very long, 100KB+)

**Source**: `/services/worker/worker/parser.py`

---

#### 4.2 Chunk (Recursive Split)

**Function**: `recursive_split(text: str) -> List[str]`

**Handler**: `/services/worker/worker/chunker.py`

**Strategy**: Recursive character splitting

**Algorithm**:
1. Split by `\n\n` (paragraph breaks)
2. For each chunk > `CHUNK_SIZE`:
   - Split by `\n` (line breaks)
3. For each chunk > `CHUNK_SIZE`:
   - Split by `. ` (sentence ends)
4. For each chunk > `CHUNK_SIZE`:
   - Split by ` ` (spaces)
5. For each chunk > `CHUNK_SIZE`:
   - Split by single character

**Configuration**:
- `CHUNK_SIZE` = 512 characters (default)
- `CHUNK_OVERLAP` = 64 characters (overlap between consecutive chunks)

**Example**:
```
Input: "This is a long document about finance. It covers many topics..."
Output: [
  "This is a long document about finance. It covers",  # chunk 0
  "covers many topics...",                              # chunk 1 (overlaps with chunk 0)
  ...
]
```

**Output**: List of text chunks (each ~512 chars with 64-char overlap)

**Source**: `/services/worker/worker/chunker.py`

---

#### 4.3 Embed (Ollama)

**Function**: `embed_chunks(chunks: List[str]) -> List[List[float]]`

**Handler**: `/services/worker/worker/embedder.py`

**Process**:
1. Batch chunks (batch size = 32)
2. For each batch, POST to Ollama `/api/embed` endpoint:
   ```json
   {
     "model": "nomic-embed-text",
     "input": ["chunk1", "chunk2", ..., "chunk32"]
   }
   ```
3. Response contains embeddings (384-dimensional vectors)
4. Return list of embeddings (same order as chunks)

**Configuration**:
- `EMBED_MODEL` = `nomic-embed-text` (384 dimensions)
- `EMBED_BATCH_SIZE` = 32
- `OLLAMA_BASE_URL` = `http://host.docker.internal:11434` (from `.env`)

**Output**: List of embedding vectors (one per chunk)

**Source**: `/services/worker/worker/embedder.py`

---

#### 4.4 Index (Qdrant)

**Function**: `upsert_chunks(collection_name, chunks, embeddings, job_id, file_path, metadata) -> int`

**Handler**: `/services/worker/worker/indexer.py`

**Process**:
1. Create or get Qdrant collection (if doesn't exist):
   - Collection name = provided (e.g., "default")
   - Vector size = 384 (matching `nomic-embed-text`)
   - Distance metric = Cosine
2. For each chunk, create a point:
   - **Point ID** = deterministic SHA256 hash: `SHA256(f"{file_path}:{chunk_index}")`
   - **Vector** = embedding from step 4.3
   - **Payload** (metadata):
     - `text` = chunk text
     - `file_path` = original file path
     - `chunk_index` = chunk number
     - `job_id` = ingestion job ID
     - `collection_name` = collection name
     - `metadata` = custom metadata from upload form
3. Batch upsert all points to Qdrant
4. Return count of successfully indexed chunks

**Deterministic ID Logic**:
```python
import hashlib
point_id = int(hashlib.sha256(f"{file_path}:{chunk_index}".encode()).hexdigest(), 16)
# Qdrant expects positive integers, so we mod by a large number
point_id = point_id % (2**63 - 1)
```

**Benefits**: Re-uploading the same file produces the same point IDs, allowing updates/deduplication.

**Output**: Integer count of chunks indexed

**Source**: `/services/worker/worker/indexer.py`

---

### 5. Job Status Update

After pipeline completes (or fails), worker updates the job hash in Valkey:

**Success**:
```
dcs:job:{job_id}
├─ status = "completed"
├─ updated_at = ISO8601 now
└─ chunks_indexed = {count}
```

**Failure**:
```
dcs:job:{job_id}
├─ status = "failed"
├─ updated_at = ISO8601 now
└─ error = "error message here"
```

**Source**: `/services/worker/worker/consumer.py`

---

### 6. Status Polling (User/Frontend)

**Endpoint**: `GET /jobs/{job_id}`

**Handler**: `/services/api/api/routers/jobs.py`

**Process**:
1. Fetch hash `dcs:job:{job_id}` from Valkey
2. Return all fields as JSON:
   ```json
   {
     "job_id": "uuid",
     "status": "pending|processing|completed|failed",
     "fields": {
       "submitted_at": "2024-01-01T10:00:00Z",
       "updated_at": "2024-01-01T10:05:00Z",
       "file_path": "/data/documents/{job_id}/file.pdf",
       "collection_name": "default",
       "chunks_indexed": "150",
       "error": ""
     }
   }
   ```

**Frontend** (e.g., `/services/web/src/routes/upload/+page.svelte`):
- After upload receives 202 + job_id, start polling
- Poll `GET /jobs/{job_id}` every 1-2 seconds
- Display status & progress
- Stop polling when status = "completed" or "failed"

**Source**: `/services/api/api/routers/jobs.py`, `/services/web/src/routes/upload/`

---

## Error Handling

### Retry Logic

If a job fails (exception in pipeline):

1. **Check retry count** (stored implicitly by dequeue attempts)
2. **If retries < MAX_RETRIES**:
   - Re-enqueue job: RPUSH back to `dcs:queue:ingestion`
   - Worker will retry on next dequeue
3. **If retries >= MAX_RETRIES**:
   - Push to dead-letter queue: RPUSH to `dcs:dlq:ingestion`
   - Set `status = "failed"`, `error = <exception message>`
   - Log the failure for manual inspection

**Configuration**: `MAX_RETRIES = 3` (in `/services/worker/worker/config.py`)

**Source**: `/services/worker/worker/consumer.py`

### Common Failures

1. **Parsing fails** (e.g., corrupted PDF)
   - Empty text returned from Docling
   - Logger warns "Document produced no text, skipping"
   - Status: `completed` with `chunks_indexed = 0`

2. **Embedding fails** (e.g., Ollama offline)
   - Exception in embedder
   - Job retried up to MAX_RETRIES
   - If all retries fail: moved to DLQ, status `failed`

3. **Indexing fails** (e.g., Qdrant offline)
   - Exception in indexer
   - Job retried up to MAX_RETRIES
   - If all retries fail: moved to DLQ, status `failed`

---

## Performance Considerations

### Chunk Size & Overlap

- **CHUNK_SIZE = 512 chars**: Balance between context window and retrieval precision
- **CHUNK_OVERLAP = 64 chars**: Small overlap to maintain semantic boundaries
- **Tuning**: Modify in `.env` or `/services/worker/worker/config.py`

### Embedding Batch Size

- **EMBED_BATCH_SIZE = 32**: Balance between throughput and memory
- **Tuning**: Modify in `/services/worker/worker/config.py`
- **Larger batches** = faster but uses more GPU/CPU memory
- **Smaller batches** = slower but lower memory footprint

### Deterministic Point IDs

- **Benefit**: Re-uploading same file with same chunks = same point IDs
- **Drawback**: If chunk boundaries change (e.g., different CHUNK_SIZE), old points won't be updated
- **Note**: Consider DELETE before re-ingest if chunk strategy changes

---

## Debugging & Monitoring

### View Queue Status

```bash
# Connect to Valkey container
docker-compose exec valkey valkey-cli

# Check pending jobs
LLEN dcs:queue:ingestion

# Check dead-letter queue
LLEN dcs:dlq:ingestion

# Inspect a specific job
HGETALL dcs:job:{job_id}

# View all keys
KEYS dcs:*
```

### View Logs

```bash
# Worker logs
docker-compose logs -f worker

# API logs
docker-compose logs -f api

# Full stack logs
docker-compose logs -f
```

### Common Issues

1. **Worker keeps crashing**
   - Check logs: `docker-compose logs worker`
   - Likely: Ollama not running, Qdrant offline, or missing dependencies
   - Fix: `docker-compose up worker` after dependencies are ready

2. **Jobs stuck in pending**
   - Worker may not be running
   - Check: `docker-compose ps` (should show worker as "Up")
   - Restart: `docker-compose restart worker`

3. **High failure rate**
   - Check DLQ: `docker-compose exec valkey valkey-cli LLEN dcs:dlq:ingestion`
   - Inspect failed job: `docker-compose exec valkey valkey-cli HGETALL dcs:job:{job_id}`
   - Common causes: Ollama offline, out of disk space, corrupted PDFs

---

## Source References

- Pipeline orchestration: `/services/worker/worker/pipeline.py`
- Consumer loop: `/services/worker/worker/consumer.py`
- Document parser: `/services/worker/worker/parser.py`
- Chunker: `/services/worker/worker/chunker.py`
- Embedder: `/services/worker/worker/embedder.py`
- Indexer: `/services/worker/worker/indexer.py`
- Ingest endpoint: `/services/api/api/routers/ingest.py`
- Jobs status endpoint: `/services/api/api/routers/jobs.py`
- Queue operations: `/services/api/api/services/queue.py`
- Storage operations: `/services/api/api/services/storage.py`
