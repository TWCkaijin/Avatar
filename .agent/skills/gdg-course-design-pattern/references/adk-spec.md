# Google ADK Specification

Official references:

- [ADK Home](https://adk.dev/)
- [ADK Docs](https://adk.dev/docs/)

This document is the runtime contract for the ADK orchestration layer used by Avatar.

## Scope

This spec defines:

- Agent graph topology and routing semantics.
- Shared generation configuration requirements.
- Tool contracts and guardrails.
- Runtime context propagation and failure behavior.
- Structured observability requirements.

This spec does not define API envelopes or SQLite schema details; those belong to `fastapi-sqlite-spec.md`.

## Runtime Constants (Current Implementation)

Defined in `Avatar/app/agent.py`:

- `AGENT_MODEL = "gemini-3-flash-preview"`
- `AGENT_GENERATE_CONTENT_CONFIG`:
  - `automatic_function_calling.disable = true`
  - `tool_config.include_server_side_tool_invocations = true`
- `MAX_FILE_BYTES = 512 * 1024`
- `MAX_LOCAL_SKILLS = 20`
- `SKILL_EXEC_TIMEOUT_SECONDS` default `20`
- `STRICT_SENSITIVE_WRITE_GUARD` default `false`

## Canonical Agent Graph

```text
AvatarCoordinator (LlmAgent, root)
├── ConversationOrchestrator (LlmAgent)
│   ├── ContextCollector (LlmAgent, output_key=collected_context)
│   ├── MemoryRetriever (LlmAgent, output_key=retrieval_context)
│   ├── ResponseComposer (LlmAgent, output_key=final_response)
│   ├── SequentialFlowTemplate (LlmAgent, output_key=sequential_template_result)
│   ├── ParallelFlowTemplate (LlmAgent, output_key=parallel_template_result)
│   └── LoopFlowTemplate (LlmAgent, output_key=loop_template_result)
└── MemoryMaintenanceAgent (LlmAgent, output_key=memory_update_status)
```

## Graph Semantics

- `AvatarCoordinator` is the only root agent mounted in ADK `Runner`.
- Coordinator routes to `ConversationOrchestrator` for normal requests.
- Coordinator routes to `MemoryMaintenanceAgent` for explicit memory-file maintenance intent.
- `ConversationOrchestrator` adaptively calls specialists/templates using `AgentTool`.
- `ResponseComposer` is the final synthesis stage for regular conversation flow.
- All LLM nodes register `google_search` by default.

## Required Shared GenerateContentConfig

Every `LlmAgent` must use the same `AGENT_GENERATE_CONTENT_CONFIG` semantics:

- `automatic_function_calling.disable = true`
- `tool_config.include_server_side_tool_invocations = true`

Rationale:

- Prevents ADK built-in tool incompatibility and runtime 400 errors.
- Ensures consistent tool invocation behavior across root, orchestrator, specialists, and templates.

## Agent Construction Sequence

Current factory sequence (`create_root_agent`):

1. Build system instruction from local files via `load_system_instruction()`.
2. Create orchestrator subgraph via `create_orchestrator_agent()`.
3. Create memory maintenance specialist via `create_memory_maintenance_agent()`.
4. Wrap sub-agents in `AgentTool`.
5. Construct `AvatarCoordinator` with root routing policy.

`load_system_instruction()` composition precedence:

1. `identity.md`
2. `soul.md`
3. `master.md`
4. local skills registry summary
5. memory-file purpose guidance

## Runtime Invocation Contract

Runtime integration in `Avatar/app/main.py::_invoke_agent`:

- `Runner(... auto_create_session=True)` is mandatory.
- Session service: `InMemorySessionService`.
- Memory service: `InMemoryMemoryService`.
- `RunConfig.custom_metadata` must include:
  - `allow_sensitive_writes`
  - `context_strategy = "adk_tool_first"`

Final response selection policy:

1. Prefer root (`AvatarCoordinator`) final text.
2. Fallback to any final text if root text missing.
3. Raise runtime error if only empty finals are emitted.

Tool failure policy in final response:

- If a `TOOL_*` failure is detected and runtime does not crash:
  - prepend a warning notice to final text
  - include failing tool and error reason

## Tool Registration Matrix (Must Match)

- `AvatarCoordinator`:
  - `google_search`
  - `preload_memory`
  - `AgentTool(ConversationOrchestrator)`
  - `AgentTool(MemoryMaintenanceAgent)`

- `ConversationOrchestrator`:
  - `google_search`
  - `AgentTool(ContextCollector)`
  - `AgentTool(MemoryRetriever)`
  - `AgentTool(ResponseComposer)`
  - `AgentTool(SequentialFlowTemplate)`
  - `AgentTool(ParallelFlowTemplate)`
  - `AgentTool(LoopFlowTemplate)`

- `ContextCollector`:
  - `google_search`
  - `load_memory`
  - `read_runtime_context`

- `MemoryRetriever`:
  - `google_search`
  - `search_memory`
  - `load_memory`

- `ResponseComposer`:
  - `google_search`
  - `load_memory`
  - `read_runtime_context`
  - `read_file`
  - `write_file`
  - `append_file`
  - `create_file`
  - `list_skills`
  - `read_skill`
  - `create_skill`
  - `execute_skill`

- `SequentialFlowTemplate` / `ParallelFlowTemplate` / `LoopFlowTemplate`:
  - `google_search`
  - `AgentTool(ContextCollector)`
  - `AgentTool(MemoryRetriever)`
  - `AgentTool(ResponseComposer)`

- `MemoryMaintenanceAgent`:
  - `google_search`
  - `read_file`
  - `write_file`
  - `append_file`
  - `create_file`

## Flow Template Contracts

### SequentialFlowTemplate

- Intent: run agent A then agent B with explicit handoff.
- Expected control fields: `agent_a`, `agent_b`, optional task payload.
- Required output fields:
  - `template`
  - `order`
  - `agent_a_output`
  - `agent_b_output`
  - `final_output`
  - `errors`

### ParallelFlowTemplate

- Intent: run agent A and B as independent branches then merge.
- Expected control fields: `agent_a`, `agent_b`, optional branch payload.
- Required output fields:
  - `template`
  - `branches`
  - `branch_outputs`
  - `merged_output`
  - `errors`

### LoopFlowTemplate

- Intent: run selected flow repeatedly until stop condition or max iteration.
- Expected control fields: `flow_agent`, `stop_condition`, `max_iterations`.
- Required output fields:
  - `template`
  - `iterations`
  - `exit_reason`
  - `final_output`
  - `errors`

## Tool Contracts

### `read_file(path: str) -> str`

- Scope-limited UTF-8 read under allowed data root.
- Fails with `TOOL_IO_ERROR` or `TOOL_PERMISSION_DENIED` style output.
- Rejects oversized reads (`MAX_FILE_BYTES`).

### `write_file(path: str, content: str) -> str`

- Atomic replace write.
- Returns `Success` on success.
- Blocks identity/soul writes when strict guard is enabled without approval.

### `append_file(path: str, content: str) -> str`

- Newline-normalized append.
- Returns `Success` on success.
- Same strict-guard behavior as `write_file`.

### `create_file(path: str, content: str) -> str`

- Create-if-absent only.
- Returns `TOOL_VALIDATION_ERROR: File already exists` when path exists.

### `search_memory(query: str) -> str`

- SQLite-backed top-k retrieval (`retrieve_top_k`).
- Returns JSON array string with: `source_type`, `source_ref`, `score`, `snippet`, `role`.
- Returns `[]` when DB not present.

### `list_skills() -> str`

- Lists local skills from `Avatar/data/skills`.
- Returns JSON array with `name`, `summary`, `path`, `has_entrypoint`, `entrypoint`.

### `read_skill(skill_name: str) -> str`

- Reads `SKILL.md` in a validated skill folder.
- Enforces name pattern and max read-size checks.

### `create_skill(skill_name: str, skill_markdown: str, python_code: str = "") -> str`

- Creates `<skill_name>/SKILL.md` and optional `run.py`.
- Rejects empty markdown and duplicate existing skill directory.

### `execute_skill(skill_name: str, input_json: str = "{}") -> str`

- Executes `run.py` via `sys.executable`.
- Input is passed via stdin and `AVATAR_SKILL_INPUT_JSON`.
- Timeout bounded by `SKILL_EXEC_TIMEOUT_SECONDS`.
- Returns stdout or `"{}"` when empty.

## Skill Registry Contract

Local skills are discovered at `Avatar/data/skills/<skill_name>/SKILL.md`.

- Name regex: `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`
- Max auto-loaded skill count: `MAX_LOCAL_SKILLS`
- Root instruction must include deterministic local skill summary block.
- If no skills exist, root instruction must still include explicit empty notice.

## Memory-File Purpose Routing

The following route guidance is mandatory in responder/memory-maintenance logic:

- `identity.md`: role/persona settings requested by user.
- `master.md`: durable user profile and preferences.
- `memory.md`: user-requested facts, decisions, long-term reminders.
- `soul.md`: assistant personality/reflection principles.

## Tool Guardrails

- Allowed path root: effective `DATA_DIR` only.
- Reject path traversal and out-of-scope absolute paths.
- Use structured tool-execution logs for both request and response phases.
- Sensitive files (`identity.md`, `soul.md`) are blocked only in strict mode without approval.

## Runtime Context Contract

`read_runtime_context(tool_context)` returns JSON with:

- `session_state`: ADK state dictionary
- `runtime_flags`:
  - `user_id`
  - `session_id`
  - `allow_sensitive_writes`

## Error Contract

Tool error families:

- `TOOL_VALIDATION_ERROR`
- `TOOL_PERMISSION_DENIED`
- `TOOL_IO_ERROR`
- `TOOL_RUNTIME_ERROR`

Coordinator behavior on tool failure:

- Record failure in route log.
- Mark route status as `tool_error` (when runtime itself did not crash).
- Surface failure notice in final user-facing text.

## Observability Contract

Required structured logs:

- `route_decision=%s` with:
  - `root_agent`
  - selected root/orchestrator sub-agents
  - response source
  - route status
  - tool failure summary (if any)

- `tool_activity=%s` for parsed function-call/function-response events:
  - category (`file_mutation`, `memory_retrieval`, `terminal_operation`)
  - phase (`request`/`response`)
  - status (`success`/`denied`/`error`)

- `tool_execution=%s` from concrete tool implementations.

## ADK Adapter Contract

File: `Avatar/adk_agents/avatar/agent.py`

- Must add `Avatar/` directory to `sys.path`.
- Must import `create_root_agent` from `app.agent`.
- Must expose `root_agent = create_root_agent()` at import time.

## Acceptance Criteria

- Agent graph and tool matrix match this document and test assertions.
- All LLM nodes share required generate-content config.
- Tool guardrails and strict-write behavior are enforced.
- Local skill lifecycle works end-to-end.
- Route/tool logs provide deterministic auditability.
