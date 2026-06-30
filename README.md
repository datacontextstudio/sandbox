# DataContext Studio

A self-hosted, open-source RAG (Retrieval-Augmented Generation) platform. Upload documents, have them automatically parsed, chunked, and embedded into a vector database, then query them with semantic search and optional LLM-generated answers — all running on your own infrastructure.

## Demos

| Title                                                    | Length | URL                                         |
| -------------------------------------------------------- | ------ | ------------------------------------------- |
| Indexing documents, running queries and making API calls | 3:47   | https://www.youtube.com/watch?v=GsPmb05vRUs |
| Using the LLM style interface                            | 2:24   | https://www.youtube.com/watch?v=ObyvFaTHk6I |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│               docker-compose  (local MacBook dev)                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                       Public Layer                           │   │
│  │  nginx  :3000→web+api  |  :3001→chat+api  |  :8000→api only  │   │
│  └──────┬───────────────────────────┬─────────────┬─────────────┘   │
│         │                           │             │                 │
│  ┌──────▼──────────┐  ┌─────────────▼───────┐  ┌──▼──────────────┐  │
│  │ Frontend Layer  │  │   Chat Layer        │  │   API Layer     │  │
│  │ web (SvelteKit) │  │  chat (SvelteKit)   │  │ api (FastAPI)   │  │
│  │ vite dev :5173  │  │  vite dev :5174     │  │ :8000           │  │
│  └─────────────────┘  └─────────────────────┘  │                 │  │
│                                                │ internal-api    │  │
│                                                │ (FastAPI) :8001 │  │
│                                                └──┬──────────┬───┘  │
│                                   ┌───────────────▼──┐  ┌────▼────┐ │
│                                   │  LLM + Embed     │  │ Vector  │ │
│                                   │  ollama :11434   │  │   DB    │ │
│                                   │  (macOS host)    │  │ qdrant  │ │
│                                   │  ├─ LLM model    │  │  :6333  │ │
│                                   │  └─ embed mdl    │  └─────────┘ │
│                                   └──────────────────┘              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Ingestion Layer                          │   │
│  │  valkey:6379 ──► worker (ingestion container)                │   │
│  │                    ├── Parse documents (Docling)             │   │
│  │                    ├── Chunk documents                       │   │
│  │                    ├── Embed  (→ ollama)                     │   │
│  │                    └── Index  (→ qdrant)                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      Storage Layer                           │   │
│  │  volume: storage_data  (raw documents)                       │   │
│  │  postgres :5432  vol: postgres_data  (chat sessions/msgs)    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Notes                                                              │
│  • All services share a single Docker bridge network                │
│  • ollama runs natively on macOS host (not in Docker)               │
│  • Containers reach ollama via host.docker.internal:11434           │
│  • Web app on :3000, chat app on :3001 (both via nginx)             │
│  • internal-api (FastAPI :8001) stores chat history in PostgreSQL   │
│  • Expose qdrant :6333 to host for the Qdrant web dashboard         │
└─────────────────────────────────────────────────────────────────────┘
```

The `architecture-vms.txt` file in this repo describes the production multi-VM layout (separate GPU VMs for LLM and embeddings, a Qdrant cluster, horizontally-scaled API nodes).

## Tech Stack

| Component        | Technology                                                               |
| ---------------- | ------------------------------------------------------------------------ |
| Frontend         | [SvelteKit 5](https://svelte.dev/docs/kit) + Tailwind CSS 4              |
| Chat Frontend    | SvelteKit 5 + Tailwind CSS 4 (chatbot UI, `services/chat`)               |
| API              | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn                       |
| Internal API     | FastAPI + SQLAlchemy 2.0 (chat session storage, `services/internal-api`) |
| Document parsing | [Docling](https://github.com/DS4SD/docling) (PDF, DOCX, PPTX, and more)  |
| LLM + Embeddings | [Ollama](https://ollama.com/)                                            |
| Vector database  | [Qdrant](https://qdrant.tech/)                                           |
| Relational DB    | PostgreSQL 16 (chat sessions & message history)                          |
| Task queue       | [Valkey](https://valkey.io/)                                             |
| Reverse proxy    | Nginx                                                                    |
| Containerization | Docker + Docker Compose                                                  |

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [Homebrew](https://brew.sh/) (used to install Ollama via `brew bundle`)

### Quickstart

```bash
git clone https://github.com/datacontextstudio/sandbox.git
cd sandbox
make start
```

`make start` runs the full first-time setup: copies `.env`, installs Ollama via Homebrew, pulls the required models, builds the Docker images, and starts the stack.

> **First-run warning:** The initial build can take **up to 30 minutes** — Docker must download and compile Docling, PyTorch, and many other large dependencies. Subsequent starts are fast.

### Make targets

| Target               | What it does                                                   |
| -------------------- | -------------------------------------------------------------- |
| `make install`       | Install Homebrew dependencies (`brew bundle`)                  |
| `make env`           | Copy `.env.example` to `.env` (skips if `.env` already exists) |
| `make ollama-start`  | Start Ollama as a macOS background service                     |
| `make ollama-models` | Pull required Ollama models (`llama3`, `nomic-embed-text`)     |
| `make setup`         | Run `env` → `install` → `ollama-start` → `ollama-models`       |
| `make build`         | Build Docker images (`docker-compose build`)                   |
| `make up`            | Start the stack in the background (`docker-compose up -d`)     |
| `make down`          | Stop and remove containers (`docker-compose down`)             |
| `make logs`          | Tail all container logs (`docker-compose logs -f`)             |
| `make restart`       | `down` then `up`                                               |
| `make start`         | Full first-time setup: `setup` + `build` + `up`                |

### Manual setup

#### 1. Clone and configure

```bash
git clone https://github.com/datacontextstudio/sandbox.git
cd sandbox
make env
```

The defaults in `.env` work out of the box. Edit them if you need to point at external services.

#### 2. Start Ollama (native, outside Docker)

See [Running Ollama](#running-ollama) below. Ollama must be running before you start the Docker stack.

```bash
make install
make ollama-start
make ollama-models
```

#### 3. Build and start the stack

> **First-run warning:** The initial build can take **up to 30 minutes** — Docker must download and compile Docling, PyTorch, and many other large dependencies. Subsequent starts are fast.

```bash
make build
make up
```

This starts nginx, the web app, the API, Qdrant, Valkey, and the ingestion worker. Ollama runs on your Mac, not in Docker.

#### 4. Verify

- Web UI: `http://localhost:3000`
- Chat UI: `http://localhost:3001`
- API health check: `http://localhost:8000/healthz`
- Internal API health check: `http://localhost:3001/internal-api/healthz`
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

## Exposed URLs

All URLs available on `localhost` after `docker-compose up -d`:

| URL                                   | Service                | Description                                         |
| ------------------------------------- | ---------------------- | --------------------------------------------------- |
| `http://localhost:3000`               | Web app                | Document upload, search, and collection management  |
| `http://localhost:3000/api/`          | Main API (proxied)     | FastAPI — ingest, query, jobs, collections          |
| `http://localhost:3000/internal-api/` | Internal API (proxied) | Chat session & message API                          |
| `http://localhost:3001`               | Chat app               | LLM chatbot interface                               |
| `http://localhost:3001/api/`          | Main API (proxied)     | Same FastAPI, served from the chat port             |
| `http://localhost:3001/internal-api/` | Internal API (proxied) | Same internal API, served from the chat port        |
| `http://localhost:8000`               | Main API (direct)      | FastAPI without nginx in the path                   |
| `http://localhost:8000/docs`          | Main API docs          | Swagger / OpenAPI UI                                |
| `http://localhost:8000/healthz`       | Main API health        | Returns `{"status": "ok"}`                          |
| `http://localhost:6333`               | Qdrant REST            | Vector DB REST API                                  |
| `http://localhost:6333/dashboard`     | Qdrant dashboard       | Web UI for browsing collections and running queries |
| `localhost:6334`                      | Qdrant gRPC            | gRPC API (TCP, not HTTP)                            |
| `localhost:6379`                      | Valkey                 | Task queue (TCP, not HTTP)                          |

> The `/api/` and `/internal-api/` paths are available on both `:3000` and `:3001` so that browser-side code in each app can call APIs without cross-origin requests.

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

| Variable            | Default                                                           | Description                              |
| ------------------- | ----------------------------------------------------------------- | ---------------------------------------- |
| `OLLAMA_BASE_URL`   | `http://host.docker.internal:11434`                               | Ollama endpoint (native macOS host)      |
| `QDRANT_HOST`       | `qdrant`                                                          | Qdrant hostname                          |
| `QDRANT_PORT`       | `6333`                                                            | Qdrant REST port                         |
| `VALKEY_URL`        | `redis://valkey:6379`                                             | Valkey connection URL                    |
| `STORAGE_PATH`      | `/data/storage`                                                   | Raw document storage path                |
| `EMBED_MODEL`       | `nomic-embed-text`                                                | Ollama model used for embeddings         |
| `CHUNK_SIZE`        | `512`                                                             | Token target for text chunks             |
| `CHUNK_OVERLAP`     | `64`                                                              | Token overlap between adjacent chunks    |
| `EMBED_BATCH_SIZE`  | `32`                                                              | Chunks per embedding request             |
| `MAX_RETRIES`       | `3`                                                               | Worker retry attempts before dead-letter |
| `POSTGRES_DB`       | `datacontext`                                                     | PostgreSQL database name                 |
| `POSTGRES_USER`     | `dcs`                                                             | PostgreSQL user                          |
| `POSTGRES_PASSWORD` | `dcs_password`                                                    | PostgreSQL password                      |
| `DATABASE_URL`      | `postgresql+asyncpg://dcs:dcs_password@postgres:5432/datacontext` | Async connection string for internal-api |

## Project Structure

```
sandbox/
├── docker-compose.yml        # Local development stack
├── nginx/default.conf        # Reverse proxy (:3000→web, :3001→chat, :8000→api)
├── services/
│   ├── web/                  # SvelteKit frontend (document upload + search UI)
│   │   ├── src/routes/       # SvelteKit pages and layouts
│   │   └── Dockerfile
│   ├── chat/                 # SvelteKit chatbot UI
│   │   ├── src/routes/[session_id]/  # Chat page (loads session + message history)
│   │   └── Dockerfile
│   ├── api/                  # FastAPI service (ingest, query, job status)
│   │   ├── api/
│   │   │   ├── routers/      # ingest.py, query.py, jobs.py
│   │   │   └── services/     # embedder, searcher, queue, storage
│   │   └── Dockerfile
│   ├── internal-api/         # FastAPI service (chat sessions + messages → PostgreSQL)
│   │   ├── api/
│   │   │   ├── database.py   # SQLAlchemy models (chatbot_sessions, chat_messages)
│   │   │   └── routers/      # sessions.py, messages.py
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
