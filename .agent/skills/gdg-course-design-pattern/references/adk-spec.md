# Google ADK Specification

Official References:

- [adk.dev](https://adk.dev/)
- [ADK docs](https://adk.dev/docs/)

This document defines runtime behavior and tool contracts for the ADK-based Local Agent OS.

## Canonical Agent Graph

```text
AvatarCoordinator (LlmAgent, root; uses AgentTool routing)
├── ConversationOrchestrator (LlmAgent, adaptive workflow orchestrator; specialists and templates exposed as AgentTool)
│   ├── ContextCollector (LlmAgent)
│   ├── MemoryRetriever (LlmAgent)
│   ├── ResponseComposer (LlmAgent)
│   ├── SequentialFlowTemplate (LlmAgent)
│   ├── ParallelFlowTemplate (LlmAgent)
│   └── LoopFlowTemplate (LlmAgent)
└── MemoryMaintenanceAgent (LlmAgent)
```

### Graph Semantics

- `AvatarCoordinator` is the only root agent mounted into `Runner`.
- `ConversationOrchestrator` adaptively decides which specialist tools (LLM-as-tool via `AgentTool`) to call per request.
- `ResponseComposer` is always used for final response composition.
- `SequentialFlowTemplate` provides ordered two-step flow execution with explicit output handoff (`agent_a_output -> agent_b_input`).
- `ParallelFlowTemplate` provides branch-style execution where `agent_a` and `agent_b` outputs stay isolated before merge.
- `LoopFlowTemplate` provides bounded iterative execution (`max_iterations`) until `stop_condition` is met.
- `MemoryMaintenanceAgent` is a specialist route for explicit memory updates.
- All LlmAgent nodes include `google_search` as a default tool for live web lookup.
- Coordinator-to-specialist dispatch uses ADK `AgentTool` (LLM-as-tool pattern).
- Specialist communication is done through ADK tool outputs (`output_key`) and optional session state metadata.

## Runtime Architecture

- Agent runtime: Google ADK `Agent` + `Runner`.
- Model default: `gemini-3-flash-preview`.
- App name: `avatar`.
- Session service: in-memory for runtime control, with durable conversation state in SQLite.
- Memory service: in-memory ADK memory service used alongside SQLite persistence.

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
4. Construct flow template agents (`SequentialFlowTemplate`, `ParallelFlowTemplate`, `LoopFlowTemplate`).
5. Wrap specialists/templates with `AgentTool` for dynamic invocation where needed.
6. Construct workflow orchestrator (`ConversationOrchestrator`) with adaptive specialist-tool and template-tool routing policy.
7. Construct root coordinator (`AvatarCoordinator`) with top-level routing tools.
8. Register toolset with guardrails (`preload_memory` on root, file/retrieval tools on specialists).
9. Initialize `Runner` with app metadata and `auto_create_session=True`.
10. On each request, host runtime passes the user message directly to ADK; specialists gather context via ADK tools (`load_memory`, `search_memory`, `read_file`) as first priority.

## Agent Flow (Per Request)

1. User message enters root coordinator.
2. Coordinator routes standard conversation to `ConversationOrchestrator` using AgentTool call.
3. `ConversationOrchestrator` adaptively invokes specialists directly, or first invokes one of the template tools when sequential/parallel/loop control is needed.
4. Template tools dispatch specialist calls according to their control semantics and return structured flow outputs.
5. Called specialists/templates produce scoped outputs via `output_key` for downstream synthesis.
6. `ResponseComposer` synthesizes final response from available outputs and ADK-native tool context.
7. Final response is returned to API layer and persisted to SQLite.
8. For explicit memory update intents, coordinator routes to `MemoryMaintenanceAgent` via AgentTool call.

## Instruction Composition Rule

Final instruction precedence:

1. Identity hard constraints
2. Soul values and style
3. Master profile memory
4. Local skills registry and memory-purpose routing guidance
5. Startup/session operational hints and retrieved snippets (via tool flow when needed)

Lower-priority layers must not override higher-priority constraints.
`startup.md` is treated as runtime guidance and is not required to be inlined into the root instruction string every turn.

## Tool Contracts

### `google_search(...) -> ...`

- Performs live web lookup through ADK's Google Search tool.
- Available by default on all LlmAgent nodes in this project.
- Must be used as an evidence source and not as a replacement for explicit file-write success checks.

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

### `list_skills() -> str`

- Lists discovered local skills from `Avatar/data/skills/<skill_name>/SKILL.md`.
- Returns JSON payload containing skill name, summary, path, and executable-entrypoint availability.

### `read_skill(skill_name: str) -> str`

- Reads `Avatar/data/skills/<skill_name>/SKILL.md`.
- Enforces skill-name validation and file-size boundaries.

### `create_skill(skill_name: str, skill_markdown: str, python_code: str = "") -> str`

- Creates a local skill under `Avatar/data/skills/<skill_name>/`.
- Writes `SKILL.md` and optional executable `run.py`.
- Rejects invalid names and duplicate skill folders.

### `execute_skill(skill_name: str, input_json: str = "{}") -> str`

- Executes `Avatar/data/skills/<skill_name>/run.py` with JSON payload.
- Payload is passed through stdin and `AVATAR_SKILL_INPUT_JSON`.
- Returns stdout on success and `TOOL_RUNTIME_ERROR` style messages on failure/timeout.

### Tool Registration Policy By Agent

- `AvatarCoordinator`: `google_search`, `preload_memory`, `AgentTool(ConversationOrchestrator)`, `AgentTool(MemoryMaintenanceAgent)`
- `ConversationOrchestrator`: `google_search`, `AgentTool(ContextCollector)`, `AgentTool(MemoryRetriever)`, `AgentTool(ResponseComposer)`, `AgentTool(SequentialFlowTemplate)`, `AgentTool(ParallelFlowTemplate)`, `AgentTool(LoopFlowTemplate)`
- `ContextCollector`: `google_search`, `load_memory`, `read_runtime_context` (runtime hints optional)
- `MemoryRetriever`: `google_search`, `search_memory`, `load_memory`
- `ResponseComposer`: `google_search`, `load_memory`, `read_runtime_context`, `read_file`, `write_file`, `append_file`, `create_file`, `list_skills`, `read_skill`, `create_skill`, `execute_skill`
- `SequentialFlowTemplate`: `google_search`, `AgentTool(ContextCollector)`, `AgentTool(MemoryRetriever)`, `AgentTool(ResponseComposer)`
- `ParallelFlowTemplate`: `google_search`, `AgentTool(ContextCollector)`, `AgentTool(MemoryRetriever)`, `AgentTool(ResponseComposer)`
- `LoopFlowTemplate`: `google_search`, `AgentTool(ContextCollector)`, `AgentTool(MemoryRetriever)`, `AgentTool(ResponseComposer)`
- `MemoryMaintenanceAgent`: `google_search`, `read_file`, `write_file`, `append_file`, `create_file`

### Local Skill Loading Contract

- Root instruction dynamically loads a concise local-skill registry from `Avatar/data/skills` on agent creation.
- Each skill summary is derived from `SKILL.md` and exposed as planning context for the orchestrator/responder.
- If no local skills exist, the instruction must still include a deterministic "no local skills registered" notice.

### Flow Template Tool Contracts

`SequentialFlowTemplate`

- Purpose: run `agent_a` first, then pass its output to `agent_b`.
- Expected caller parameters: `agent_a`, `agent_b`, optional per-step payload.
- Output contract: `template`, `order`, `agent_a_output`, `agent_b_output`, `final_output`, `errors`.

`ParallelFlowTemplate`

- Purpose: execute `agent_a` and `agent_b` as independent branches, then merge.
- Expected caller parameters: `agent_a`, `agent_b`, optional per-branch payload.
- Output contract: `template`, `branches`, `branch_outputs`, `merged_output`, `errors`.

`LoopFlowTemplate`

- Purpose: repeatedly execute `flow_agent` until condition is met or iteration bound is reached.
- Expected caller parameters: `flow_agent`, `stop_condition`, `max_iterations`, optional loop state payload.
- Output contract: `template`, `iterations`, `exit_reason`, `final_output`, `errors`.

### Memory File Purpose Routing

- `Avatar/data/identity.md`: role identity and character settings requested by user.
- `Avatar/data/master.md`: durable memory about the user profile and preferences.
- `Avatar/data/memory.md`: user-requested memory entries and other important durable facts.
- `Avatar/data/soul.md`: assistant personality principles and reflection notes.

When a user request explicitly asks for role/personality/profile memory updates, the responder should target the file that matches this purpose map instead of defaulting all writes to `Avatar/data/memory.md`.

## Tool Guardrails

- Allowed path roots: effective `DATA_DIR` (defaults to `Avatar/data/`) and approved subdirectories.
- Disallow traversal (`..`) and absolute paths outside workspace.
- Maximum read/write size per call should be bounded.
- All tool calls (`read_file`, `write_file`, `append_file`, `create_file`, `search_memory`) must emit structured request/response logs with category, status, and operation metadata.
- File-mutation logs must include target path and write-byte metadata when available.
- Memory-retrieval logs must include query-size and hit-count metadata.
- Skill-registry logs (`list_skills`, `read_skill`) must include operation status and skill-count/read metadata.
- Skill-mutation logs (`create_skill`) must include creation status and entrypoint creation metadata.
- Skill-execution logs (`execute_skill`) must include execution status, output-size metadata, and timeout/error details when applicable.
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
- All `LlmAgent` nodes must reuse shared `GenerateContentConfig` from `Avatar/app/agent.py` with:
	- `automatic_function_calling.disable=true`
	- `tool_config.include_server_side_tool_invocations=true`
- Reason: built-in tools (for example `google_search`) with function-calling require server-side invocation metadata; without this, runtime may return `400 INVALID_ARGUMENT`.

## Observability

- Capture per-request metadata: request id, session id, tool call count, latency.
- Keep structured logs for audit and debugging.
- Log selected route (`orchestrator` or `memory_maintenance`) per request.
- Log workflow stage completion (`context_collect`, `retrieve`, `compose`) for stages that were actually invoked.
- Log tool activity records at request/response phases for `file_read`, `file_mutation`, `memory_retrieval`, and terminal categories.
- Log API operation stages for `/chat` transaction lifecycle (`request_received`, `ensure_session`, `persist_*`, `retrieve_context`, `invoke_agent`, `compress_context`, `transaction commit/rollback`, `response_ready`).
- Log `/memory` operation stages (`request_received`, `fetch_messages`, `read_memory_files`).
- Log storage bootstrap as `storage_config` and successful persistence as `chat_persisted`.

## Acceptance Criteria

- Agent initialization is deterministic and reproducible.
- Tool calls enforce path and size boundaries.
- Failures are reported with actionable messages.
- Retrieval and generation pipeline can be validated in integration tests.
- Agent graph includes root coordinator + workflow orchestrator + specialist sub-agents + reusable flow templates.
- Local skill lifecycle (create/list/read/execute) is available through ADK tools and constrained to `Avatar/data/skills`.
