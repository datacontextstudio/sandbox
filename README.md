# DataContext Studio

A self-hosted, open-source RAG (Retrieval-Augmented Generation) platform. Upload documents, have them automatically parsed, chunked, and embedded into a vector database, then query them with semantic search and optional LLM-generated answers — all running on your own infrastructure.

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│            docker-compose  (local MacBook dev)                │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    Public Layer                         │  │
│  │          nginx (reverse proxy)  host: :80               │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                             │                                 │
│  ┌──────────────────────────▼──────────────────────────────┐  │
│  │                    API Layer                            │  │
│  │             api  (FastAPI)  :8000                       │  │
│  └─────────────┬───────────────────────────────┬───────────┘  │
│                │                               │              │
│  ┌─────────────▼──────────────┐  ┌─────────────▼───────────┐  │
│  │  LLM + Embedding Layer     │  │    Vector DB Layer      │  │
│  │                            │  │                         │  │
│  │  ollama  :11434            │  │  qdrant  :6333/:6334    │  │
│  │  ├─ LLM model              │  │  volume: qdrant_data    │  │
│  │  └─ embed model            │  │                         │  │
│  │  volume: ollama_data       │  └─────────────────────────┘  │
│  └────────────────────────────┘                               │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  Ingestion Layer                        │  │
│  │                                                         │  │
│  │  redis :6379 ──► worker (ingestion container)           │  │
│  │                    ├── Parse documents (Docling)        │  │
│  │                    ├── Chunk documents                  │  │
│  │                    ├── Embed  (→ ollama)                │  │
│  │                    └── Index  (→ qdrant)                │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                  Storage Layer                          │  │
│  │         volume: storage_data  (raw documents)           │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

The `architecture-vms.txt` file in this repo describes the production multi-VM layout (separate GPU VMs for LLM and embeddings, a Qdrant cluster, horizontally-scaled API nodes).

## Tech Stack

| Component | Technology |
|---|---|
| API | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Document parsing | [Docling](https://github.com/DS4SD/docling) (PDF, DOCX, PPTX, and more) |
| LLM + Embeddings | [Ollama](https://ollama.com/) |
| Vector database | [Qdrant](https://qdrant.tech/) |
| Task queue | [Redis](https://redis.io/) |
| Reverse proxy | Nginx |
| Containerization | Docker + Docker Compose |

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- (Apple Silicon — recommended) Native Ollama for GPU acceleration: see [tip below](#apple-silicon--gpu-acceleration)

### 1. Clone and configure

```bash
git clone https://github.com/datacontextstudio/sandbox.git
cd sandbox
cp .env.example .env
```

The defaults in `.env` work out of the box with Docker Compose. Edit them if you need to point at external services.

### 2. Start the stack

```bash
docker-compose up -d
```

This starts nginx, the API, Ollama, Qdrant, Redis, and the ingestion worker.

### 3. Pull models (first time only)

```bash
docker-compose exec ollama ollama pull llama3
docker-compose exec ollama ollama pull nomic-embed-text
```

### 4. Verify

- API health check: `http://localhost:3000/healthz`
- Qdrant dashboard: `http://localhost:6333/dashboard`

### Apple Silicon / GPU Acceleration

Ollama inside Docker runs on the Linux VM and cannot access Apple Metal. For GPU-accelerated inference:

```bash
brew install ollama
ollama serve   # run in a separate terminal
```

Then in `.env`, change:

```
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

And comment out the `ollama` service in `docker-compose.yml`.

## API Usage

### Ingest a document

```bash
curl -X POST http://localhost:3000/ingest \
  -F "file=@/path/to/document.pdf" \
  -F "collection_name=my-docs"
```

Response:
```json
{
  "job_id": "abc123",
  "status": "pending",
  "file_path": "...",
  "collection_name": "my-docs"
}
```

### Check job status

```bash
curl http://localhost:3000/jobs/abc123
```

Response:
```json
{
  "job_id": "abc123",
  "status": "completed",
  "chunks_indexed": 42
}
```

Status values: `pending` → `processing` → `completed` / `failed`

### Query documents

Semantic search only:

```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key findings?",
    "collections": ["my-docs"],
    "top_k": 5
  }'
```

With LLM-generated answer:

```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key findings?",
    "collections": ["my-docs"],
    "top_k": 5,
    "generate": true,
    "llm_model": "llama3"
  }'
```

Response includes a `results` array (text, score, metadata) and an optional `answer` field when `generate` is `true`.

## Configuration

All configuration is via environment variables (set in `.env`):

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama endpoint |
| `QDRANT_HOST` | `qdrant` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant REST port |
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `STORAGE_PATH` | `/data/storage` | Raw document storage path |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama model used for embeddings |
| `CHUNK_SIZE` | `512` | Token target for text chunks |
| `CHUNK_OVERLAP` | `64` | Token overlap between adjacent chunks |
| `EMBED_BATCH_SIZE` | `32` | Chunks per embedding request |
| `MAX_RETRIES` | `3` | Worker retry attempts before dead-letter |

## Project Structure

```
sandbox/
├── docker-compose.yml        # Local development stack
├── nginx/default.conf        # Reverse proxy config
├── services/
│   ├── api/                  # FastAPI service (ingest, query, job status)
│   │   ├── api/
│   │   │   ├── routers/      # ingest.py, query.py, jobs.py
│   │   │   └── services/     # embedder, searcher, queue, storage
│   │   └── Dockerfile
│   └── worker/               # Background ingestion worker
│       ├── worker/
│       │   └── pipeline.py   # Parse → Chunk → Embed → Index
│       └── Dockerfile
├── architecture-local.txt    # ASCII diagram: local Docker Compose stack
└── architecture-vms.txt      # ASCII diagram: production multi-VM layout
```

## Contributing

This project is early-stage and actively evolving. Contributions, bug reports, and feature ideas are welcome.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes
4. Open a pull request

Please open an issue first for larger changes so we can discuss the approach.

## License

MIT License — see [LICENSE](LICENSE) for details.
