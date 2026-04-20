---
name: gdg-course-design-pattern
description: Comprehensive implementation blueprint for recreating the Avatar Local Agent OS with FastAPI + SQLite + Markdown memory + Google ADK multi-agent orchestration.
---

# GDG Course Design Pattern

This skill is a full reconstruction guide for the Avatar Local Agent OS under `Avatar/`.

Use it when you want an LLM agent to build or refactor a project so it behaves like the current Avatar implementation, without depending on Firebase services.

The intent is reproducibility:

- Same core architecture
- Same API and persistence contracts
- Same ADK orchestration pattern
- Same safety and observability behavior
- Same test-driven verification gates

## Scope And Boundaries

- This skill applies to Avatar runtime and data flow design, plus documentation updates in `.agent/skills/gdg-course-design-pattern`.
- Changes must stay within the Local Agent OS pattern and avoid reintroducing Firebase services.
- When requirements are ambiguous, prefer explicit contracts over implicit behavior.
- Keep documentation synchronized with the current implementation in Avatar/app/, Avatar/adk_agents/, Avatar/data/, and Avatar/test/.
- When using path-related commands, use PathLib to point to the Avatar/Avatar subfolder and add that path explicitly.

## What This Skill Must Produce

When this skill is invoked to implement or regenerate the project, the agent should deliver:

1. A runnable FastAPI service with deterministic contracts.
2. Local SQLite persistence and deterministic embedding retrieval behavior.
3. ADK multi-agent graph with LLM-as-tool orchestration.
4. Local markdown memory files and safe write behavior.
5. Local skill lifecycle tools under `Avatar/data/skills`.
6. Passing automated tests in `Avatar/test`.
7. Updated documentation and change-log aligned with the actual code.

## Non-Goals

- No Firebase Functions, Firestore, or Firebase Hosting dependencies.
- No remote vector database as the default path.
- No undocumented tool behavior in ADK runtime.

## Source-Of-Truth Priority (Critical)

When documentation and code disagree, follow this strict priority order:

1. Runtime code in `Avatar/app/*.py`
2. Tests in `Avatar/test/*.py`
3. ADK adapter in `Avatar/adk_agents/avatar/agent.py`
4. Reference docs under `.agent/skills/gdg-course-design-pattern/references/*.md`
5. README files
6. Historical notes in `references/change-log.md`

Do not preserve stale documentation behavior if it conflicts with runtime code and tests.

## ADK Documentation Requirement

- Before modifying ADK-related code (agent graph, tools, runner/session/memory integration), read the official ADK documentation first: https://adk.dev/
- If ADK provides an equivalent native method, prioritize the ADK method over manual host-side context composition or flow orchestration.

## Current Workspace Snapshot

```text
<repo-root>/
  pyproject.toml
  requirements.txt
  README.md
  Avatar/
    README.md
    app/
      main.py
      agent.py
      retrieval.py
    adk_agents/
      avatar/
        __init__.py
        agent.py
    data/
      identity.md
      soul.md
      startup.md
      master.md
      memory.md
      chat.db
    test/
      test_agent.py
      test_main.py
```

## Architecture Overview

- **FastAPI**: Provides `/health`, `/chat`, and `/memory` endpoints with a unified error envelope.
- **SQLite**: Local persistence for sessions/messages/embeddings/compressions with deterministic top-k retrieval.
- **Markdown Memory**: Local files (identity.md, soul.md, startup.md, master.md, memory.md) acting as context and durable memory.
- **Google ADK**: Root coordinator + orchestrator + specialist LLM-as-tool graph, with native ADK adapter at Avatar/adk_agents/avatar/agent.py (official docs: https://adk.dev/).
- **Model + Retrieval**: Default agent model is gemini-3-flash-preview; retrieval uses local deterministic hash embeddings (EMBEDDING_MODEL_NAME=local-hash-embedding-v1 by default).

## Canonical Contracts (Must Match)

### API Contract (Core Profile)

Mandatory routes:

- `GET /health`
- `POST /chat`
- `GET /memory`

Mandatory response style:

- Success: `{"success": true, ...}`
- Error: `{"success": false, "error": {"code": ..., "message": ..., "details": {...}}}`

Mandatory request guardrails:

- `message` is required for `/chat`
- Max UTF-8 payload size: 64 KB (`MAX_MESSAGE_BYTES = 64 * 1024`)
- CORS is configurable via env (`CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS`)

### SQLite Contract

Must create and maintain these tables idempotently:

- `sessions`
- `messages`
- `embeddings`
- `compressions`

Must include these behaviors:

- Persist user + assistant messages in one request lifecycle.
- Persist embeddings for searchable sources.
- Trigger context compression when thresholds are reached.

Compression thresholds (current default behavior):

- `COMPRESSION_MIN_MESSAGES = 24`
- `COMPRESSION_SOFT_CHAR_THRESHOLD = 12000`

### Retrieval Contract

- Tool-first retrieval: prefer ADK tool telemetry (`search_memory`) as retrieval source.
- Fallback retrieval: use SQLite top-k retrieval when ADK retrieval tool was not invoked in the turn.
- API response must always return stable retrieval metadata shape:
  - `retrieval.hit_count`
  - `retrieval.sources[]` with `source_type`, `source_ref`, `score`

### ADK Agent Graph Contract

The graph must preserve this shape:

- Root: `AvatarCoordinator`
- Root tools include:
  - `preload_memory`
  - `AgentTool(ConversationOrchestrator)`
  - `AgentTool(MemoryMaintenanceAgent)`
  - `google_search`
- `ConversationOrchestrator` tools include:
  - `AgentTool(ContextCollector)`
  - `AgentTool(MemoryRetriever)`
  - `AgentTool(ResponseComposer)`
  - `AgentTool(SequentialFlowTemplate)`
  - `AgentTool(ParallelFlowTemplate)`
  - `AgentTool(LoopFlowTemplate)`
  - `google_search`

### ADK Generate Config Contract (Hard Requirement)

All LlmAgent nodes must share the same `GenerateContentConfig` semantics:

- `automatic_function_calling.disable = true`
- `tool_config.include_server_side_tool_invocations = true`

This prevents ADK runtime incompatibility issues (for example 400 invalid argument cases with built-in tools).

### Tooling And Safety Contract

- Local file tools are restricted to allowed workspace/data scope.
- Sensitive memory files (`identity.md`, `soul.md`) follow strict-guard behavior:
  - default allows writes unless strict mode is enabled
  - strict mode enabled by `STRICT_SENSITIVE_WRITE_GUARD=true`
- Local skill lifecycle tools must exist and remain operational:
  - `list_skills`
  - `read_skill`
  - `create_skill`
  - `execute_skill`

### Observability Contract

Structured logs must remain stable:

- `operation=%s` for route lifecycle events
- `route_decision=%s` for ADK route selection metadata
- `tool_execution=%s` and `tool_activity=%s` for tool-level logs
- `chat_persisted=%s` on commit success

## Critical Implementation Notes

- Runtime source of truth is under `Avatar/Avatar/`; validate docs against `Avatar/Avatar/app/*.py` and `Avatar/Avatar/test/*.py`.
- Root instruction composition currently inlines `identity.md`, `soul.md`, and `master.md`; `startup.md` is treated as runtime/session guidance consumed through tool flow when needed.
- Local skill lifecycle tools (`list_skills`, `read_skill`, `create_skill`, `execute_skill`) are production contracts and must remain documented in ADK/tool specs.
- Keep tool observability schema stable (`tool_execution`, `tool_activity`, `route_decision`, `chat_persisted`) when introducing new tools or categories.
- Environment key compatibility rule:
  - prefer `GOOGLE_API_KEY`
  - allow `GEMINI_API_KEY` fallback
  - if both are set, `GOOGLE_API_KEY` takes precedence.

## Component Responsibilities

- API Layer (Avatar/app/main.py): Input validation, error mapping, CORS, response contract consistency, transaction lifecycle logging.
- Agent Runtime (Avatar/app/agent.py): ADK graph construction, instruction precedence, tool invocation, path guardrails, runtime route/tool logs.
- Retrieval Layer (Avatar/app/retrieval.py): Deterministic hash embeddings, cosine similarity ranking, top-k retrieval, embedding persistence helpers.
- Memory Layer (Avatar/data/\*.md): Durable local memory contracts and purpose-based routing (identity/master/memory/soul).
- Adapter Layer (Avatar/adk_agents/avatar/agent.py): ADK web/CLI auto-discovery root agent export.
- Test Layer (Avatar/test/\*.py): Unit/integration/contract checks for API shape, agent graph, write guards, retrieval fallback, and observability.

## Spec Reading Order

1. Read `references/env-setup.md` for local setup, paths, and runtime commands.
2. Read `references/fastapi-sqlite-spec.md` for API, database, retrieval, and compression flow.
3. Read `references/adk-spec.md` for agent lifecycle, graph, and tool contracts.
4. Read `references/memory-system-spec.md` for markdown file schemas and write policies.
5. Read `references/identity-spec.md` for baseline memory file templates and default content.
6. Read `references/testing-spec.md` for test matrix and quality gates.
7. Read `references/change-log.md` for architecture/spec evolution history.
8. Re-validate all decisions against current code/tests before finalizing changes.

## Definition Of Done For Planning

- Every component has explicit input/output contracts.
- Failure modes and error codes are documented.
- Data schemas and index strategies are defined.
- Test strategy maps to each component and includes acceptance criteria.
- Documentation paths and runtime paths are consistent with the current Avatar/ folder layout.

## Rebuild Playbook (For Any LLM Agent)

Follow this sequence exactly to recreate the project reliably.

### Step 0: Baseline Discovery

- Confirm project tree and entry points.
- Confirm existing API routes and tests.
- Confirm env var usage in runtime code.
- Identify stale docs before coding.

### Step 1: Foundation Bootstrap

- Ensure `Avatar/data/` exists.
- Ensure baseline markdown files exist:
  - `identity.md`
  - `soul.md`
  - `startup.md`
  - `master.md`
  - `memory.md`
- Ensure `Avatar/data/skills/` exists.

### Step 2: Persistence Layer

- Implement idempotent schema creation for all required tables and indexes.
- Keep transaction boundaries explicit in `POST /chat`.
- Guarantee rollback behavior on model/db failures.

### Step 3: API Layer

- Implement `/health`, `/chat`, `/memory` contracts first.
- Enforce payload validation and 64 KB UTF-8 limit on chat message.
- Keep standardized error envelope in all failure paths.

### Step 4: ADK Runtime Layer

- Build root + orchestrator + specialists + template tools graph.
- Ensure all LlmAgent nodes share the required generate-content config.
- Keep `Runner(... auto_create_session=True)` to avoid first-turn session failures.

### Step 5: Tool And Guardrail Layer

- Implement file tools with strict path restrictions.
- Implement sensitive write approval logic (strict mode only when enabled).
- Implement local skill lifecycle tools and bounded execution timeout.

### Step 6: Retrieval And Compression

- Integrate ADK retrieval telemetry first.
- Fallback to SQLite retrieval when ADK retrieval not invoked.
- Keep deterministic compression policy and summary persistence.

### Step 7: Logging And Observability

- Add structured operation logs at each API lifecycle stage.
- Add route decision and tool activity logs.
- Add commit/persist log after successful transaction.

### Step 8: Test Gate

Minimum required checks before declaring completion:

- Route contract tests pass.
- Agent graph shape tests pass.
- Retrieval fallback behavior tests pass.
- Logging/observability tests pass.
- Local skill lifecycle tests pass.

Recommended command set:

```bash
PYTHONPATH=. uv run pytest Avatar/test/test_agent.py Avatar/test/test_main.py -q
PYTHONPATH=. .venv/bin/python -m pytest -q
```

### Step 9: Documentation Sync Gate

After code changes, update these files if behavior changes:

- `.agent/skills/gdg-course-design-pattern/SKILL.md`
- `.agent/skills/gdg-course-design-pattern/references/adk-spec.md`
- `.agent/skills/gdg-course-design-pattern/references/fastapi-sqlite-spec.md`
- `.agent/skills/gdg-course-design-pattern/references/env-setup.md`
- `.agent/skills/gdg-course-design-pattern/references/memory-system-spec.md`
- `.agent/skills/gdg-course-design-pattern/references/testing-spec.md`
- `.agent/skills/gdg-course-design-pattern/references/change-log.md`

## Core Profile vs Extension Profile

Core profile (must implement unless user explicitly requests otherwise):

- `/health`
- `/chat`
- `/memory`
- FastAPI + SQLite + Markdown memory + ADK graph contracts above

Extension profile (only when explicitly requested, and must include tests/docs updates):

- Additional non-core routes
- Alternate retrieval sources
- Additional synthesis/output modalities

Do not silently add extension features to core profile.

## Anti-Patterns To Reject

- Reintroducing Firebase architecture.
- Bypassing unified error envelope.
- Diverging from ADK shared tool config requirements.
- Returning retrieval payloads without stable `source_type/source_ref/score` fields.
- Writing outside allowed data directories from tools.
- Updating docs without corresponding runtime/test verification.

## Final Verification Checklist

Before final handoff, an agent must verify all items:

- API routes and payload contracts match runtime behavior.
- Agent graph shape matches test assertions.
- Shared ADK generate config is applied to all LlmAgent nodes.
- Retrieval uses ADK tool-first with SQLite fallback.
- Compression logic and thresholds are deterministic.
- Logging keys remain stable (`operation`, `route_decision`, `tool_execution`, `tool_activity`, `chat_persisted`).
- Tests pass locally.
- References and change-log are synchronized.

## Suggested Agent Handoff Format

When completing work with this skill, provide:

1. What changed (code + docs)
2. Which contracts were preserved or updated
3. Which tests were executed and results
4. Any residual risks or deferred items

## Implementation Phases By Component

### Phase 1: Foundation

- Components: Environment, Data Directory, Baseline Memory Files.
- Primary spec: references/env-setup.md and references/memory-system-spec.md.
- Deliverables:
  - Reproducible local runtime.
  - Required Avatar/data/\*.md files with valid structure.
  - SQLite bootstrap and migration-safe initialization.

### Phase 2: API And Persistence

- Components: FastAPI routes, SQLite schema, request/response contracts.
- Primary spec: references/fastapi-sqlite-spec.md.
- Deliverables:
  - `POST /chat`, `GET /memory`, and `GET /health` contracts fully implemented.
  - Standardized error envelope.
  - Idempotent schema/index creation.

### Phase 3: Agent Runtime And Tools

- Components: ADK agent, tool registry, instruction composition.
- Primary spec: references/adk-spec.md.
- Deliverables:
  - Guardrailed file tools.
  - Deterministic initialization flow.
  - Retrieval tool integrated with persistence layer and ADK-tool-first behavior.

### Phase 4: Retrieval And Compression

- Components: Embedding write path, top-k retrieval, context compression loop.
- Primary spec: references/fastapi-sqlite-spec.md.
- Deliverables:
  - Retrieval context selection with stable ranking.
  - Compression trigger and summary persistence.
  - Token budget protection behavior.

### Phase 5: Verification And Hardening

- Components: Unit tests, integration tests, contract tests, quality gates.
- Primary spec: references/testing-spec.md.
- Deliverables:
  - Component test matrix coverage.
  - Deterministic mocked model and file I/O tests.
  - Acceptance criteria validated for all layers.

## References

- [Environment Setup](references/env-setup.md)
- [FastAPI & SQLite Spec](references/fastapi-sqlite-spec.md)
- [Memory System Spec](references/memory-system-spec.md)
- [Identity/Data Baseline Spec](references/identity-spec.md)
- [Google ADK Spec](references/adk-spec.md)
- [Testing Spec](references/testing-spec.md)
- [Change Log](references/change-log.md)
