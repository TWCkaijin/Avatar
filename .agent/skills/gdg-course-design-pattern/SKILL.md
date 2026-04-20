---
name: gdg-course-design-pattern
description: Defines the Local Agent OS architecture for the "Build with AI" course project, replacing Firebase with FastAPI + SQLite + Markdown memory.
---

# GDG Course Design Pattern

This skill defines the Local Agent OS architecture for the "Build with AI" course project. It replaces the old Firebase architecture with a local FastAPI + SQLite + Markdown memory approach.

## Scope And Boundaries

- This skill applies only to local architecture and implementation planning.
- Changes must stay within the Local Agent OS pattern and avoid reintroducing Firebase services.
- When requirements are ambiguous, prefer explicit contracts over implicit behavior.

## Non-Goals

- No Firebase Functions, Firestore, or Firebase Hosting dependencies.
- No remote vector database as the default path.
- No undocumented tool behavior in ADK runtime.

## ADK Documentation Requirement

- Before modifying ADK-related code (agent graph, tools, runner/session/memory integration), read the official ADK documentation first: https://adk.dev/
- If ADK provides an equivalent native method, prioritize the ADK method over manual host-side context composition or flow orchestration.

## Architecture Overview

- **FastAPI**: Provides `/chat` and `/memory` endpoints.
- **SQLite**: Local persistence for sessions/messages/embeddings/compressions with deterministic top-k retrieval.
- **Markdown Memory**: Local files (`identity.md`, `soul.md`, `startup.md`, `master.md`, `memory.md`) acting as context and durable memory.
- **Google ADK**: Root coordinator + orchestrator + specialist sub-agents, with native ADK adapter at `Avatar/adk_agents/avatar/agent.py` (official docs: https://adk.dev/).
- **Model + Retrieval**: Default agent model is `gemini-3-flash-preview`; retrieval uses local deterministic hash embeddings (`EMBEDDING_MODEL_NAME=local-hash-embedding-v1` by default).

## Component Responsibilities

- API Layer: Input validation, error mapping, response contract consistency.
- Agent Runtime: Prompt assembly, tool invocation, response generation, safety boundaries.
- Memory Layer: Durable local memory represented as markdown contracts.
- Data Layer: SQLite message persistence, embeddings, retrieval indexes, transactions.
- Compression Layer: Token budget control, historical summarization, context continuity.
- Test Layer: Unit, integration, and contract tests with deterministic mocks.

## Spec Reading Order

1. Read `references/fastapi-sqlite-spec.md` for API, database, retrieval, and compression flow.
2. Read `references/adk-spec.md` for agent lifecycle and tool contracts.
3. Read `references/memory-system-spec.md` for markdown file schemas and write policies.
4. Read `references/env-setup.md` for local setup and runtime profiles.
5. Read `references/testing-spec.md` for test matrix and quality gates.

## Definition Of Done For Planning

- Every component has explicit input/output contracts.
- Failure modes and error codes are documented.
- Data schemas and index strategies are defined.
- Test strategy maps to each component and includes acceptance criteria.

## Implementation Phases By Component

### Phase 1: Foundation

- Components: Environment, Data Directory, Baseline Memory Files.
- Primary spec: `references/env-setup.md` and `references/memory-system-spec.md`.
- Deliverables:
  - Reproducible local runtime.
  - Required `Avatar/data/*.md` files with valid structure.
  - SQLite bootstrap and migration-safe initialization.

### Phase 2: API And Persistence

- Components: FastAPI routes, SQLite schema, request/response contracts.
- Primary spec: `references/fastapi-sqlite-spec.md`.
- Deliverables:
  - `POST /chat` and `GET /memory` contracts fully implemented.
  - Standardized error envelope.
  - Idempotent schema/index creation.

### Phase 3: Agent Runtime And Tools

- Components: ADK agent, tool registry, instruction composition.
- Primary spec: `references/adk-spec.md`.
- Deliverables:
  - Guardrailed file tools.
  - Deterministic initialization flow.
  - Retrieval tool integrated with persistence layer.

### Phase 4: Retrieval And Compression

- Components: Embedding write path, top-k retrieval, context compression loop.
- Primary spec: `references/fastapi-sqlite-spec.md`.
- Deliverables:
  - Retrieval context selection with stable ranking.
  - Compression trigger and summary persistence.
  - Token budget protection behavior.

### Phase 5: Verification And Hardening

- Components: Unit tests, integration tests, contract tests, quality gates.
- Primary spec: `references/testing-spec.md`.
- Deliverables:
  - Component test matrix coverage.
  - Deterministic mocked model and file I/O tests.
  - Acceptance criteria validated for all layers.

## References

- [Environment Setup](references/env-setup.md)
- [FastAPI & SQLite Spec](references/fastapi-sqlite-spec.md)
- [Memory System Spec](references/memory-system-spec.md)
- [Google ADK Spec](references/adk-spec.md)
- [Testing Spec](references/testing-spec.md)
