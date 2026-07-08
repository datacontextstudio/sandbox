# Query Workflow

## Overview

The query workflow enables semantic search across indexed documents and optionally generates LLM-powered answers.

**Core steps**:
1. Embed the user's query text
2. Search across specified Qdrant collections
3. Optionally generate an LLM answer from the top results

---

## Request/Response Structure

**Endpoint**: `POST /query`

**Handler**: `/services/api/api/routers/query.py`

### Request

```json
{
  "query": "What is the refund policy?",
  "collections": ["default", "finance-docs"],
  "top_k": 5,
  "generate": false,
  "llm_model": "llama3.1",
  "include_results": true
}
```

**Fields**:

| Field | Type | Default | Purpose |
| --- | --- | --- | --- |
| `query` | string | required | The user's search query |
| `collections` | list[string] | ["default"] | Which Qdrant collections to search |
| `top_k` | int | 5 | Number of top results to return |
| `generate` | bool | false | Whether to generate an LLM answer |
| `llm_model` | string | "llama3.1" | Which Ollama model to use for generation |
| `include_results` | bool | true | Whether to include search results in response |

### Response

```json
{
  "query": "What is the refund policy?",
  "results": [
    {
      "text": "Refunds are processed within 5-7 business days...",
      "score": 0.92,
      "collection_name": "default",
      "file_path": "/data/documents/job-123/policy.pdf",
      "chunk_index": 3,
      "metadata": {"source": "policy-docs"}
    },
    ...
  ],
  "answer": "Based on the refund policy, refunds are typically processed within 5-7 business days to the original payment method."
}
```

**Fields**:

| Field | Type | Purpose |
| --- | --- | --- |
| `query` | string | Echo of the user's query |
| `results` | list[QueryResult] or null | Search results (null if `include_results=false`) |
| `answer` | string or null | LLM-generated answer (null if `generate=false` or no results) |

**QueryResult**:

| Field | Type | Purpose |
| --- | --- | --- |
| `text` | string | The chunk text |
| `score` | float | Similarity score (0-1, cosine similarity) |
| `collection_name` | string | Which collection this result came from |
| `file_path` | string | Path to the original document |
| `chunk_index` | int | Index of this chunk within the document |
| `metadata` | dict | Custom metadata from ingestion |

---

## Step-by-Step Flow

### 1. Embed Query Text

**Function**: `await embedder.embed_text(query_text: str) -> List[float]`

**Handler**: `/services/api/api/services/embedder.py`

**Process**:
1. POST to Ollama `/api/embed` endpoint:
   ```json
   {
     "model": "nomic-embed-text",
     "input": ["What is the refund policy?"]
   }
   ```
2. Receive 384-dimensional embedding vector
3. Return the vector

**Configuration**:
- `OLLAMA_BASE_URL` from `.env` (e.g., `http://host.docker.internal:11434`)
- Model: `nomic-embed-text` (384 dimensions)

**Error Handling**:
- If Ollama is offline: raises `HTTPException(502, "Embedding service error")`

**Source**: `/services/api/api/services/embedder.py`

---

### 2. Search Collections

**Function**: `await search_many(collections: List[str], vector: List[float], top_k: int) -> List[QueryResult]`

**Handler**: `/services/api/api/services/searcher.py`

**Process**:
1. For each collection:
   - Query Qdrant with the embedding vector
   - Request top-k results (cosine similarity)
   - Extract payload (text, file_path, chunk_index, metadata)
2. Combine and deduplicate results across collections
3. Sort by score descending
4. Return top-k overall results

**Qdrant Query**:
```python
results = qdrant_client.search(
    collection_name=collection_name,
    query_vector=vector,
    limit=top_k,
    with_payload=True  # Include all metadata
)
```

**Result Mapping**:
```python
for point in results:
    QueryResult(
        text=point.payload["text"],
        score=point.score,
        collection_name=collection_name,
        file_path=point.payload["file_path"],
        chunk_index=point.payload["chunk_index"],
        metadata=point.payload.get("metadata", {})
    )
```

**Error Handling**:
- If Qdrant is offline: raises `HTTPException(502, "Search error")`
- If collection doesn't exist: Qdrant returns empty results (no error)

**Source**: `/services/api/api/services/searcher.py`

---

### 3. Generate Answer (Optional)

**Condition**: Only if `generate=true` and results are non-empty

**Process**:

#### 3.1 Build Context

Concatenate the text of all retrieved results:

```python
context = "\n\n".join(r.text for r in results)
```

**Example**:
```
Refunds are processed within 5-7 business days.

Customers may request a refund up to 30 days after purchase.

Refund requests must include the order number and reason for return.
```

---

#### 3.2 Build Prompt

```python
system_message = (
    "You are a helpful assistant. Answer questions directly and concisely "
    "using the provided context. Do not begin your answer with phrases like "
    "'According to the context', 'Based on the context', or similar meta-references. "
    "Just answer the question. You may use bullet points."
)

prompt = (
    f"Use the following context to answer the question.\n\n"
    f"Context:\n{context}\n\n"
    f"Question: {query}\n\n"
    f"Answer:"
)

messages = [
    {"role": "system", "content": system_message},
    {"role": "user", "content": prompt}
]
```

**Design notes**:
- System message instructs LLM to avoid meta-commentary ("According to the context")
- User message includes both context and question
- Prompt structure helps LLM focus on answering, not explaining

---

#### 3.3 Load Available MCP Tools (Optional)

**Function**: `await get_tools(mcp_servers_json: str) -> list[dict]`

**Handler**: `/services/api/api/services/mcp_client.py`

**Process**:
1. Parse MCP servers configuration from `settings.mcp_servers`
2. Connect to each configured MCP server (via stdio or SSE)
3. Call `session.list_tools()` to retrieve available tools
4. Format tools for Ollama consumption:
   ```json
   {
     "type": "function",
     "function": {
       "name": "tool_name",
       "description": "Tool description",
       "parameters": {...}
     }
   }
   ```

**Configuration**:
- `MCP_SERVERS` from `.env` (JSON array of server configs)
- Each server config: `{"type": "stdio"|"sse", "command": "...", "args": [...], "env": {...}}`
- Returns empty list if no servers configured or connection fails

**Source**: `/services/api/api/services/mcp_client.py`

**Example server shipped with this repo**: `services/fake-refund` is a demo
MCP server (SSE transport, `mcp.server.fastmcp.FastMCP`) exposing fake Super
Payments refund tools (`list_transactions`, `get_transaction`,
`refund_transaction`) over seeded transaction data matching the
`sample-data/*_transaction_report.pdf` documents. It's registered by default
via `MCP_SERVERS` in `.env.example` and reachable at
`http://fake-refund:8010/sse` on the internal docker network. See
`/services/fake-refund/fake_refund/server.py` for the tool implementations.

---

#### 3.4 Agentic Tool Calling Loop

The query handler implements an agentic loop that iterates up to `_MAX_TOOL_ITERATIONS` (10) times:

```python
for _ in range(_MAX_TOOL_ITERATIONS):
    payload: dict = {
        "model": req.llm_model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    resp = await client.post(
        f"{settings.ollama_base_url}/api/chat",
        json=payload,
    )
    msg = resp.json()["message"]
    
    tool_calls = msg.get("tool_calls")
    if not tool_calls:
        answer = msg["content"]
        break
    
    # Execute tool calls and append results to messages
    messages.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": tool_calls})
    for tc in tool_calls:
        fn = tc["function"]
        name = fn["name"]
        args = fn.get("arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
        result = await call_tool(settings.mcp_servers, name, args)
        messages.append({"role": "tool", "content": result})
```

**Iteration Logic**:
1. Build payload with model, messages, and tools (if any available)
2. Send to Ollama `/api/chat`
3. Check response for `tool_calls` field
4. If no tool calls: extract answer and break loop
5. If tool calls present:
   - Append assistant message with tool calls to messages
   - For each tool call: parse arguments, execute via `call_tool`, append tool result
   - Continue to next iteration (LLM responds with more context)

**Configuration**:
- `llm_model` from request (default: "llama3.1")
- `OLLAMA_BASE_URL` from `.env`
- Timeout: 120 seconds (generous for large contexts)
- Streaming: disabled (wait for full response)
- `_MAX_TOOL_ITERATIONS`: 10 (prevents infinite loops)

**Tool Execution**:
- **Function**: `await call_tool(mcp_servers_json: str, tool_name: str, arguments: dict) -> str`
- **Handler**: `/services/api/api/services/mcp_client.py`
- **Process**:
  1. Connect to each MCP server
  2. List tools, find matching tool_name
  3. Execute with `session.call_tool(tool_name, arguments)`
  4. Extract text content from response
  5. Return concatenated text or error message

**Error Handling**:
- If Ollama is offline: raises `HTTPException(502, "LLM service error")`
- If model doesn't exist: Ollama returns error → propagated to user
- If tool not found: returns `"Tool '{tool_name}' not found in any configured MCP server."`

**Source**: `/services/api/api/routers/query.py` and `/services/api/api/services/mcp_client.py`

---

### 4. Return Response

After the agentic loop completes (either via breaking on no tool calls or max iterations reached):

```python
QueryResponse(
    query=req.query,
    results=results if req.include_results else None,
    answer=answer
)
```

**Conditional fields**:
- `results` is null if `include_results=false`
- `answer` is null if `generate=false` or no results were found
- `answer` may contain LLM reasoning and tool call results if tools were executed

---

## Key Concepts

### Cosine Similarity Scoring

**Score Range**: 0 to 1 (for normalized embeddings)

**Interpretation**:
- `1.0` = Perfect match (identical embeddings)
- `0.9+` = Very similar semantically
- `0.5-0.9` = Somewhat related
- `< 0.5` = Weak relevance

**Example**:
- Query: "What is the refund policy?"
- Result 1: "Our refund policy allows..." (score: 0.95)
- Result 2: "Customer support can be reached at..." (score: 0.42)

### Multi-Collection Search

**Use Case**: Search across multiple document categories

**Example**:
```json
{
  "query": "How do I contact support?",
  "collections": ["docs", "faq", "support-guides"]
}
```

**Behavior**:
- Query each collection independently
- Combine and rank results by score
- Return top-k across all collections

**Determinism**: Results are consistent (same query on same data = same results)

### Result Deduplication

If multiple chunks from the same document match:

**Current behavior**: All matching chunks are returned (up to top-k)

**Future improvement**: Option to deduplicate by file_path, returning only the top chunk per document

---

## Performance Characteristics

### Latency

| Step | Typical Duration |
| --- | --- |
| Embed query | 50-200ms |
| Search Qdrant (single collection) | 10-50ms |
| Search Qdrant (multiple collections) | 20-100ms |
| Generate answer (LLM) | 2-10 seconds |
| **Total** (without generation) | 100-300ms |
| **Total** (with generation) | 2-11 seconds |

**Factors**:
- Embedding latency depends on Ollama model and GPU availability
- Search latency depends on collection size and query complexity
- Generation latency depends on context size and LLM model

### Memory Usage

- Embedding vector: 384 floats = ~1.5 KB per query
- Qdrant search: results held in memory briefly
- LLM generation: depends on context size and model

### Scalability

- **Qdrant collections** can store millions of chunks
- **Search latency** scales sublinearly with collection size (HNSW index)
- **Multi-collection search** has minimal overhead (parallel queries possible)
- **LLM generation** is the primary bottleneck; consider result limiting

---

## Error Handling

### Embedding Service Error

**Symptom**: Query returns `HTTP 502, "Embedding service error: ..."`

**Cause**: Ollama is offline or unreachable

**Fix**:
```bash
brew services start ollama
# or verify it's running:
curl http://localhost:11434/api/tags
```

### Search Error

**Symptom**: Query returns `HTTP 502, "Search error: ..."`

**Cause**: Qdrant is offline or network issue

**Fix**:
```bash
docker-compose restart qdrant
# or check logs:
docker-compose logs qdrant
```

### LLM Service Error

**Symptom**: Query returns `HTTP 502, "LLM service error: ..."` when `generate=true`

**Cause**: Ollama offline or model not available

**Fix**:
```bash
brew services start ollama
ollama pull llama3  # if model is missing
```

### Collection Not Found

**Symptom**: Query returns empty results (not an error, but unexpected)

**Cause**: Collection doesn't exist or typo in collection name

**Fix**: Ingest a document to that collection first, or use an existing collection name

---

## Tuning & Customization

### Change top-k Results

```json
{
  "query": "refund policy",
  "top_k": 10  // Get more results (default: 5)
}
```

**Trade-off**:
- Larger top-k = more context for LLM, but slower
- Smaller top-k = faster, but may miss relevant chunks

### Change LLM Model

```json
{
  "query": "refund policy",
  "generate": true,
  "llm_model": "mistral"  // Use Mistral instead of Llama3
}
```

**Requirement**: Model must be installed in Ollama

```bash
ollama pull mistral
```

### Disable Results in Response

```json
{
  "query": "refund policy",
  "include_results": false,
  "generate": true  // Only return the answer, not the chunks
}
```

**Use case**: When frontend only needs the LLM answer (saves bandwidth)

---

## Testing & Debugging

### Manual API Test

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "refund policy",
    "collections": ["default"],
    "top_k": 5,
    "generate": false
  }'
```

### Check Collection Contents

```bash
# Access Qdrant dashboard
http://localhost:6333/dashboard

# Or use curl to list collections
curl http://localhost:6333/collections
```

### Monitor Ollama

```bash
# Check loaded models
ollama list

# Check Ollama service
brew services list | grep ollama

# Watch Ollama logs
tail -f ~/.ollama/logs/server.log
```

---

## Source References

- Query endpoint: `/services/api/api/routers/query.py`
- Embedder service: `/services/api/api/services/embedder.py`
- Searcher service: `/services/api/api/services/searcher.py`
- Data models: `/services/api/api/models.py`
- Web frontend query UI: `/services/web/src/routes/query/`
