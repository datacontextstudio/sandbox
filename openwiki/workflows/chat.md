# Chat Workflow

## Overview

The chat workflow enables multi-turn conversations with persistent history stored in PostgreSQL. Users create sessions, send messages, receive LLM answers, and browse message history.

**Core flow**:
1. Create a chat session (specifying collections to search)
2. User sends a message
3. LLM generates an answer
4. Both user and assistant messages are saved
5. History is persisted for later retrieval

---

## Request/Response Structure

### Session Management

#### Create Session

**Endpoint**: `POST /internal-api/sessions`

**Handler**: `/services/internal-api/api/routers/sessions.py`

**Request**:
```json
{
  "collections": ["default", "finance-docs"]
}
```

**Response**:
```json
{
  "id": "uuid-string",
  "collections": ["default", "finance-docs"],
  "created_at": "2024-01-01T10:00:00Z"
}
```

#### Get Session

**Endpoint**: `GET /internal-api/sessions/{session_id}`

**Request**: (no body)

**Response**:
```json
{
  "id": "uuid-string",
  "collections": ["default", "finance-docs"],
  "created_at": "2024-01-01T10:00:00Z"
}
```

### Message Management

#### Save Message

**Endpoint**: `POST /internal-api/sessions/{session_id}/messages`

**Request**:
```json
{
  "role": "user",
  "content": "What is the refund policy?"
}
```

**Fields**:
- `role`: "user" or "assistant"
- `content`: Message text

**Response**:
```json
{
  "id": "uuid-string",
  "session_id": "uuid-string",
  "role": "user",
  "content": "What is the refund policy?",
  "created_at": "2024-01-01T10:00:00.123Z"
}
```

#### Get Messages

**Endpoint**: `GET /internal-api/sessions/{session_id}/messages`

**Request**: (no body, optional query params for pagination)

**Response**:
```json
[
  {
    "id": "msg-uuid-1",
    "session_id": "session-uuid",
    "role": "user",
    "content": "What is the refund policy?",
    "created_at": "2024-01-01T10:00:00.123Z"
  },
  {
    "id": "msg-uuid-2",
    "session_id": "session-uuid",
    "role": "assistant",
    "content": "Refunds are processed within 5-7 business days...",
    "created_at": "2024-01-01T10:00:05.456Z"
  },
  ...
]
```

**Ordering**: By `created_at` ascending (oldest first)

---

## Step-by-Step Flow

### 1. Initialize Chat Session

**User Action**: Open chat app or click "New Chat"

**API Call**:
```
POST /internal-api/sessions
{
  "collections": ["default"]
}
```

**Handler**: `/services/internal-api/api/routers/sessions.py` → `create_session()`

**Process**:

1. Generate UUID for session
2. Parse request body (collections list)
3. Insert into PostgreSQL `chatbot_sessions` table:
   ```sql
   INSERT INTO chatbot_sessions (id, collections, created_at)
   VALUES ('{uuid}', '{"default"}', NOW())
   RETURNING id, collections, created_at
   ```
4. Return session object

**Database State**:
```
chatbot_sessions
├─ id: "550e8400-e29b-41d4-a716-446655440000"
├─ collections: ["default"]
└─ created_at: 2024-01-01 10:00:00+00
```

**Source**: `/services/internal-api/api/routers/sessions.py`

---

### 2. User Sends Message

**User Action**: Type message and press Enter

**Frontend** (`/services/chat/src/routes/[session_id]/+page.svelte`):

```typescript
// 1. Save user message
const userMsg = await fetch(`/internal-api/sessions/${sessionId}/messages`, {
  method: "POST",
  body: JSON.stringify({
    role: "user",
    content: userInput
  })
});

// 2. Clear input, append message to UI
userInput = "";
messages.push(await userMsg.json());

// 3. Call query API for LLM response
const queryResp = await fetch("/api/query", {
  method: "POST",
  body: JSON.stringify({
    query: userInput,
    collections: session.collections,
    generate: true,
    include_results: false  // Don't send chunks to UI
  })
});

// 4. Save assistant response
const answer = queryResp.answer;
const assistantMsg = await fetch(`/internal-api/sessions/${sessionId}/messages`, {
  method: "POST",
  body: JSON.stringify({
    role: "assistant",
    content: answer
  })
});

// 5. Append assistant message to UI
messages.push(await assistantMsg.json());
```

---

### 3. Save User Message

**API Call**:
```
POST /internal-api/sessions/{session_id}/messages
{
  "role": "user",
  "content": "What is the refund policy?"
}
```

**Handler**: `/services/internal-api/api/routers/messages.py` → `create_message()`

**Process**:

1. Validate session_id exists (query chatbot_sessions)
2. Generate UUID for message
3. Insert into PostgreSQL `chat_messages` table:
   ```sql
   INSERT INTO chat_messages (id, session_id, role, content, created_at)
   VALUES (
     '{uuid}',
     '{session_id}',
     'user',
     'What is the refund policy?',
     NOW()
   )
   RETURNING id, session_id, role, content, created_at
   ```
4. Return message object

**Database State**:
```
chat_messages
├─ id: "msg-uuid-1"
├─ session_id: "550e8400-e29b-41d4-a716-446655440000"
├─ role: "user"
├─ content: "What is the refund policy?"
└─ created_at: 2024-01-01 10:00:05+00
```

**Source**: `/services/internal-api/api/routers/messages.py`

---

### 4. Generate LLM Answer

**Frontend calls** `POST /api/query` with `generate=true`:

```json
{
  "query": "What is the refund policy?",
  "collections": ["default"],
  "generate": true,
  "include_results": false
}
```

**Handler**: `/services/api/api/routers/query.py`

**Process** (see [Query Workflows](./query.md) for details):

1. Embed query → 384-dim vector
2. Search Qdrant collections → top-k results
3. Build prompt with system message + context + query
4. Call Ollama `/api/chat` with llama3 model
5. Return answer text

**Response**:
```json
{
  "query": "What is the refund policy?",
  "results": null,
  "answer": "Refunds are processed within 5-7 business days to the original payment method. Customers can request a refund up to 30 days after purchase."
}
```

**Source**: `/services/api/api/routers/query.py`

---

### 5. Save Assistant Message

**API Call**:
```
POST /internal-api/sessions/{session_id}/messages
{
  "role": "assistant",
  "content": "Refunds are processed within 5-7 business days..."
}
```

**Handler**: `/services/internal-api/api/routers/messages.py` → `create_message()`

**Process**: (same as step 3, but role="assistant")

**Database State**:
```
chat_messages
├─ id: "msg-uuid-1"
│  role: "user", content: "What is the refund policy?", created_at: T+0s
└─ id: "msg-uuid-2"
   role: "assistant", content: "Refunds are processed...", created_at: T+3s
```

---

### 6. Load Message History

**User Action**: Open existing session or scroll back

**API Call**:
```
GET /internal-api/sessions/{session_id}/messages
```

**Handler**: `/services/internal-api/api/routers/messages.py` → `get_messages()`

**Process**:

1. Validate session_id exists
2. Query all messages for this session:
   ```sql
   SELECT id, session_id, role, content, created_at
   FROM chat_messages
   WHERE session_id = '{session_id}'
   ORDER BY created_at ASC
   ```
3. Return array of messages

**Response**:
```json
[
  {
    "id": "msg-uuid-1",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "user",
    "content": "What is the refund policy?",
    "created_at": "2024-01-01T10:00:05.123Z"
  },
  {
    "id": "msg-uuid-2",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "assistant",
    "content": "Refunds are processed within 5-7 business days...",
    "created_at": "2024-01-01T10:00:08.456Z"
  }
]
```

**Frontend** (`/services/chat/src/routes/[session_id]/+page.ts`):
- Fetches session metadata + message history on page load
- Renders chat bubbles (user on right, assistant on left)

**Source**: `/services/internal-api/api/routers/messages.py`

---

## Database Schema

### chatbot_sessions Table

```sql
CREATE TABLE chatbot_sessions (
  id UUID PRIMARY KEY,
  collections TEXT[],        -- Qdrant collections to search (array)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Purpose**: Store session metadata (which collections are included in this chat)

**Example**:
```
id                                   | collections      | created_at
-------------------------------------+------------------+----------------------------
550e8400-e29b-41d4-a716-446655440000 | {default}        | 2024-01-01 10:00:00+00
550e8400-e29b-41d4-a716-446655440001 | {default,finance} | 2024-01-01 11:00:00+00
```

### chat_messages Table

```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES chatbot_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,                -- "user" or "assistant"
  content TEXT NOT NULL,             -- Message body
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Purpose**: Store all messages in a session, ordered by time

**Cascade delete**: When a session is deleted, all its messages are deleted

**Example**:
```
id                                   | session_id                           | role      | content                     | created_at
-------------------------------------+--------------------------------------+-----------+-----------------------------+----------------------------
msg-uuid-1                           | 550e8400-e29b-41d4-a716-446655440000 | user      | What is the refund policy?  | 2024-01-01 10:00:05+00
msg-uuid-2                           | 550e8400-e29b-41d4-a716-446655440000 | assistant | Refunds are processed...    | 2024-01-01 10:00:08+00
msg-uuid-3                           | 550e8400-e29b-41d4-a716-446655440000 | user      | How long does it take?      | 2024-01-01 10:00:10+00
msg-uuid-4                           | 550e8400-e29b-41d4-a716-446655440000 | assistant | It typically takes 5-7 days | 2024-01-01 10:00:13+00
```

---

## Key Concepts

### Session as Context Container

A **session** is a unit of conversation tied to a specific set of Qdrant collections.

**Use case**:
- Session 1: `collections=["default"]` (search general docs)
- Session 2: `collections=["finance-docs"]` (search financial docs)
- Session 3: `collections=["default", "finance-docs"]` (search both)

**Implication**: Users can have parallel conversations against different document sets without cross-contamination.

### One-to-Many Relationship

- One session has many messages
- Messages are immutable (no edit/delete endpoints)
- Session is immutable once created

### Ordering & Pagination

Messages are queried ordered by `created_at ASC` (oldest first).

**Current behavior**: Always return all messages for a session

**Future consideration**: Add pagination (limit/offset) for large conversations

---

## Multi-Turn Conversation Example

**Session**: "Finance Q&A" (collections: ["finance-docs"])

```
Turn 1:
  User:      "What's our revenue target for 2024?"
  Assistant: "Our Q1-Q4 targets are $5M, $6M, $7M, $8M respectively."

Turn 2:
  User:      "What about expenses?"
  Assistant: "Operating expenses are budgeted at 40% of revenue..."

Turn 3:
  User:      "Can you summarize the profit projections?"
  Assistant: "Based on the targets and expenses, projected net profit is..."
```

**Database**:
```
chatbot_sessions:
  id: session-uuid
  collections: ["finance-docs"]
  created_at: 2024-01-01 10:00:00

chat_messages:
  [4 messages, alternating user/assistant, each saved with role + content + timestamp]
```

**Context flow**:
- Each LLM call includes only the user's current message (not full history)
- LLM generates answer based on query + Qdrant search results
- History is stored for user to review, not replayed to LLM

**Note**: Future versions could implement LLM context window management to send conversation history to the LLM for improved context retention.

---

## Frontend Integration

### Chat UI (`/services/chat/src/routes/[session_id]/+page.svelte`)

1. On mount: Load session metadata + message history
2. Render messages as chat bubbles (user right, assistant left)
3. Input form at bottom
4. On send:
   - POST user message to internal-api
   - POST query to main api (with generate=true)
   - POST assistant response to internal-api
   - Append both to UI

### Session List (`/services/chat/src/routes/+layout.svelte`)

1. List all sessions (or load from external session management)
2. Click to open session (navigate to `[session_id]`)
3. Create new session (POST to internal-api, navigate to new session)

---

## Error Handling

### Session Not Found

**Symptom**: GET or POST to `/internal-api/sessions/{session_id}/messages` returns 404

**Cause**: Session ID doesn't exist or was already deleted

**Fix**: Create a new session before sending messages

---

### LLM Generation Error

**Symptom**: Message is saved but no assistant response is generated

**Cause**: Ollama error during query (see [Query Workflows](./query.md) for details)

**Frontend behavior**: Display error toast, let user retry or continue

---

### Database Connection Error

**Symptom**: Internal API returns 500 on message endpoints

**Cause**: PostgreSQL offline or connection pool exhausted

**Fix**:
```bash
docker-compose restart postgres
docker-compose restart internal-api
```

---

## Performance Considerations

### Message Storage

- PostgreSQL stores message text in JSONB would allow richer structure, but currently plain TEXT
- No indexing on `role` or `content` (sequential scan for history)
- Future: Add partial index on `(session_id, created_at)` for faster pagination

### Query per Turn

- Each user message triggers one query to main API
- Multiple concurrent users each trigger queries (no query batching)
- Ollama is the primary bottleneck (2-10 seconds per turn)

### Scalability

- PostgreSQL can store millions of messages easily
- Session/message retrieval is O(messages per session)
- No hard limit on session or message count

---

## Testing & Debugging

### Manual API Test

```bash
# Create session
SESS_ID=$(curl -X POST http://localhost:8001/sessions \
  -H "Content-Type: application/json" \
  -d '{"collections":["default"]}' | jq -r '.id')

# Send user message
curl -X POST http://localhost:8001/sessions/$SESS_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"Hello"}'

# Get all messages
curl http://localhost:8001/sessions/$SESS_ID/messages
```

### Check Database Directly

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U dcs -d datacontext

# List sessions
SELECT id, collections, created_at FROM chatbot_sessions;

# List messages in a session
SELECT id, role, content, created_at FROM chat_messages
WHERE session_id = '{session_id}'
ORDER BY created_at;
```

### Monitor Internal API

```bash
docker-compose logs -f internal-api
```

---

## Source References

- Internal API entry: `/services/internal-api/api/main.py`
- Sessions router: `/services/internal-api/api/routers/sessions.py`
- Messages router: `/services/internal-api/api/routers/messages.py`
- Database models: `/services/internal-api/api/database.py`
- Chat UI: `/services/chat/src/routes/[session_id]/+page.svelte`
- Chat page loader: `/services/chat/src/routes/[session_id]/+page.ts`
- Query API: `/services/api/api/routers/query.py` (used for LLM generation)
