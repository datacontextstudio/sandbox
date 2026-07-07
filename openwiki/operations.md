# Operations & Configuration

## Environment Setup

### Configuration Files

**`.env.example`** — Template for environment variables (check into git)

**`.env`** — Local environment configuration (not in git, created by `make env`)

**Location**: Repository root

### Required Environment Variables

Copy from `.env.example` to `.env`, or run `make env`:

```bash
make env
```

### Full Configuration Reference

```env
# ─────────────────────────────────────────────────────────────
# Ollama (LLM + Embeddings, runs natively on macOS)
# ─────────────────────────────────────────────────────────────
OLLAMA_BASE_URL=http://host.docker.internal:11434

# ─────────────────────────────────────────────────────────────
# Qdrant (Vector Database, Docker)
# ─────────────────────────────────────────────────────────────
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# ─────────────────────────────────────────────────────────────
# Valkey (Task Queue, Docker)
# ─────────────────────────────────────────────────────────────
VALKEY_URL=redis://valkey:6379

# ─────────────────────────────────────────────────────────────
# PostgreSQL (Chat History, Docker)
# ─────────────────────────────────────────────────────────────
POSTGRES_DB=datacontext
POSTGRES_USER=dcs
POSTGRES_PASSWORD=dcs_password
DATABASE_URL=postgresql+asyncpg://dcs:dcs_password@postgres:5432/datacontext

# ─────────────────────────────────────────────────────────────
# Storage (Document Upload Location)
# ─────────────────────────────────────────────────────────────
STORAGE_PATH=/data/documents
```

---

## Local Development Setup

### Prerequisites

- **Docker Desktop** (with Docker Compose)
- **Homebrew** (for macOS package management)
- **macOS** (current setup optimized for Mac, though architecture is portable)

### One-Command Quickstart

```bash
cd sandbox
make start
```

This runs:
1. `make setup` — Install Ollama, start service, pull models
2. `make build` — Build Docker images
3. `make up` — Start all containers

**First run**: ~20–30 minutes (Docker compiles dependencies)  
**Subsequent runs**: ~1–2 minutes

---

### Step-by-Step Manual Setup

#### 1. Clone & Configure

```bash
git clone https://github.com/datacontextstudio/sandbox.git
cd sandbox
make env
```

**Result**: Creates `.env` with defaults (can edit if needed)

---

#### 2. Install & Start Ollama

**Install Ollama** (via Homebrew):
```bash
make install
```

This runs `brew bundle`, which reads `/Brewfile`:
```
brew "ollama"
```

---

**Start Ollama service**:
```bash
make ollama-start
```

Equivalent to:
```bash
brew services start ollama
```

**Verify it's running**:
```bash
curl http://localhost:11434/api/tags
# Should list available models
```

---

**Pull required models**:
```bash
make ollama-models
```

This runs:
```bash
ollama pull llama3
ollama pull nomic-embed-text
```

**Expected output**:
```
pulling manifest
pulling a6d5c...
[==============>  ] 2.5 GB / 2.5 GB
...
```

(Each model is ~2.5 GB)

---

#### 3. Build & Start Docker Stack

**Build images**:
```bash
make build
```

Equivalent to:
```bash
docker-compose build
```

**Expected output**: Compiles services (api, internal-api, worker, etc.)

---

**Start stack**:
```bash
make up
```

Equivalent to:
```bash
docker-compose up -d
```

**Verify containers are running**:
```bash
docker-compose ps
```

**Expected output**:
```
NAME              COMMAND                  SERVICE       STATUS       PORTS
sandbox-nginx-1   "/docker-entrypoint..."  nginx         Up 2 min     0.0.0.0:3000->3000/tcp, 0.0.0.0:3001->3001/tcp, 0.0.0.0:8000->8000/tcp
sandbox-web-1     "npm run dev"            web           Up 2 min
sandbox-chat-1    "npm run dev"            chat          Up 2 min
sandbox-api-1     "uvicorn api.main:app"   api           Up 2 min
sandbox-internal-api-1  "uvicorn api.main:app"  internal-api  Up 2 min
sandbox-worker-1  "python worker/main.py"  worker        Up 2 min
sandbox-qdrant-1  "/qdrant --http-port"    qdrant        Up 2 min
sandbox-postgres-1  "postgres"             postgres      Up 2 min
sandbox-valkey-1  "valkey-server"          valkey        Up 2 min
```

---

#### 4. Access the Stack

**Web app**: http://localhost:3000
- Document upload
- Search/query interface
- Collection management

**Chat app**: http://localhost:3001
- Chatbot interface
- Multi-turn conversations

**API (direct)**: http://localhost:8000
- REST endpoints
- Swagger docs: http://localhost:8000/docs

**Qdrant dashboard**: http://localhost:6333/dashboard
- View vector collections
- Inspect embeddings

**Health check**:
```bash
curl http://localhost:8000/healthz
# {"status":"ok"}
```

---

## Common Operations

### View Logs

**All services**:
```bash
make logs
```

Equivalent to:
```bash
docker-compose logs -f
```

**Specific service**:
```bash
docker-compose logs -f worker
docker-compose logs -f api
docker-compose logs -f internal-api
```

---

### Stop the Stack

**Stop all containers** (but keep volumes):
```bash
make down
```

Equivalent to:
```bash
docker-compose down
```

**Stop Ollama**:
```bash
brew services stop ollama
```

---

### Restart Services

**Restart all**:
```bash
make restart
```

**Restart specific service**:
```bash
docker-compose restart api
docker-compose restart worker
```

---

### Clean Build

**Remove all containers and volumes** (⚠️ deletes data):
```bash
docker-compose down -v
```

**Rebuild images** (without cache):
```bash
docker-compose build --no-cache
```

---

## Debugging & Troubleshooting

### Issue: Ollama Not Reachable

**Symptom**: Query or ingest fails with "connection refused" to ollama

**Diagnosis**:
```bash
# Check if Ollama service is running
brew services list | grep ollama

# Try to reach it
curl http://localhost:11434/api/tags
```

**Fix**:
```bash
brew services start ollama
brew services restart ollama
```

**Alternative**: Check if process is stuck
```bash
ps aux | grep ollama
# Kill and restart:
brew services stop ollama
sleep 2
brew services start ollama
```

---

### Issue: Worker Not Processing Jobs

**Symptom**: Jobs stuck in "pending" status; check `GET /jobs/{job_id}` repeatedly

**Diagnosis**:
```bash
# Check if worker is running
docker-compose ps | grep worker

# View worker logs
docker-compose logs worker

# Check job queue in Valkey
docker-compose exec valkey valkey-cli LLEN dcs:queue:ingestion
```

**Fix**:
```bash
# Restart worker
docker-compose restart worker

# Or view full logs to see error
docker-compose logs -f worker
```

---

### Issue: Database Connection Errors

**Symptom**: Chat endpoints return 500; internal-api logs show PostgreSQL errors

**Diagnosis**:
```bash
# Check if postgres is running
docker-compose ps | grep postgres

# Check internal-api logs
docker-compose logs internal-api

# Try to connect directly
docker-compose exec postgres psql -U dcs -d datacontext -c "SELECT 1;"
```

**Fix**:
```bash
# Restart PostgreSQL and internal-api
docker-compose restart postgres internal-api

# Wait a few seconds for tables to be created
sleep 5

# Verify tables exist
docker-compose exec postgres psql -U dcs -d datacontext \
  -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
```

**Expected output**:
```
    tablename
─────────────────────
 chatbot_sessions
 chat_messages
```

---

### Issue: Qdrant Collection Not Found

**Symptom**: Query returns empty results or 500 error related to collection

**Diagnosis**:
```bash
# View all collections
curl http://localhost:6333/collections

# Or check via dashboard
http://localhost:6333/dashboard
```

**Fix**: Ingest a document to create the collection
```bash
# Upload a file via the web app
# Or use curl:
curl -X POST http://localhost:8000/ingest \
  -F "file=@/path/to/document.pdf" \
  -F "collection_name=default"
```

---

### Issue: Disk Space Errors

**Symptom**: Ingest fails with "out of space" or Docker container won't start

**Diagnosis**:
```bash
# Check available space
df -h /

# Check Docker disk usage
docker system df

# Check volume sizes
docker volume ls
docker volume inspect sandbox_storage_data
```

**Fix**:
```bash
# Clean up unused images/containers
docker system prune -a

# Remove unused volumes (⚠️ this deletes data)
docker volume prune

# Or specifically clear storage
docker volume rm sandbox_storage_data
```

---

### Issue: Port Already in Use

**Symptom**: Docker fails to start with "port X already in use"

**Diagnosis**:
```bash
# Find process using port 3000
lsof -i :3000

# Or for ports 3001, 8000, 6333, etc.
lsof -i :3001
```

**Fix**:
```bash
# Kill the process using the port
kill -9 <PID>

# Or change the port in docker-compose.yml or via environment
docker-compose -f docker-compose.yml up -d
```

---

### Issue: High Memory Usage

**Symptom**: Docker Desktop uses excessive memory, machine slows down

**Diagnosis**:
```bash
# Check container memory usage
docker stats

# Check Ollama memory usage
ps aux | grep ollama
```

**Causes**:
- Large embeddings batch size
- Large documents being parsed
- Ollama model too large for available GPU

**Fix**:
```bash
# Reduce EMBED_BATCH_SIZE in .env or worker config
# Reduce CHUNK_SIZE if documents are being held in memory
# Use a smaller Ollama model (e.g., neural-chat instead of llama3)

# Or limit Docker Desktop memory allocation in Docker Desktop settings
```

---

## Monitoring & Health Checks

### Health Endpoints

```bash
# API health
curl http://localhost:8000/healthz
# {"status":"ok"}

# Internal API health
curl http://localhost:8001/healthz
# {"status":"ok"}

# Ollama health
curl http://localhost:11434/api/tags
# {"models":[...]}
```

---

### Queue Status

```bash
docker-compose exec valkey valkey-cli

# View queue length
LLEN dcs:queue:ingestion

# View dead-letter queue length
LLEN dcs:dlq:ingestion

# View a specific job
HGETALL dcs:job:{job_id}

# View all keys
KEYS dcs:*
```

---

### Database Status

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U dcs -d datacontext

# Count sessions
SELECT COUNT(*) FROM chatbot_sessions;

# Count messages
SELECT COUNT(*) FROM chat_messages;

# View recent sessions
SELECT id, collections, created_at FROM chatbot_sessions ORDER BY created_at DESC LIMIT 5;
```

---

### Qdrant Status

```bash
# List collections
curl http://localhost:6333/collections

# View collection info
curl http://localhost:6333/collections/{collection_name}

# Example response:
# {
#   "status": "ok",
#   "result": {
#     "name": "default",
#     "vectors_count": 1500,
#     "config": {...}
#   }
# }
```

---

## Performance Tuning

### Ingestion Performance

**Chunk Size** (`CHUNK_SIZE`):
- Larger = fewer chunks, faster indexing, less granular search
- Smaller = more chunks, slower indexing, more granular search
- Default: 512 characters (good balance)
- Tuning: Adjust in `.env` or `/services/worker/worker/config.py`

**Chunk Overlap** (`CHUNK_OVERLAP`):
- Helps maintain semantic continuity across chunks
- Larger overlap = more redundancy, better context at boundaries
- Default: 64 characters
- Tuning: Adjust if using very small or large chunks

**Embedding Batch Size** (`EMBED_BATCH_SIZE`):
- Larger = faster throughput, higher memory
- Smaller = slower throughput, lower memory
- Default: 32
- Tuning: If GPU memory is constrained, reduce to 16 or 8

**Max Retries** (`MAX_RETRIES`):
- Number of times to retry a failed job before moving to DLQ
- Default: 3
- Tuning: Increase if transient failures are common (e.g., temporary Ollama offline)

---

### Query Performance

**Top-k** (default: 5):
- Number of results to return (user-specified in query)
- Larger top-k = more context for LLM, but slower search
- Typical range: 3–10

**Ollama Model Choice**:
- `llama3` (default): ~8B parameters, ~5 seconds per query
- `mistral`: ~7B parameters, ~4 seconds per query
- `neural-chat`: ~7B parameters, ~3 seconds per query
- Smaller models = faster but lower quality

---

### Container Resource Limits

**Docker Compose**:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

Add to `/docker-compose.yml` if memory is constrained.

---

## Backup & Recovery

### Backup Chat History

```bash
# Export PostgreSQL data
docker-compose exec postgres pg_dump -U dcs -d datacontext > backup.sql

# Or use Valkey persistence (snapshots are at /data/snapshots)
```

---

### Restore Chat History

```bash
# Restore PostgreSQL from backup
docker-compose exec postgres psql -U dcs -d datacontext < backup.sql
```

---

### Backup Vector Database

```bash
# Create a snapshot (Qdrant has built-in snapshots)
# Currently must be done via Qdrant API or manual volume backup

# Manual volume backup (for all Docker volumes)
docker run -v sandbox_qdrant_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/qdrant-backup.tar.gz /data
```

---

## Deployment to Production

See `/architecture-vms.txt` for the planned multi-VM production layout.

**Key differences from local dev**:
- Ollama on dedicated GPU VM (vLLM)
- Embeddings on separate GPU VM (TEI)
- Load-balanced API instances
- Qdrant cluster (multi-node)
- PostgreSQL HA (replication)
- Object storage (S3) instead of Docker volume
- Valkey cluster instead of single node

**Current local stack is suitable for**:
- Development & testing
- Demos
- Small-scale personal use
- Evaluation

---

## Source References

- Configuration: `.env.example`, `/services/*/config.py`
- Orchestration: `/docker-compose.yml`, `/Makefile`
- Automation: `/run.sh`, `/Brewfile`
- Package management: `/services/*/requirements.txt`, `/services/*/package.json`
- Deployment: `/nginx/default.conf` (reverse proxy config)
- Docs: `/architecture-local.txt`, `/architecture-vms.txt`
