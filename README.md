# DataContext Studio

A self-hosted, open-source RAG (Retrieval-Augmented Generation) platform. Upload documents, have them automatically parsed, chunked, and embedded into a vector database, then query them with semantic search and optional LLM-generated answers — all running on your own infrastructure.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│            docker-compose  (local MacBook dev)                 │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Public Layer                         │   │
│  │  nginx (reverse proxy)  :3000 → web  |  :8000 → api     │   │
│  └──────┬──────────────────────────────────────┬───────────┘   │
│         │                                      │               │
│  ┌──────▼──────────────────────┐  ┌────────────▼────────────┐  │
│  │      Frontend Layer         │  │       API Layer         │  │
│  │  web  (SvelteKit)           │  │  api  (FastAPI)  :8000  │  │
│  │  vite dev  :5173            │  └────────┬──────────┬─────┘  │
│  └─────────────────────────────┘           │          │        │
│                                ┌───────────▼──┐  ┌────▼──────┐ │
│                                │  LLM + Embed │  │ Vector DB │ │
│                                │              │  │           │ │
│                                │ ollama :11434│  │qdrant     │ │
│                                │ (macOS host) │  │:6333/:6334│ │
│                                │ ├─ LLM model │  │vol: data  │ │
│                                │ └─ embed mdl │  └───────────┘ │
│                                └──────────────┘                │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Ingestion Layer                        │   │
│  │                                                         │   │
│  │  redis :6379 ──► worker (ingestion container)           │   │
│  │                    ├── Parse documents (Docling)        │   │
│  │                    ├── Chunk documents                  │   │
│  │                    ├── Embed  (→ ollama)                │   │
│  │                    └── Index  (→ qdrant)                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Storage Layer                          │   │
│  │         volume: storage_data  (raw documents)           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  Notes                                                         │
│  • All services share a single Docker bridge network           │
│  • ollama runs natively on macOS host (not in Docker)          │
│  • Containers reach ollama via host.docker.internal:11434      │
│  • Web app exposed via nginx on :3000 (vite dev inside)        │
│  • API exposed via nginx on :8000 (FastAPI inside)             │
│  • Expose qdrant :6333 to host for the Qdrant web dashboard    │
└────────────────────────────────────────────────────────────────┘
```

The `architecture-vms.txt` file in this repo describes the production multi-VM layout (separate GPU VMs for LLM and embeddings, a Qdrant cluster, horizontally-scaled API nodes).

## Tech Stack

| Component        | Technology                                                              |
| ---------------- | ----------------------------------------------------------------------- |
| Frontend         | [SvelteKit 5](https://svelte.dev/docs/kit) + Tailwind CSS 4             |
| API              | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn                      |
| Document parsing | [Docling](https://github.com/DS4SD/docling) (PDF, DOCX, PPTX, and more) |
| LLM + Embeddings | [Ollama](https://ollama.com/)                                           |
| Vector database  | [Qdrant](https://qdrant.tech/)                                          |
| Task queue       | [Redis](https://redis.io/)                                              |
| Reverse proxy    | Nginx                                                                   |
| Containerization | Docker + Docker Compose                                                 |

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [Ollama](https://ollama.com/) running natively on macOS (see [Running Ollama](#running-ollama) below)

### Quickstart — use `run.sh`

The easiest way to get everything running is to use the provided `run.sh` script:

```bash
git clone https://github.com/datacontextstudio/sandbox.git
cd sandbox
./run.sh
```

The script does the following:

```bash
cp .env.example .env

brew install ollama
brew services start ollama
ollama pull llama3
ollama pull nomic-embed-text

# this will take a while (10-20 minutes), be patient
docker-compose build
docker-compose up -d
```

> **First-run warning:** The initial `docker-compose build` (or `docker-compose up`) can take **up to 30 minutes**. Docker needs to download and compile a large set of dependencies including Docling, PyTorch, and their transitive packages. Subsequent starts are fast.

### Manual setup

#### 1. Clone and configure

```bash
git clone https://github.com/datacontextstudio/sandbox.git
cd sandbox
cp .env.example .env
```

The defaults in `.env` work out of the box. Edit them if you need to point at external services.

#### 2. Start Ollama (native, outside Docker)

See [Running Ollama](#running-ollama) below. Ollama must be running before you start the Docker stack.

#### 3. Build and start the stack

> **First-run warning:** The initial build can take **up to 30 minutes** — Docker must download and compile Docling, PyTorch, and many other large dependencies. Subsequent starts are fast.

```bash
docker-compose build
docker-compose up -d
```

This starts nginx, the web app, the API, Qdrant, Redis, and the ingestion worker. Ollama runs on your Mac, not in Docker.

#### 4. Verify

- Web UI: `http://localhost:3000`
- API health check: `http://localhost:8000/healthz`
- Qdrant dashboard: `http://localhost:6333/dashboard`

### Running Ollama

This project is configured to run Ollama **natively on macOS**, outside of Docker. The `ollama` service block in `docker-compose.yml` is commented out by default. Ollama inside Docker Desktop runs in a Linux VM and cannot access Apple's Metal GPU, so native is both simpler and faster.

**Install and start Ollama:**

```bash
brew install ollama
brew services start ollama   # starts automatically on login
```

**Pull the required models (first time only):**

```bash
ollama pull llama3
ollama pull nomic-embed-text
```

The `.env` file points the Docker services at Ollama via `OLLAMA_BASE_URL=http://host.docker.internal:11434`.

#### Running Ollama inside Docker instead

If you prefer to run everything in Docker (e.g. on Linux, or without Homebrew), uncomment the following in `docker-compose.yml`:

1. The `ollama` service block (lines starting with `# ollama:`)
2. The `# - ollama` line under `depends_on` in the `api` service
3. The `# - ollama` line under `depends_on` in the `worker` service
4. The `# ollama_data:` line in the `volumes` section at the bottom

Then change `OLLAMA_BASE_URL` in `.env` to:

```
OLLAMA_BASE_URL=http://ollama:11434
```

And pull models via:

```bash
docker-compose exec ollama ollama pull llama3
docker-compose exec ollama ollama pull nomic-embed-text
```

## API Usage

### Ingest a document

```bash
curl -X POST http://localhost:8000/ingest \
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
curl http://localhost:8000/jobs/abc123
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
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key findings?",
    "collections": ["my-docs"],
    "top_k": 5
  }'
```

With LLM-generated answer:

```bash
curl -X POST http://localhost:8000/query \
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

| Variable           | Default               | Description                              |
| ------------------ | --------------------- | ---------------------------------------- |
| `OLLAMA_BASE_URL`  | `http://host.docker.internal:11434` | Ollama endpoint (native macOS host) |
| `QDRANT_HOST`      | `qdrant`              | Qdrant hostname                          |
| `QDRANT_PORT`      | `6333`                | Qdrant REST port                         |
| `REDIS_URL`        | `redis://redis:6379`  | Redis connection URL                     |
| `STORAGE_PATH`     | `/data/storage`       | Raw document storage path                |
| `EMBED_MODEL`      | `nomic-embed-text`    | Ollama model used for embeddings         |
| `CHUNK_SIZE`       | `512`                 | Token target for text chunks             |
| `CHUNK_OVERLAP`    | `64`                  | Token overlap between adjacent chunks    |
| `EMBED_BATCH_SIZE` | `32`                  | Chunks per embedding request             |
| `MAX_RETRIES`      | `3`                   | Worker retry attempts before dead-letter |

## Project Structure

```
sandbox/
├── docker-compose.yml        # Local development stack
├── nginx/default.conf        # Reverse proxy config (:3000→web, :8000→api)
├── services/
│   ├── web/                  # SvelteKit frontend (Svelte 5, Tailwind CSS 4)
│   │   ├── src/routes/       # SvelteKit pages and layouts
│   │   └── Dockerfile
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
