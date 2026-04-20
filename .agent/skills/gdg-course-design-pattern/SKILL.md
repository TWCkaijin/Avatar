---
name: gdg-course-design-pattern
description: Defines the Local Agent OS architecture for the "Build with AI" course project, replacing Firebase with FastAPI + SQLite + Markdown memory.
---

# GDG Course Design Pattern

This skill defines the Local Agent OS architecture for the Avatar project under Avatar/. It replaces the old Firebase architecture with a local FastAPI + SQLite + Markdown memory approach and keeps implementation details aligned with the current codebase.

## Scope And Boundaries

- This skill applies to Avatar/ runtime and data flow design, plus documentation updates in .claude/skills/gdg-course-design-pattern.
- Changes must stay within the Local Agent OS pattern and avoid reintroducing Firebase services.
- When requirements are ambiguous, prefer explicit contracts over implicit behavior.
- Keep documentation synchronized with the current implementation in Avatar/app/, Avatar/adk_agents/, Avatar/data/, and Avatar/test/.
- When using path-related commands, use PathLib to point to the Avatar/Avatar subfolder and add that path explicitly.

## Non-Goals

- No Firebase Functions, Firestore, or Firebase Hosting dependencies.
- No remote vector database as the default path.
- No undocumented tool behavior in ADK runtime.

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

- **FastAPI**: Provides /health, /chat, and /memory endpoints with a unified error envelope.
- **SQLite**: Local persistence for sessions/messages/embeddings/compressions with deterministic top-k retrieval.
- **Markdown Memory**: Local files (identity.md, soul.md, startup.md, master.md, memory.md) acting as context and durable memory.
- **Google ADK**: Root coordinator + orchestrator + specialist LLM-as-tool graph, with native ADK adapter at Avatar/adk_agents/avatar/agent.py (official docs: https://adk.dev/).
- **Model + Retrieval**: Default agent model is gemini-3-flash-preview; retrieval uses local deterministic hash embeddings (EMBEDDING_MODEL_NAME=local-hash-embedding-v1 by default).

## Critical Implementation Notes

- Runtime source of truth is under `Avatar/Avatar/`; validate docs against `Avatar/Avatar/app/*.py` and `Avatar/Avatar/test/*.py`.
- All `LlmAgent` nodes must share `generate_content_config` with:
  - `automatic_function_calling.disable=true`
  - `tool_config.include_server_side_tool_invocations=true`
  This is required to avoid ADK runtime `400 INVALID_ARGUMENT` with built-in tools.
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

1. Read references/env-setup.md for local setup, paths, and runtime commands.
2. Read references/fastapi-sqlite-spec.md for API, database, retrieval, and compression flow.
3. Read references/adk-spec.md for agent lifecycle, graph, and tool contracts.
4. Read references/memory-system-spec.md for markdown file schemas and write policies.
5. Read references/identity-spec.md for baseline memory file templates and default content.
6. Read references/testing-spec.md for test matrix and quality gates.
7. Read references/change-log.md for architecture/spec evolution history.

## Definition Of Done For Planning

- Every component has explicit input/output contracts.
- Failure modes and error codes are documented.
- Data schemas and index strategies are defined.
- Test strategy maps to each component and includes acceptance criteria.
- Documentation paths and runtime paths are consistent with the current Avatar/ folder layout.

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
  - POST /chat, GET /memory, and GET /health contracts fully implemented.
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
