# FastAPI & SQLite Specification

This is the normative backend contract for Avatar Local Agent OS.

## Scope

This document defines:

- API route contracts and validation rules.
- Error-envelope format.
- SQLite schema/index contracts.
- Retrieval and compression policies.
- Request transaction boundaries.
- Route-level observability contracts.

## Runtime Components

- API Router: FastAPI endpoints and exception handlers.
- Chat Service: request validation, ADK invocation, persistence lifecycle.
- Retrieval Service: deterministic embedding retrieval and ranking.
- Compression Service: summarization and marker updates for long sessions.
- SQLite Repository: sessions/messages/embeddings/compressions.

## API Route Surface (Core Profile)

- `GET /health`
- `POST /chat`
- `GET /memory`

No other route is required by the current core profile.

## Unified Error Envelope

All non-2xx responses must follow:

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "human readable message",
    "details": {}
  }
}
```

Current status-to-code mapping:

- `400 -> INVALID_REQUEST`
- `403 -> UNAUTHORIZED_PATH`
- `404 -> NOT_FOUND`
- `500 -> INTERNAL_ERROR`
- `502 -> MODEL_RUNTIME_ERROR`

## Endpoint Contracts

### `GET /health`

Response (200):

```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2026-04-21T00:00:00+00:00"
}
```

Behavior:

- Emits operation log `health.check` with `success` status.

### `POST /chat`

Request schema:

```json
{
  "user_id": "string",
  "message": "string",
  "session_id": "string (optional)",
  "metadata": {
    "locale": "zh-TW",
    "channel": "web",
    "allow_sensitive_writes": "true"
  },
  "allow_sensitive_writes": false
}
```

Validation rules:

- `user_id`: required, non-empty, max 128 chars.
- `message`: required, non-empty after trim.
- `message` UTF-8 bytes must be `<= 64 KB`.
- `session_id`: optional; server generates `session-<uuidhex>` when absent.

Success response (200):

```json
{
  "success": true,
  "session_id": "session-...",
  "response": "...",
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0
  },
  "retrieval": {
    "hit_count": 0,
    "sources": [
      {
        "source_type": "message",
        "source_ref": "123",
        "score": 0.73
      }
    ]
  }
}
```

### `GET /memory`

Query parameters:

- `user_id` (required)
- `session_id` (optional)

Success response (200):

```json
{
  "success": true,
  "memory_files": {
    "identity": "...",
    "soul": "...",
    "startup": "...",
    "master": "...",
    "memory": "..."
  },
  "recent_messages": [
    {
      "role": "user",
      "content": "...",
      "created_at": "..."
    }
  ]
}
```

Behavior:

- Returns latest messages (descending by id) with limit `RECENT_MESSAGES_LIMIT`.
- Filters by `session_id` when provided; otherwise by `user_id` only.

## Request Lifecycle: `POST /chat`

1. Validate request payload and message size.
2. Resolve `session_id` and sensitive-write approval.
3. Open SQLite connection and start explicit transaction (`BEGIN`).
4. Ensure session row exists/upserts `updated_at`.
5. Persist user message and embedding.
6. Invoke ADK runtime (`_invoke_agent`) with telemetry capture.
7. Determine retrieval source:
   - if ADK `search_memory` invoked -> use ADK telemetry hits
   - else -> run SQLite fallback retrieval (`top_k=5`, exclude current user message id)
8. Persist assistant message and embedding.
9. Attempt context compression when thresholds are met.
10. Commit transaction.
11. Emit persistence log and return success envelope.

Failure behavior:

- ADK runtime error -> 502 `MODEL_RUNTIME_ERROR`.
- SQLite error -> rollback + 500 `INTERNAL_ERROR`.
- HTTPException in flow -> rollback + mapped error envelope.

## SQLite Schema Contract

Database path: `Avatar/data/chat.db` by default, overrideable via `AVATAR_DB_PATH`.

### `sessions`

- `session_id TEXT PRIMARY KEY`
- `user_id TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

Upsert policy:

- insert on first use
- on conflict, update `updated_at`

### `messages`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `session_id TEXT NOT NULL`
- `user_id TEXT NOT NULL`
- `role TEXT NOT NULL`
- `content TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `compressed INTEGER NOT NULL DEFAULT 0`

Indexes:

- `idx_messages_session_created(session_id, created_at)`
- `idx_messages_user_created(user_id, created_at)`

### `embeddings`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `message_id INTEGER`
- `source_type TEXT NOT NULL`
- `source_ref TEXT NOT NULL`
- `model TEXT NOT NULL`
- `dimensions INTEGER NOT NULL`
- `vector_json TEXT NOT NULL`
- `created_at TEXT NOT NULL`

Index:

- `idx_embeddings_source(source_type, source_ref)`

### `compressions`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `session_id TEXT NOT NULL`
- `from_message_id INTEGER NOT NULL`
- `to_message_id INTEGER NOT NULL`
- `summary TEXT NOT NULL`
- `created_at TEXT NOT NULL`

## Embedding & Retrieval Contract

Embedding implementation (`Avatar/app/retrieval.py`):

- Deterministic local hash embeddings (`blake2b`-derived).
- Default dimensions: `64`.
- Runtime bounds: `8..256` via `EMBEDDING_DIMENSIONS`.
- Vectors are normalized.

Retrieval (`retrieve_top_k`) behavior:

- Query is embedded with same deterministic method.
- Scans latest 256 embedding rows.
- Calculates cosine similarity.
- Rounds score to 6 decimals.
- Sorts by:
  1. descending score
  2. `source_type`
  3. `source_ref`
- Returns bounded top-k (`DEFAULT_TOP_K=5`, `MAX_TOP_K=12`).
- Snippet truncation: first 240 chars.

## Compression Contract

Compression trigger conditions:

- Uncompressed message count in session `>= 24`
- Total uncompressed content chars `>= 12000`

Compression behavior:

- Select compress range size: `min(max(len(rows)//2, 8), 16)`
- Build summary from selected messages:
  - each line format: `<role>: <first 140 normalized chars>`
- Insert compression row
- Mark selected messages as `compressed=1`
- Persist summary as system message with embedding (`source_type=summary`, `source_ref=compression:<id>`)

## Sensitive Write Approval Resolution

Input sources considered (priority order):

1. request field `allow_sensitive_writes`
2. explicit natural-language write intent targeting identity/soul
3. `metadata.allow_sensitive_writes` (truthy parsing)

This flag is forwarded into ADK runtime metadata and tool runtime context.

## Observability Contract

Route-level structured logs (`uvicorn.error`):

- `operation=%s`
  - examples: `chat.request_received`, `chat.transaction`, `chat.retrieve_context`, `chat.invoke_agent`, `chat.response_ready`, `memory.fetch_messages`
- `route_decision=%s`
- `tool_activity=%s`
- `chat_persisted=%s`
- `storage_config=%s` (startup)

`chat_persisted` must include:

- `db_path`
- `user_id`
- `session_id`
- `user_message_id`
- `assistant_message_id`

## Acceptance Criteria

- Core routes match this spec and return deterministic envelopes.
- Schema and indexes are idempotent.
- `/chat` transaction lifecycle is atomic and rollback-safe.
- Retrieval source selection follows ADK-tool-first then SQLite fallback.
- Compression writes summary artifacts correctly.
- Structured logs expose enough metadata for postmortem and tracing.
