# Architecture

## Service Overview

DataContext Studio consists of five main services deployed via Docker Compose, plus Ollama running natively on the host:

```
┌─────────────────────────────────────────────────────────────┐
│ nginx (reverse proxy)                                        │
│ ├─ :3000 → web + api + internal-api                         │
│ ├─ :3001 → chat + api + internal-api                        │
│ └─ :8000 → api only                                         │
└────┬───────────┬───────────┬────────────┬────────────────────┘
     │           │           │            │
┌────▼──┐ ┌──────▼─────┐ ┌──▼──────┐ ┌──▼──────┐
│  web  │ │    chat    │ │   api   │ │internal-│
│       │ │            │ │         │ │  api    │
│SvelteKit SvelteKit FastAPI  FastAPI
│:5173  │ │ :5174      │ │ :8000   │ │ :8001   │
└────┬──┘ └────┬───────┘ └──┬─────┘ └──┬──────┘
     │         │            │          │
     │         └────┬────────┴──────────┘
     │              │
     │    ┌─────────┴────────┬──────────────┬──────────────┐
     │    │                  │              │              │
     │ ┌──▼──────┐   ┌──────▼────┐   ┌──────▼────┐   ┌────▼─────┐
     │ │ Ollama* │   │  Qdrant   │   │ PostgreSQL│   │ Valkey   │
     │ │ :11434  │   │  :6333    │   │ :5432     │   │ :6379    │
     │ │ (host)  │   │ (Docker)  │   │ (Docker)  │   │ (Docker) │
     └ └─────────┘   └───────────┘   └───────────┘   └──────────┘
           ^
     (host.docker.internal from containers)

* Ollama runs natively on macOS, not containerized
```

---

## Service Descriptions

### Nginx (Reverse Proxy)

- **Port**: 3000, 3001, 8000
- **Purpose**: Routes requests to frontend, API, and internal-api based on port and path
- **Config**: `/nginx/default.conf`
- **Networking**: Docker bridge network; reaches containers by hostname
- **Status**: Restarts unless stopped

#### Routing Logic

- **:3000** → web (SvelteKit) + api + internal-api (via path prefix `/api`, `/internal-api`)
- **:3001** → chat (SvelteKit) + api + internal-api (same path routing)
- **:8000** → api only (direct FastAPI, no HTML routing)

### web (SvelteKit Frontend)

- **Port**: 5173 (dev server inside container, exposed via nginx on :3000)
- **Purpose**: Document upload, search, collection management
- **Tech**: SvelteKit 5 + TypeScript + Tailwind CSS 4
- **API Client**: Calls `/api` and `/internal-api` endpoints
- **Routes**:
  - `/` → Home
  - `/upload/` → Document upload
  - `/query/` → Search/query interface
  - `/collections/` → Manage collections & documents
- **Source**: `/services/web/src/routes/`
- **Dev Setup**: Hot reload via Docker volume mount
- **Status**: Restarts unless stopped

### chat (SvelteKit Chat Frontend)

- **Port**: 5174 (dev server inside container, exposed via nginx on :3001)
- **Purpose**: LLM-powered chatbot with multi-turn history
- **Tech**: SvelteKit 5 + TypeScript + Tailwind CSS 4
- **API Clients**: Calls `/api/query` (main API) and `/internal-api/sessions/*` (chat history)
- **Routes**:
  - `/` → Home (session list or creation)
  - `/[session_id]/` → Active chat session
  - `/[session_id]/[chat_id]/` → Individual message view (if needed)
- **Session Model**: Each session stores `collections` (list of Qdrant collections to search) and message history
- **Source**: `/services/chat/src/routes/`
- **Dev Setup**: Hot reload via Docker volume mount
- **Status**: Restarts unless stopped

### api (FastAPI Backend)

- **Port**: 8000 (inside Docker; exposed via nginx on all three public ports)
- **Purpose**: Core RAG API—ingest documents, query vector DB, manage collections
- **Tech**: FastAPI + Python 3.14 + Uvicorn
- **Configuration**: `/services/api/api/config.py` (pydantic-settings)
- **Entry Point**: `/services/api/api/main.py`
- **Routers**:
  - `ingest.py` → `POST /ingest` (file upload + queue)
  - `query.py` → `POST /query` (semantic search + optional LLM)
  - `jobs.py` → `GET /jobs/{job_id}` (poll ingestion status)
  - `collections.py` → `GET /collections`, `DELETE /collections/{name}`
  - `documents.py` → `GET /collections/{name}/documents`, `DELETE /collections/{name}/documents/{job_id}`
  - `title.py` → `POST /title` (generate chat session title)
  - `healthz` → `GET /healthz` (health check)
- **Services** (dependency injection):
  - `queue.py` → Valkey client (enqueue/dequeue jobs)
  - `searcher.py` → Qdrant client (vector search)
  - `embedder.py` → Ollama client (text embedding)
  - `storage.py` → File storage (Docker volume)
- **Status**: Restarts unless stopped
- **Dependencies**: Qdrant, Valkey, Ollama (for embeddings during query)

### internal-api (FastAPI Chat History)

- **Port**: 8001 (inside Docker; exposed via nginx on ports 3000 & 3001 with path `/internal-api/`)
- **Purpose**: Persistent chat session & message storage (PostgreSQL)
- **Tech**: FastAPI + Python 3.14 + SQLAlchemy 2.0 + asyncpg
- **Configuration**: `/services/internal-api/api/config.py`
- **Entry Point**: `/services/internal-api/api/main.py` (includes lifespan hook to auto-create tables)
- **Routers**:
  - `sessions.py` → CRUD for chat sessions
  - `messages.py` → CRUD for chat messages
  - `chats.py` → Chat-specific endpoints
  - `healthz` → `GET /healthz`
- **Database**:
  - `chatbot_sessions` (id: UUID, collections: text[], created_at: timestamptz)
  - `chat_messages` (id: UUID, session_id: UUID FK, role: text, content: text, created_at: timestamptz)
- **Status**: Restarts unless stopped
- **Dependencies**: PostgreSQL

### worker (Ingestion Pipeline)

- **Purpose**: Background job consumer; processes document ingestion asynchronously
- **Tech**: Python 3.14 + Docling + Valkey consumer
- **Entry Point**: `/services/worker/worker/main.py`
- **Main Loop** (`consumer.py`):
  - Polls Valkey list `dcs:queue:ingestion` with BLPOP (5s timeout)
  - For each job: set status → `processing`, run pipeline, update status & chunks_indexed
  - On failure: push to `dcs:dlq:ingestion` dead-letter queue
- **Pipeline** (`pipeline.py`):
  1. **Parse** (`parser.py`): Docling + Tesseract OCR → markdown text
  2. **Chunk** (`chunker.py`): Recursive split (512 char chunks, 64 char overlap)
  3. **Embed** (`embedder.py`): Batch POST to Ollama (nomic-embed-text, batch size 32)
  4. **Index** (`indexer.py`): Upsert to Qdrant (deterministic SHA256 chunk IDs)
- **Warmup** (`warmup/download_models.py`): Pre-download Docling & Hugging Face models at Docker build
- **Status**: Restarts unless stopped
- **Dependencies**: Ollama (for embeddings), Qdrant (for indexing), Valkey (for job queue)

### Qdrant (Vector Database)

- **Image**: `qdrant/qdrant:latest`
- **Port**: 6333 (Docker internal + exposed to host for dashboard)
- **Purpose**: Store embeddings, enable fast semantic search
- **Model**: Cosine similarity, `nomic-embed-text` embeddings (384 dimensions)
- **Collections**: One per logical document group (e.g., "default", "finance-docs")
- **Chunk IDs**: Deterministic SHA256 hash of `{file_path}:{chunk_index}`
- **Volume**: `qdrant_data` (persistent storage)
- **Dashboard**: http://localhost:6333/dashboard (web UI for inspection)
- **Status**: Restarts unless stopped

### PostgreSQL

- **Image**: `postgres:16`
- **Port**: 5432 (Docker internal)
- **Purpose**: Persistent chat session and message storage
- **Database**: `datacontext`
- **User/Password**: `dcs` / `dcs_password` (from `.env`)
- **Tables** (auto-created on `internal-api` startup):
  - `chatbot_sessions`: UUID, collections (array of collection names), created_at
  - `chat_messages`: UUID, session_id (FK), role, content, created_at
- **Volume**: `postgres_data` (persistent storage)
- **Status**: Restarts unless stopped

### Valkey (Task Queue)

- **Image**: `valkey/valkey:8`
- **Port**: 6379 (Docker internal)
- **Purpose**: FIFO queue for document ingestion jobs
- **Key Schema**:
  - `dcs:queue:ingestion` → List (FIFO job queue)
  - `dcs:job:{job_id}` → Hash (job state: status, file_path, collection_name, chunks_indexed, error, etc.)
  - `dcs:dlq:ingestion` → List (dead-letter queue for failed jobs)
- **Connection URL**: `redis://valkey:6379` (or `VALKEY_URL` env var)
- **Status**: Restarts unless stopped

### Ollama (LLM + Embeddings)

- **Platform**: Native macOS (not containerized)
- **Port**: 11434
- **Purpose**: LLM inference (`llama3`) + text embeddings (`nomic-embed-text`)
- **Docker Access**: Containers reach via `host.docker.internal:11434`
- **Setup**:
  - Install: `brew install ollama`
  - Start: `brew services start ollama`
  - Models: `ollama pull llama3`, `ollama pull nomic-embed-text`
- **Endpoints**:
  - `POST /api/embed` (embedding service)
  - `POST /api/chat` (chat/inference service)
- **GPU**: Uses Metal GPU on Apple Silicon for acceleration
- **Status**: Controlled via `brew services` (not part of docker-compose)

---

## Networking & Communication

### Docker Bridge Network

All Docker containers share a single `bridge` network (created by docker-compose). Containers communicate by hostname:

- `web` → http://api:8000 (FastAPI backend)
- `chat` → http://api:8000 + http://internal-api:8001
- `api` → http://qdrant:6333, http://valkey:6379, http://ollama:11434
- `internal-api` → postgresql://postgres:5432
- `worker` → http://qdrant:6333, http://valkey:6379, http://ollama:11434
- `nginx` → http://web:5173, http://chat:5174, http://api:8000, http://internal-api:8001

### Host-to-Container

- **Ollama** (on macOS host) is unreachable by hostname from containers
- **Solution**: Docker's `host.docker.internal` special DNS name
- **Usage in containers**: `http://host.docker.internal:11434`
- **Configuration**: Set `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `.env`

### Public Ports (from host)

- **:3000** → nginx → web + api + internal-api
- **:3001** → nginx → chat + api + internal-api
- **:8000** → nginx → api only
- **:6333** → qdrant (exposed for dashboard)

---

## Data Flow Diagrams

### Ingestion Flow

```
User (Web App)
    │
    └─→ POST /ingest (upload file)
        │
        └─→ API (ingest.py)
            ├─ Save file to /data/documents (Docker volume)
            ├─ Create IngestJob (job_id, file_path, collection_name, metadata)
            ├─ Enqueue to dcs:queue:ingestion (Valkey)
            └─ Return 202 Accepted + job_id
                │
                └─→ Worker (consumer.py) polls Valkey
                    ├─ Dequeue job (BLPOP, 5s timeout)
                    ├─ Update status → processing
                    │
                    ├─ Pipeline (pipeline.py)
                    │  ├─ Parse (Docling) → markdown
                    │  ├─ Chunk (chunker) → 512-char chunks
                    │  ├─ Embed (Ollama /api/embed) → vectors
                    │  └─ Index (Qdrant upsert) → stored
                    │
                    └─ Update job status → completed (+ chunks_indexed)
                       or → failed (push to dlq)

User polls: GET /jobs/{job_id} (api/jobs.py)
    └─→ Fetch job state from dcs:job:{job_id} (Valkey hash)
        └─→ Return status, chunks_indexed, error (if any)
```

### Query Flow

```
User (Web App or API client)
    │
    └─→ POST /query
        │
        └─→ API (query.py)
            ├─ Embed query text (POST to Ollama /api/embed)
            │  └─→ Get 384-dim vector
            │
            ├─ Search collections (Qdrant cosine similarity, top-k=5)
            │  └─→ Get list of (text, score, file_path, chunk_index, metadata)
            │
            └─ If generate=true:
               ├─ Concatenate results as context
               ├─ Build prompt with system message + user query
               ├─ POST to Ollama /api/chat (llama3 model)
               │  └─→ Get LLM response
               └─ Return QueryResponse (results + answer)

Return: QueryResponse
    ├─ query: str
    ├─ results: List[QueryResult] or None
    │  └─ text, score, file_path, chunk_index, metadata
    └─ answer: str or None
```

### Chat Flow

```
User (Chat App)
    │
    ├─→ Create session: POST /internal-api/sessions
    │   └─→ Internal API (sessions.py)
    │       ├─ Generate session UUID
    │       ├─ Insert into chatbot_sessions (PostgreSQL)
    │       └─ Return session_id
    │
    ├─→ Send message
    │   │
    │   ├─→ Save user message: POST /internal-api/sessions/{id}/messages
    │   │   └─→ Insert into chat_messages (role=user, content)
    │   │
    │   ├─→ Get LLM answer: POST /api/query (with generate=true)
    │   │   └─→ (same as Query Flow above)
    │   │
    │   └─→ Save assistant message: POST /internal-api/sessions/{id}/messages
    │       └─→ Insert into chat_messages (role=assistant, content=LLM response)
    │
    └─→ Load history: GET /internal-api/sessions/{id}/messages
        └─→ Internal API (messages.py)
            ├─ Query chat_messages WHERE session_id={id}
            └─ Return list ordered by created_at
```

---

## Configuration & Environment Variables

Loaded from `.env` (via pydantic-settings) at service startup:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
QDRANT_HOST=qdrant
QDRANT_PORT=6333
VALKEY_URL=redis://valkey:6379
STORAGE_PATH=/data/documents

POSTGRES_DB=datacontext
POSTGRES_USER=dcs
POSTGRES_PASSWORD=dcs_password
DATABASE_URL=postgresql+asyncpg://dcs:dcs_password@postgres:5432/datacontext
```

**Worker-only defaults** (set in `/services/worker/worker/config.py`):

```python
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
EMBED_BATCH_SIZE = 32
MAX_RETRIES = 3
```

---

## Storage

### Docker Volumes

| Volume | Mounted in | Purpose |
| --- | --- | --- |
| `storage_data` | `/data/documents` (api, worker) | Raw uploaded documents |
| `qdrant_data` | `/qdrant/storage` (qdrant) | Vector embeddings & metadata |
| `postgres_data` | `/var/lib/postgresql/data` (postgres) | Chat history database |

### File Layout (in Docker container)

```
/data/documents/
├─ {job_id}/
│  ├─ original.pdf
│  ├─ original.docx
│  └─ ...
└─ ...
```

---

## Dependency Graph

```
nginx
├─ web
├─ chat
├─ api
│  ├─ qdrant
│  ├─ valkey
│  └─ (ollama via host.docker.internal)
└─ internal-api
   └─ postgres

worker
├─ qdrant
├─ valkey
└─ (ollama via host.docker.internal)

(All containers depend on docker-compose network)
```

---

## Production Architecture (Future)

For scaling to production, see `/architecture-vms.txt`. Key differences:

- **Separate GPU VMs**: vLLM (inference) + TEI (embeddings) on dedicated nodes
- **Load-balanced API**: Multiple API instances behind a reverse proxy
- **Qdrant Cluster**: Multi-node Qdrant with persistent disk
- **Valkey Cluster**: Distributed Valkey for high-volume job queues
- **Object Storage**: S3 or similar for document storage instead of local Docker volume
- **PostgreSQL HA**: Replication for chat history (optional)

---

## Common Issues & Diagnostics

### Ollama not reachable

**Symptom**: Query or ingest fails with "connection refused" to ollama.

**Cause**: Ollama service not running on macOS host.

**Fix**:
```bash
brew services start ollama
ollama pull llama3
ollama pull nomic-embed-text
```

### Worker not processing jobs

**Symptom**: Jobs stuck in `dcs:queue:ingestion`.

**Cause**: Worker container crashed or not running.

**Fix**:
```bash
docker-compose up worker
# Or check logs:
docker-compose logs worker
```

### Database migration/schema issues

**Symptom**: Chat endpoints return 500 errors related to PostgreSQL.

**Cause**: internal-api lifespan hook didn't create tables.

**Fix**:
```bash
docker-compose down
docker-compose up -d internal-api
# Wait for tables to be created, then restart:
docker-compose restart api
```

### Qdrant collection not found

**Symptom**: Query or ingest returns "collection not found".

**Cause**: Typo in collection name or collection doesn't exist yet.

**Fix**: Check collection name matches; ingest a document to that collection first.

---

## Source References

- Docker Compose config: `/docker-compose.yml`
- Nginx routing: `/nginx/default.conf`
- API entry: `/services/api/api/main.py`
- Worker entry: `/services/worker/worker/main.py`
- Internal API entry: `/services/internal-api/api/main.py`
- Architecture diagrams: `/architecture-local.txt`, `/architecture-vms.txt`
