# FastAPI & SQLite Specification

## Purpose

Define the backend contract for the Local Agent OS using FastAPI and SQLite. This document is normative for API behavior, persistence, retrieval, and context compression.

## Component Map

- API Router: Receives HTTP requests and validates payloads.
- Chat Service: Orchestrates ADK calls, retrieval, and persistence.
- Retrieval Service: Uses deterministic local hash embeddings and fetches relevant context.
- Compression Service: Summarizes long history when context budget is exceeded.
- SQLite Repository: Persists sessions, messages, embeddings, and compression records.
- Observability Layer: Emits structured operation, route, and tool logs for each request stage.

## ADK Flow Integration

### Runtime Wiring

- FastAPI `POST /chat` initializes ADK `Runner` with the root coordinator agent (`AvatarCoordinator`).
- API layer sends user prompt directly to ADK and uses ADK tool telemetry as the primary retrieval/context source.
- Root coordinator delegates to workflow orchestrator (`ConversationOrchestrator`) for standard chat.
- Orchestrator adaptively invokes specialist LLM tools (`AgentTool`) per request intent and context needs.
- `Runner` is configured with `auto_create_session=True` to avoid first-turn missing-session errors.

### Request Lifecycle (`POST /chat`)

1. Validate payload and ensure non-empty `message` under 64 KB.
2. Ensure session row exists in `sessions`.
3. Resolve `allow_sensitive_writes` from request field, metadata hint, or explicit write-intent language.
4. Persist user message to `messages` (with embedding).
5. Run ADK flow through `Runner.run(...)` and collect tool telemetry.
6. Use `search_memory` tool results as primary retrieval payload for API response.
7. If ADK retrieval tool invocation is absent for this turn, run SQLite fallback retrieval (`top_k=5`, `exclude_message_ids` for current user message) for response compatibility.
8. Extract final response event and merge any tool failure notice when required.
9. Persist assistant response to `messages` (with embedding).
10. Compress old uncompressed turns when thresholds are met, and persist summary outputs.
11. Return standardized response envelope.

### State Passing Contract

- Specialist tool outputs are written to shared session state using `output_key`.
- `ResponseComposer` may consume available specialist outputs (`collected_context`, `retrieval_context`) when they are produced.
- Final response text is selected from ADK final events (prefer root final response when present) and returned in API response payload.
- Retrieval payload in API response is sourced from ADK `search_memory` tool telemetry first, then SQLite fallback when telemetry indicates retrieval was not invoked.

## API Contracts

### `GET /health`

Successful response:

```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2026-04-20T00:00:00+00:00"
}
```

### `POST /chat`

Request body:

```json
{
  "user_id": "string",
  "session_id": "string (optional)",
  "message": "string",
  "allow_sensitive_writes": false,
  "metadata": {
    "locale": "zh-TW",
    "channel": "web",
    "allow_sensitive_writes": "true"
  }
}
```

Successful response:

```json
{
  "success": true,
  "session_id": "string",
  "response": "string",
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0
  },
  "retrieval": {
    "hit_count": 0,
    "sources": []
  }
}
```

Validation rules:

- `message` must be non-empty after trim.
- `user_id` is required.
- If `session_id` is missing, server generates one.
- Payload size should remain below 64 KB (UTF-8 bytes).

### `GET /memory`

Query parameters:

- `user_id` (required)
- `session_id` (optional)

Successful response:

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
  "recent_messages": []
}
```

## Error Contract

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

Recommended codes:

- `INVALID_REQUEST` (400)
- `UNAUTHORIZED_PATH` (403)
- `NOT_FOUND` (404)
- `MODEL_RUNTIME_ERROR` (502)
- `INTERNAL_ERROR` (500)

## SQLite Data Model (`Avatar/data/chat.db`)

### `sessions`

- `session_id` TEXT PRIMARY KEY
- `user_id` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### `messages`

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `session_id` TEXT NOT NULL
- `user_id` TEXT NOT NULL
- `role` TEXT NOT NULL
- `content` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `compressed` INTEGER NOT NULL DEFAULT 0

Indexes:

- `idx_messages_session_created` on (`session_id`, `created_at`)
- `idx_messages_user_created` on (`user_id`, `created_at`)

### `embeddings`

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `message_id` INTEGER
- `source_type` TEXT NOT NULL (`message`, `memory`, `summary`)
- `source_ref` TEXT NOT NULL
- `model` TEXT NOT NULL
- `dimensions` INTEGER NOT NULL
- `vector_json` TEXT NOT NULL
- `created_at` TEXT NOT NULL

Indexes:

- `idx_embeddings_source` on (`source_type`, `source_ref`)

### `compressions`

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `session_id` TEXT NOT NULL
- `from_message_id` INTEGER NOT NULL
- `to_message_id` INTEGER NOT NULL
- `summary` TEXT NOT NULL
- `created_at` TEXT NOT NULL

## Retrieval Pipeline

1. Persist user message in `messages`.
2. During ADK execution, `MemoryRetriever` calls `search_memory` to fetch retrieval snippets.
3. `search_memory` computes deterministic local hash embeddings and ranks candidates by cosine similarity.
4. API consumes ADK tool retrieval hits for response metadata.
5. If ADK retrieval tool invocation is absent, API performs SQLite fallback retrieval (default 5, max 12).

## Context Compression Policy

- Trigger when uncompressed message count is at least 24 and total chars exceed 12,000.
- Summarize oldest uncompressed range first (size: `min(max(len(rows)//2, 8), 16)`).
- Persist summary in `compressions`, then persist a `messages` record with role `system`, and write an embedding with `source_type="summary"`.
- Mark compressed raw messages as `compressed = 1` but keep raw data for auditability.

## Concurrency And Transactions

- Each `POST /chat` request executes one explicit SQLite transaction (`BEGIN` to `COMMIT`).
- User/assistant message writes, embeddings, retrieval metadata, and compression writes happen inside the same request transaction.
- On `HTTPException` or `sqlite3.Error`, transaction rolls back and response follows error-envelope contract.
- Avoid long-lived SQLite connections across threads.

## Observability Contract

- API layer logs `operation=%s` with stage/status metadata for `/chat`, `/memory`, and `/health`.
- ADK route decisions are logged as `route_decision=%s`.
- Tool request/response activity is logged as `tool_execution=%s` and `tool_activity=%s`.
- Successful commits emit `chat_persisted=%s` with effective `db_path`, `session_id`, and message ids.

## Acceptance Criteria

- API responses conform to contract for success and error cases.
- Database schema and indexes are created idempotently.
- Retrieval returns deterministic top-k ordering for identical input.
- Compression triggers and persistence can be validated by integration tests.
- `POST /chat` reflects ADK-tool-first coordinator/orchestrator flow, with SQLite retrieval fallback only for response compatibility.
