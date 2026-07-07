# DataContext Studio — OpenWiki Quickstart

**DataContext Studio** is a self-hosted, open-source RAG (Retrieval-Augmented Generation) platform. Users upload documents, which are automatically parsed, chunked, embedded, and indexed into a vector database. They can then run semantic searches and get LLM-generated answers — all running on personal infrastructure.

**Status**: Functional local development stack with Docker Compose orchestration.  
**License**: MIT 2026  
**Repository**: https://github.com/datacontextstudio/sandbox

---

## Table of Contents

1. [Quick Overview](#quick-overview)
2. [Architecture at a Glance](#architecture-at-a-glance)
3. [Tech Stack](#tech-stack)
4. [Getting Started Locally](#getting-started-locally)
5. [Key Workflows](#key-workflows)
6. [Documentation Map](#documentation-map)
7. [Important Files](#important-files)

---

## Quick Overview

DataContext Studio provides three main user-facing interfaces:

1. **Web App** (`localhost:3000`) — Document upload & search interface
2. **Chat App** (`localhost:3001`) — LLM-powered chatbot with chat history
3. **API** (`localhost:8000` or via nginx on `:3000`/`:3001`) — REST endpoints for programmatic access

**Core workflow:**
1. Upload a document (PDF, DOCX, PPTX, etc.) to the Web App or via `/ingest` API
2. The document is parsed, chunked, embedded, and indexed by a background worker
3. Query the vector database for semantic search, optionally generating LLM answers
4. Chat App stores conversation history in PostgreSQL

---

## Architecture at a Glance

```
┌─ Docker Compose (local MacBook dev) ──────────────────────────────────────┐
│                                                                             │
│  Public Layer (nginx)                                                       │
│  ├─ :3000 → web (SvelteKit) + api (FastAPI) + internal-api                 │
│  ├─ :3001 → chat (SvelteKit) + api + internal-api                          │
│  └─ :8000 → api only (direct FastAPI)                                      │
│                                                                             │
│  Frontend Layer                      Backend Layer                          │
│  ├─ web (SvelteKit :5173)   ┌────────┤ api (FastAPI :8000)                 │
│  └─ chat (SvelteKit :5174)  │        ├── Query & Ingest endpoints          │
│                             │        ├── Collections & Document management  │
│                             │        └── Title generation                  │
│                             │                                              │
│                             │        internal-api (FastAPI :8001)         │
│                             └────────├── Chat session storage               │
│                                      └── Message history (PostgreSQL)      │
│                                                                             │
│  Ingestion Pipeline                  Data Layer                            │
│  worker (container)          ┌──────────┤ qdrant :6333 (vector DB)        │
│  ├─ Parse (Docling)          │          ├── Collections with embeddings     │
│  ├─ Chunk                    │          └── Cosine similarity search       │
│  ├─ Embed (→ Ollama)         │                                            │
│  └─ Index (→ Qdrant)         │        ollama :11434 (macOS host)          │
│  valkey :6379 (job queue)    │        ├── llama3 (LLM inference)          │
│  storage_data volume         │        └── nomic-embed-text (embeddings)   │
│                              │                                            │
│                              └──────────┤ postgres :5432 (chat history)   │
│                                         └── Sessions & messages           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key design points:**
- **Ollama runs natively on the macOS host** (not containerized) for GPU acceleration via Metal
- **Containers reach Ollama via** `host.docker.internal:11434`
- **All Docker services share a single bridge network**
- **Valkey** (FIFO list) queues ingestion jobs; worker polls with BLPOP
- **PostgreSQL** stores chat sessions and message history; auto-created at startup
- **Qdrant** runs in a Docker container but is also exposed on `:6333` for the web dashboard

For production architecture (multi-VM with separate GPU nodes, load-balanced API, Qdrant cluster), see `/architecture-vms.txt`.

---

## Tech Stack

| Component        | Technology                                                               |
| ---------------- | ---------------------------------------------------------------------- |
| **Frontend**     | SvelteKit 5 + TypeScript + Tailwind CSS 4                               |
| **Chat Frontend**| SvelteKit 5 + TypeScript + Tailwind CSS 4 (`services/chat`)            |
| **API**          | FastAPI + Python 3.14 + Uvicorn                                         |
| **Internal API** | FastAPI + Python 3.14 + Uvicorn + SQLAlchemy 2.0 + asyncpg            |
| **Worker**       | Python 3.14 + Docling (document parsing)                                |
| **Document Parse** | [Docling](https://github.com/DS4SD/docling) (PDF, DOCX, PPTX, etc.)    |
| **LLM & Embed**  | [Ollama](https://ollama.com/) (native on macOS host)                    |
| **Vector DB**    | [Qdrant](https://qdrant.tech/) (cosine similarity, `nomic-embed-text`)  |
| **Relational DB**| PostgreSQL 16 (chat sessions & message history)                         |
| **Task Queue**   | [Valkey](https://valkey.io/) (FIFO list + job state hashes)             |
| **Reverse Proxy**| Nginx                                                                    |
| **Container**    | Docker + Docker Compose                                                  |

---

## Getting Started Locally

### Prerequisites

- Docker Desktop
- Homebrew (for Ollama installation)
- macOS (current setup is optimized for local dev on Mac)

### Quickstart (One Command)

```bash
git clone https://github.com/datacontextstudio/sandbox.git
cd sandbox
make start
```

`make start` performs the full first-time setup:
- Copies `.env.example` to `.env`
- Installs Ollama via Homebrew
- Pulls the required models (`llama3`, `nomic-embed-text`)
- Builds Docker images
- Starts the stack

> ⏱️ **First run:** Up to 30 minutes (Docker compiles Docling, PyTorch, and dependencies). Subsequent starts are fast.

### Make Targets

| Target | What it does |
| --- | --- |
| `make install` | Install Homebrew dependencies (`brew bundle`) |
| `make env` | Copy `.env.example` to `.env` (skips if `.env` exists) |
| `make ollama-start` | Start Ollama as a macOS background service |
| `make ollama-models` | Pull `llama3` and `nomic-embed-text` |
| `make setup` | Run `env` → `install` → `ollama-start` → `ollama-models` |
| `make build` | Build Docker images (`docker-compose build`) |
| `make up` | Start the stack in the background (`docker-compose up -d`) |
| `make down` | Stop and remove containers (`docker-compose down`) |
| `make logs` | Tail container logs (`docker-compose logs -f`) |
| `make restart` | `down` then `up` |
| `make start` | Full first-time setup: `setup` → `build` → `up` |

### Manual Setup (if not using `make start`)

```bash
# 1. Configure environment
make env

# 2. Start Ollama (native on macOS)
make install
make ollama-start
make ollama-models

# 3. Build and run Docker stack
make build
make up

# 4. Watch logs
make logs
```

### Verify It's Working

Once the stack is running:

- **Web app**: http://localhost:3000 (upload documents, run queries)
- **Chat app**: http://localhost:3001 (chatbot with history)
- **API (direct)**: http://localhost:8000 (REST endpoints)
- **Qdrant Dashboard**: http://localhost:6333/dashboard (vector DB admin)
- **Health check**: `curl http://localhost:8000/healthz` → `{"status":"ok"}`

### Stopping the Stack

```bash
make down
```

To stop Ollama:

```bash
brew services stop ollama
```

---

## Key Workflows

### 1. Document Ingestion

**User action**: Upload a PDF, DOCX, or PPTX via the Web App or API.

**Flow**:
1. **API** receives upload at `POST /ingest`
2. Saves file to `/data/documents` (Docker volume)
3. Enqueues `IngestJob` JSON to `dcs:queue:ingestion` (Valkey)
4. Returns `202 Accepted` with `job_id`
5. **Worker** (background) dequeues job via BLPOP (5s timeout)
6. **Pipeline**:
   - Parse (Docling + OCR) → markdown text
   - Chunk (recursive split: `\n\n` → `\n` → `. ` → space → char) → 512-char chunks with 64-char overlap
   - Embed (batch POST to Ollama `/api/embed`, `nomic-embed-text`, batch size 32)
   - Index (upsert to Qdrant, deterministic SHA256 chunk IDs from `file_path:chunk_index`)
7. Updates job status in Valkey:
   - Success: `status=completed`, `chunks_indexed=N`
   - Failure: `status=failed`, error message; job moves to `dcs:dlq:ingestion` dead-letter queue
8. **Polling**: UI calls `GET /jobs/{job_id}` to monitor status

**Source**: See [Ingestion Workflows](./workflows/ingestion.md)

### 2. Semantic Query + LLM Answer

**User action**: Enter a query on the Web App or call `POST /query`.

**Flow**:
1. **API** receives query
2. Embeds the query text (POST to Ollama `/api/embed`) → 384-dim vector
3. Searches all requested Qdrant collections (cosine similarity, top-k results, default top-k=5)
4. Returns `QueryResponse`:
   - `results`: list of chunks (text, score, file_path, chunk_index)
   - `answer`: None (unless `generate=true`)
5. If `generate=true`:
   - Concatenates top results as context
   - Builds prompt with system message (guiding the LLM to answer concisely)
   - POSTs to Ollama `/api/chat` with `llama3` model
   - Returns LLM-generated answer

**Source**: See [Query Workflows](./workflows/query.md)

### 3. Chat with History

**User action**: Open Chat App, start a conversation.

**Flow**:
1. Chat UI creates a session: `POST /internal-api/sessions` (body: `collections: ["default"]`)
2. User sends a message → saved as `role=user` via `POST /internal-api/sessions/{id}/messages`
3. Chat UI calls `POST /api/query` with `generate=true` to get LLM answer
4. LLM response saved as `role=assistant` via `POST /internal-api/sessions/{id}/messages`
5. UI fetches full message history: `GET /internal-api/sessions/{id}/messages` (ordered by created_at)
6. UI re-renders with new messages

**Storage**: PostgreSQL `chatbot_sessions` and `chat_messages` tables (auto-created at internal-api startup)

**Source**: See [Chat Workflows](./workflows/chat.md)

---

## Documentation Map

| Document | Purpose |
| --- | --- |
| **[Ingestion Workflows](./workflows/ingestion.md)** | Deep dive into document upload, parsing, chunking, embedding, and indexing |
| **[Query Workflows](./workflows/query.md)** | Semantic search, result ranking, and LLM answer generation |
| **[Chat Workflows](./workflows/chat.md)** | Chat session creation, message history, and multi-turn conversations |
| **[Data Models](./data-models.md)** | API request/response schemas, database tables, Valkey key schema |
| **[Architecture](./architecture.md)** | Service topology, container dependencies, networking, configuration |
| **[Operations & Config](./operations.md)** | Environment variables, Ollama setup, Qdrant configuration, troubleshooting |

---

## Important Files

### API Layer

| File | Purpose |
| --- | --- |
| `/services/api/api/main.py` | FastAPI app entry, router includes |
| `/services/api/api/config.py` | Environment settings (pydantic-settings) |
| `/services/api/api/models.py` | Request/response schemas (IngestJob, QueryRequest, QueryResponse, etc.) |
| `/services/api/api/routers/ingest.py` | `POST /ingest` (file upload) |
| `/services/api/api/routers/query.py` | `POST /query` (semantic search + LLM) |
| `/services/api/api/routers/collections.py` | Collection listing & deletion |
| `/services/api/api/routers/documents.py` | Document listing within collections |
| `/services/api/api/routers/jobs.py` | `GET /jobs/{job_id}` (ingestion status) |
| `/services/api/api/routers/title.py` | Title generation for chats |
| `/services/api/api/services/queue.py` | Valkey queue operations (enqueue, dequeue) |
| `/services/api/api/services/searcher.py` | Qdrant client & search logic |
| `/services/api/api/services/embedder.py` | Ollama embedding client |
| `/services/api/api/services/storage.py` | File storage (Docker volume) |

### Worker (Ingestion)

| File | Purpose |
| --- | --- |
| `/services/worker/worker/main.py` | Worker entry point |
| `/services/worker/worker/consumer.py` | Valkey BLPOP consumer loop, job status updates |
| `/services/worker/worker/pipeline.py` | Orchestrates parse → chunk → embed → index |
| `/services/worker/worker/parser.py` | Docling document converter |
| `/services/worker/worker/chunker.py` | Recursive text splitter |
| `/services/worker/worker/embedder.py` | Batch embedding via Ollama |
| `/services/worker/worker/indexer.py` | Qdrant upsert (deterministic SHA256 IDs) |
| `/services/worker/warmup/download_models.py` | Pre-downloads Docling & HF models at Docker build |

### Internal API (Chat History)

| File | Purpose |
| --- | --- |
| `/services/internal-api/api/main.py` | FastAPI entry (CORS, lifespan, router includes) |
| `/services/internal-api/api/database.py` | SQLAlchemy models (Session, Message), auto-create tables |
| `/services/internal-api/api/models.py` | Pydantic schemas |
| `/services/internal-api/api/routers/sessions.py` | Session CRUD |
| `/services/internal-api/api/routers/messages.py` | Message CRUD |
| `/services/internal-api/api/routers/chats.py` | Chat-specific endpoints |

### Frontend

| File | Purpose |
| --- | --- |
| `/services/web/src/lib/api.ts` | API client (calls main API) |
| `/services/web/src/routes/upload/` | Document upload UI |
| `/services/web/src/routes/query/` | Query/search UI |
| `/services/web/src/routes/collections/` | Collections & document management UI |
| `/services/chat/src/lib/api.ts` | API client (calls internal-api + main api) |
| `/services/chat/src/routes/[session_id]/` | Chat UI (session-based routing) |

### Configuration & Orchestration

| File | Purpose |
| --- | --- |
| `/.env.example` | Environment variable template |
| `/docker-compose.yml` | Service definitions, volumes, networking |
| `/nginx/default.conf` | Reverse proxy config (port routing) |
| `/Makefile` | Development targets (start, up, down, logs) |
| `/Brewfile` | Homebrew dependencies (Ollama) |

---

## Next Steps

1. **To understand the full architecture**, read [Architecture](./architecture.md)
2. **To dive into ingestion**, read [Ingestion Workflows](./workflows/ingestion.md)
3. **To learn the API contract**, read [Data Models](./data-models.md)
4. **To set up or troubleshoot**, read [Operations & Config](./operations.md)
5. **To add new features**, see the relevant workflow doc and check source files listed in the "Important Files" sections above

---

## Support & Links

- **GitHub**: https://github.com/datacontextstudio/sandbox
- **Demos**: See README.md for YouTube walkthrough videos
- **Issues**: File issues on GitHub
- **License**: MIT 2026
