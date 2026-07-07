# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## OpenWiki

This repository has documentation located in the /openwiki directory.

Start here:
- [OpenWiki quickstart](openwiki/quickstart.md)

OpenWiki includes repository overview, architecture notes, workflows, domain concepts, operations, integrations, testing guidance, and source maps.

When working in this repository, read the OpenWiki quickstart first, then follow its links to the relevant architecture, workflow, domain, operation, and testing notes.

## Repository Context

**DataContext Studio** is a self-hosted, open-source RAG (Retrieval-Augmented Generation) platform. Users upload documents, which are automatically parsed, chunked, embedded, and indexed into a vector database. They can then run semantic searches and get LLM-generated answers — all running on personal infrastructure.

**Status**: Functional local development stack (docker-compose based).
**License**: MIT 2026

## Tech Stack

| Layer            | Technology                                                        |
| ---------------- | ----------------------------------------------------------------- |
| Frontend         | SvelteKit 5 + TypeScript + Tailwind CSS 4 (`services/web`)        |
| Chat Frontend    | SvelteKit 5 + TypeScript + Tailwind CSS 4 (`services/chat`)       |
| Backend API      | FastAPI + Python 3.14 + Uvicorn                                   |
| Internal API     | FastAPI + Python 3.14 + Uvicorn + SQLAlchemy 2.0 + asyncpg        |
| Ingestion Worker | Python 3.14 + Docling + Valkey consumer                           |
| Vector DB        | Qdrant (COSINE distance, `nomic-embed-text` embeddings, 384 dims) |
| Relational DB    | PostgreSQL 16 (chat sessions & message history)                   |
| Task Queue       | Valkey 8 (FIFO list + job hash keys)                              |
| Reverse Proxy    | Nginx (`:3000`→web+api, `:3001`→chat+api, `:8000`→api only)       |
| LLM & Embeddings | Ollama running natively on macOS host (not containerized)         |

## Running Locally

**Prerequisites**: Docker Desktop, Ollama (`brew install ollama`)

```bash
./run.sh   # copies .env, installs Ollama, pulls models, builds + starts stack
```

Or manually:

```bash
cp .env.example .env
brew services start ollama
ollama pull llama3
ollama pull nomic-embed-text
docker-compose build
docker-compose up -d
```

**Access**: http://localhost:3000 (web app), http://localhost:3001 (chat app)

**Docker Compose services**: `nginx`, `web`, `api`, `internal-api`, `worker`, `qdrant`, `valkey`, `postgres`, `chat`
(Ollama runs on the host; Docker containers reach it via `host.docker.internal:11434`)

## Directory Structure

```
services/
  web/                  SvelteKit 5 frontend (document upload + search UI)
  chat/                 SvelteKit 5 chatbot UI
  api/                  FastAPI backend (RAG: ingest, query, collections)
  internal-api/         FastAPI chat session & message API (PostgreSQL)
  worker/               Ingestion worker (Docling → Qdrant)
nginx/                  Reverse proxy config
sample-data/            Test PDFs for development
docker-compose.yml      Local dev orchestration
run.sh                  One-shot setup script
.env / .env.example     Configuration
architecture-local.txt  ASCII diagram: current docker-compose stack
architecture-vms.txt    ASCII diagram: future production multi-VM layout
```

## Key Files

```
services/api/api/main.py              FastAPI app entry point
services/api/api/config.py            Settings (pydantic-settings)
services/api/api/models.py            Request/response data models
services/api/api/routers/             Endpoint handlers (ingest, query, collections, documents, jobs)
services/api/api/services/            Core services: embedder, searcher, queue, storage

services/worker/worker/consumer.py    Valkey queue consumer (dequeue → pipeline → status update)
services/worker/worker/pipeline.py    Orchestrates parse → chunk → embed → index
services/worker/worker/parser.py      Docling document converter (PDF/DOCX/PPTX → markdown)
services/worker/worker/chunker.py     Recursive text splitter
services/worker/worker/embedder.py    Batch embedding via Ollama
services/worker/worker/indexer.py     Qdrant upsert with SHA256 chunk IDs
services/worker/warmup/               Pre-downloads Docling/HF models at Docker build time

services/web/src/lib/api.ts           Frontend API client
services/web/src/routes/              SvelteKit pages: upload/, query/, collections/

services/internal-api/api/main.py              FastAPI entry point (CORS, router setup)
services/internal-api/api/database.py          SQLAlchemy models + create_tables() on startup
services/internal-api/api/models.py            Pydantic request/response schemas
services/internal-api/api/routers/sessions.py  Session CRUD endpoints
services/internal-api/api/routers/messages.py  Message CRUD endpoints

services/chat/src/lib/api.ts                        API client (internal-api + main api)
services/chat/src/routes/[session_id]/+page.svelte  Chat UI component
services/chat/src/routes/[session_id]/+page.ts      Page loader (fetches session + messages)
```

## API Endpoints

| Method | Endpoint                                 | Purpose                               |
| ------ | ---------------------------------------- | ------------------------------------- |
| POST   | `/ingest`                                | Upload file, enqueue ingestion job    |
| GET    | `/jobs/{job_id}`                         | Poll job status                       |
| POST   | `/query`                                 | Semantic search + optional LLM answer |
| GET    | `/collections`                           | List all collection names             |
| GET    | `/collections/{name}/documents`          | List documents in a collection        |
| DELETE | `/collections/{name}/documents/{job_id}` | Delete single document                |
| DELETE | `/collections/{name}`                    | Delete entire collection              |
| GET    | `/healthz`                               | Health check → `{"status": "ok"}`     |

No authentication on any endpoint.

## Internal API Endpoints

Served at `/internal-api/` (port 3000 and 3001 via nginx; port 8001 directly).

| Method | Endpoint                          | Purpose                                              |
| ------ | --------------------------------- | ---------------------------------------------------- |
| POST   | `/sessions`                       | Create chat session (body: `collections: list[str]`) |
| GET    | `/sessions/{session_id}`          | Fetch session metadata                               |
| POST   | `/sessions/{session_id}/messages` | Save a message (`role`: `user` or `assistant`)       |
| GET    | `/sessions/{session_id}/messages` | List all messages, ordered by `created_at`           |
| GET    | `/healthz`                        | Health check → `{"status": "ok"}`                    |

## Ingestion Pipeline

1. **API** saves uploaded file to `/data/documents`, enqueues `IngestJob` JSON to `dcs:queue:ingestion`
2. **Consumer** dequeues job (BLPOP, 5s timeout), sets status → `processing`
3. **Parser** (Docling + Tesseract OCR): converts PDF/DOCX/PPTX to markdown text
4. **Chunker**: recursive split (`\n\n` → `\n` → `. ` → space → char), 512 char chunks with 64 char overlap
5. **Embedder**: batch POST to Ollama `/api/embed` (model: `nomic-embed-text`, batch size: 32)
6. **Indexer**: upserts to Qdrant collection (deterministic SHA256 chunk IDs from `file_path:chunk_index`)
7. Status → `completed` with `chunks_indexed` count; on failure → `failed` + push to `dcs:dlq:ingestion`

## Configuration (.env)

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
QDRANT_HOST=qdrant
QDRANT_PORT=6333
VALKEY_URL=redis://valkey:6379
POSTGRES_DB=datacontext
POSTGRES_USER=dcs
POSTGRES_PASSWORD=dcs_password
DATABASE_URL=postgresql+asyncpg://dcs:dcs_password@postgres:5432/datacontext
```

Worker-only defaults (set in `worker/config.py`):

- `EMBED_MODEL=nomic-embed-text`
- `CHUNK_SIZE=512`, `CHUNK_OVERLAP=64`, `EMBED_BATCH_SIZE=32`
- `MAX_RETRIES=3`

## PostgreSQL Schema

Two tables are auto-created at `internal-api` startup via SQLAlchemy (`create_tables()`):

| Table              | Column        | Type        | Notes                                   |
| ------------------ | ------------- | ----------- | --------------------------------------- |
| `chatbot_sessions` | `id`          | UUID PK     |                                         |
|                    | `collections` | text[]      | Qdrant collections to search            |
|                    | `created_at`  | timestamptz |                                         |
| `chat_messages`    | `id`          | UUID PK     |                                         |
|                    | `session_id`  | UUID FK     | → `chatbot_sessions.id`, cascade delete |
|                    | `role`        | text        | `user` or `assistant`                   |
|                    | `content`     | text        | Message body                            |
|                    | `created_at`  | timestamptz |                                         |

## Chat Flow

1. Chat UI (`services/chat`) loads session metadata + message history from `internal-api` (PostgreSQL)
2. User sends a message → saved as `role=user` via `POST /sessions/{id}/messages`
3. Chat UI calls `POST /api/query` (main API) with `generate: true` to get an LLM answer
4. LLM response saved as `role=assistant` via `POST /sessions/{id}/messages`
5. UI re-renders with both messages appended

## Valkey Key Schema

| Key                   | Type | Purpose                                                                                        |
| --------------------- | ---- | ---------------------------------------------------------------------------------------------- |
| `dcs:queue:ingestion` | List | FIFO ingestion job queue                                                                       |
| `dcs:job:{job_id}`    | Hash | Job state: status, submitted_at, updated_at, file_path, collection_name, chunks_indexed, error |
| `dcs:dlq:ingestion`   | List | Dead-letter queue for failed jobs                                                              |

## Planned Future Architecture

`architecture-vms.txt` describes the eventual production layout:

- Separate GPU VMs for vLLM (LLM inference) and TEI (embeddings)
- Horizontally-scaled API VMs behind a load balancer
- Multi-node Qdrant cluster with persistent disk
- Object storage layer for raw documents

## Launching Claude

```bash
./claude.sh   # runs: claude --dangerously-skip-permissions
```
