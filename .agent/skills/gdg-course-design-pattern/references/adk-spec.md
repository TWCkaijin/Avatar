# Google ADK Specification

Official References:
- https://adk.dev/
- https://adk.dev/docs/

This document defines runtime behavior and tool contracts for the ADK-based Local Agent OS.

## Canonical Agent Graph

```text
AvatarCoordinator (LlmAgent, root; uses AgentTool routing)
├── ConversationOrchestrator (LlmAgent, adaptive workflow orchestrator; specialists exposed as AgentTool)
│   ├── ContextCollector (LlmAgent)
│   ├── MemoryRetriever (LlmAgent)
│   └── ResponseComposer (LlmAgent)
└── MemoryMaintenanceAgent (LlmAgent)
```

### Graph Semantics

- `AvatarCoordinator` is the only root agent mounted into `Runner`.
- `ConversationOrchestrator` adaptively decides which specialist tools (LLM-as-tool via `AgentTool`) to call per request.
- `ResponseComposer` is always used for final response composition.
- `MemoryMaintenanceAgent` is a specialist route for explicit memory updates.
- Coordinator-to-specialist dispatch uses ADK `AgentTool` (LLM-as-tool pattern).
- Specialist communication is done through ADK tool outputs (`output_key`) and optional session state metadata.

## Runtime Architecture

- Agent runtime: Google ADK `Agent` + `Runner`.
- Model default: `gemini-3-flash-preview`.
- Session service: in-memory for runtime control, with durable conversation state in SQLite.

## ADK Native Adapter Contract

- ADK Web/CLI auto-discovery entrypoint: `Avatar/adk_agents/avatar/agent.py`.
- Adapter must expose `root_agent` at package import time (`Avatar/adk_agents/avatar/__init__.py`).
- Adapter import path must resolve from injected project root (`from app.agent import create_root_agent`).
- Adapter bootstrap must avoid path assumptions that require `Avatar.app.*` module prefix.

## ADK Types And Usage Rules

- Use `LlmAgent` for natural-language reasoning roles.
- Use `LlmAgent` as workflow orchestrator when request-specific adaptive routing is needed.
- Prefer `AgentTool(agent=<llm_agent>)` when a specialist should be dynamically callable as a tool.
- Keep specialist names/descriptions explicit so tool selection remains stable.

## Agent Initialization Sequence

1. Load `identity.md`, `soul.md`, and `master.md`.
2. Build root instruction from identity-first precedence (`identity -> soul -> master`).
3. Construct specialist agents (`ContextCollector`, `MemoryRetriever`, `ResponseComposer`, `MemoryMaintenanceAgent`).
4. Wrap specialists with `AgentTool` for dynamic invocation where needed.
5. Construct workflow orchestrator (`ConversationOrchestrator`) with adaptive specialist-tool routing policy.
6. Construct root coordinator (`AvatarCoordinator`) with top-level routing tools.
7. Register toolset with guardrails.
8. Initialize `Runner` with app metadata and `auto_create_session=True`.
9. On each request, host runtime passes the user message directly to ADK; specialists gather context via ADK tools (`load_memory`, `search_memory`, `read_file`) as first priority.

## Agent Flow (Per Request)

1. User message enters root coordinator.
2. Coordinator routes standard conversation to `ConversationOrchestrator` using AgentTool call.
3. `ConversationOrchestrator` adaptively invokes `ContextCollector`, `MemoryRetriever`, both, or only `ResponseComposer` as specialist tools based on request needs.
4. Called specialists produce scoped outputs via `output_key` for downstream synthesis.
5. `ResponseComposer` synthesizes final response from available specialist outputs and ADK-native tool context.
6. Final response is returned to API layer and persisted to SQLite.
7. For explicit memory update intents, coordinator routes to `MemoryMaintenanceAgent` via AgentTool call.

## Instruction Composition Rule

Final instruction precedence:

1. Identity hard constraints
2. Soul values and style
3. Master profile memory
4. Startup run context
5. Session-local operational hints and retrieved snippets

Lower-priority layers must not override higher-priority constraints.

## Tool Contracts

### `read_file(path: str) -> str`

- Reads UTF-8 content from allowed local paths.
- Returns clear error text on not found or forbidden paths.

### `write_file(path: str, content: str) -> str`

- Overwrites existing file atomically.
- Reserved files (`identity.md`, `soul.md`) are writable by default.
- Optional strict mode: when `STRICT_SENSITIVE_WRITE_GUARD=true`, reserved-file writes require explicit approval (for example `allow_sensitive_writes=true` or a clear user write-intent request).

### `append_file(path: str, content: str) -> str`

- Appends content with newline normalization.
- Preferred for `memory.md` event logs.

### `create_file(path: str, content: str) -> str`

- Creates file only if absent.
- Returns deterministic conflict message when file exists.

### `search_memory(query: str) -> str`

- Embeds query and retrieves top-k relevant context from SQLite-backed vector records.
- Response format should include short snippets and source references.

### Tool Registration Policy By Agent

- `AvatarCoordinator`: `preload_memory`, `AgentTool(ConversationOrchestrator)`, `AgentTool(MemoryMaintenanceAgent)`
- `ConversationOrchestrator`: `AgentTool(ContextCollector)`, `AgentTool(MemoryRetriever)`, `AgentTool(ResponseComposer)`
- `ContextCollector`: `load_memory`, `read_runtime_context` (runtime hints optional)
- `MemoryRetriever`: `search_memory`, `load_memory`
- `ResponseComposer`: `load_memory`, `read_runtime_context`, `read_file`, `write_file`, `append_file`, `create_file`
- `MemoryMaintenanceAgent`: `read_file`, `write_file`, `append_file`, `create_file`

### Memory File Purpose Routing

- `Avatar/data/identity.md`: role identity and character settings requested by user.
- `Avatar/data/master.md`: durable memory about the user profile and preferences.
- `Avatar/data/memory.md`: user-requested memory entries and other important durable facts.
- `Avatar/data/soul.md`: assistant personality principles and reflection notes.

When a user request explicitly asks for role/personality/profile memory updates, the responder should target the file that matches this purpose map instead of defaulting all writes to `Avatar/data/memory.md`.

## Tool Guardrails

- Allowed path roots: `Avatar/data/` and approved subdirectories.
- Disallow traversal (`..`) and absolute paths outside workspace.
- Maximum read/write size per call should be bounded.
- All tool calls (`read_file`, `write_file`, `append_file`, `create_file`, `search_memory`) must emit structured request/response logs with category, status, and operation metadata.
- File-mutation logs must include target path and write-byte metadata when available.
- Memory-retrieval logs must include query-size and hit-count metadata.
- Terminal operations (if enabled via toolset) must emit structured execution logs with status and command details.
- Tool calls must be logged with timestamp, tool name, and status.

## Error Handling

Standard tool error categories:

- `TOOL_VALIDATION_ERROR`
- `TOOL_PERMISSION_DENIED`
- `TOOL_IO_ERROR`
- `TOOL_RUNTIME_ERROR`

Agent behavior on tool failure:

1. Surface concise failure reason.
2. Avoid fabricating tool output.
3. Retry only when failure is transient and safe.
4. If any `TOOL_*` failure is observed, the final assistant response must explicitly state that corresponding operations were not completed.

## Model And Generation Policy

- Default generation model: `gemini-3-flash-preview`.
- Embedding model defaults to local deterministic hash embedding (`local-hash-embedding-v1`) and is persisted in `embeddings.model` metadata.
- Temperature and max output tokens should be configurable but bounded.

## Observability

- Capture per-request metadata: request id, session id, tool call count, latency.
- Keep structured logs for audit and debugging.
- Log selected route (`orchestrator` or `memory_maintenance`) per request.
- Log workflow stage completion (`context_collect`, `retrieve`, `compose`) for stages that were actually invoked.
- Log tool activity records at request/response phases for `file_read`, `file_mutation`, `memory_retrieval`, and terminal categories.
- Log API operation stages for `/chat` transaction lifecycle (`request_received`, `ensure_session`, `persist_*`, `retrieve_context`, `invoke_agent`, `compress_context`, `transaction commit/rollback`, `response_ready`).
- Log `/memory` operation stages (`request_received`, `fetch_messages`, `read_memory_files`).

## Acceptance Criteria

- Agent initialization is deterministic and reproducible.
- Tool calls enforce path and size boundaries.
- Failures are reported with actionable messages.
- Retrieval and generation pipeline can be validated in integration tests.
- Agent graph includes root coordinator + workflow orchestrator + specialist sub-agents.
