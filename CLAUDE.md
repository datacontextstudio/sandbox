# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Context

**DataContext Studio** is a self-hosted, open-source RAG (Retrieval-Augmented Generation) platform. Users upload documents, which are automatically parsed, chunked, embedded, and indexed into a vector database. They can then run semantic searches and get LLM-generated answers — all running on personal infrastructure.

**Status**: Functional local development stack (docker-compose based).
**License**: MIT 2026

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | SvelteKit 5 + TypeScript + Tailwind CSS 4 |
| Backend API | FastAPI + Python 3.14 + Uvicorn |
| Ingestion Worker | Python 3.14 + Docling + Redis consumer |
| Vector DB | Qdrant (COSINE distance, `nomic-embed-text` embeddings, 384 dims) |
| Task Queue | Redis 7 (FIFO list + job hash keys, AOF persistence) |
| Reverse Proxy | Nginx (port 3000 → web+api, port 8000 → api only) |
| LLM & Embeddings | Ollama running natively on macOS host (not containerized) |

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

**Access**: http://localhost:3000

**Docker Compose services**: `nginx`, `web`, `api`, `worker`, `qdrant`, `redis`
(Ollama runs on the host; Docker containers reach it via `host.docker.internal:11434`)

## Directory Structure

```
services/
  web/                  SvelteKit 5 frontend
  api/                  FastAPI backend
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

services/worker/worker/consumer.py    Redis queue consumer (dequeue → pipeline → status update)
services/worker/worker/pipeline.py    Orchestrates parse → chunk → embed → index
services/worker/worker/parser.py      Docling document converter (PDF/DOCX/PPTX → markdown)
services/worker/worker/chunker.py     Recursive text splitter
services/worker/worker/embedder.py    Batch embedding via Ollama
services/worker/worker/indexer.py     Qdrant upsert with SHA256 chunk IDs
services/worker/warmup/               Pre-downloads Docling/HF models at Docker build time

services/web/src/lib/api.ts           Frontend API client
services/web/src/routes/              SvelteKit pages: upload/, query/, collections/
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/ingest` | Upload file, enqueue ingestion job |
| GET | `/jobs/{job_id}` | Poll job status |
| POST | `/query` | Semantic search + optional LLM answer |
| GET | `/collections` | List all collection names |
| GET | `/collections/{name}/documents` | List documents in a collection |
| DELETE | `/collections/{name}/documents/{job_id}` | Delete single document |
| DELETE | `/collections/{name}` | Delete entire collection |
| GET | `/healthz` | Health check → `{"status": "ok"}` |

No authentication on any endpoint.

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
REDIS_URL=redis://redis:6379
```

Worker-only defaults (set in `worker/config.py`):
- `EMBED_MODEL=nomic-embed-text`
- `CHUNK_SIZE=512`, `CHUNK_OVERLAP=64`, `EMBED_BATCH_SIZE=32`
- `MAX_RETRIES=3`

## Redis Key Schema

| Key | Type | Purpose |
|-----|------|---------|
| `dcs:queue:ingestion` | List | FIFO ingestion job queue |
| `dcs:job:{job_id}` | Hash | Job state: status, submitted_at, updated_at, file_path, collection_name, chunks_indexed, error |
| `dcs:dlq:ingestion` | List | Dead-letter queue for failed jobs |

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
