# Testing Specification

This document defines required verification strategy and quality gates for Avatar Local Agent OS.

## Scope

Covers tests for:

- API contracts
- ADK graph/runtime behavior
- Tool safety contracts
- SQLite/retrieval/compression correctness
- structured observability behavior

## Tooling

- `pytest`
- `fastapi.testclient.TestClient`
- `monkeypatch` for dependency isolation
- temporary data directories per test fixture

Primary test modules:

- `Avatar/test/test_main.py`
- `Avatar/test/test_agent.py`

## Core Testing Principles

- Deterministic: avoid network and unstable timing dependencies.
- Contract-first: verify envelopes, shapes, and status/error rules.
- Isolation: each test should control its own data root and DB path.
- Traceability: log behavior should be asserted where it is part of contract.

## Required Fixture Behaviors

Common fixture expectations:

- create temporary `Avatar/data` baseline files
- set env overrides:
  - `AVATAR_DATA_DIR`
  - `AVATAR_DB_PATH`
- reload runtime modules after env patching

## API Layer Test Requirements

Mandatory assertions:

- `GET /health` returns `success=true` and status payload.
- `POST /chat` success envelope shape is stable.
- blank message rejection returns `INVALID_REQUEST`.
- CORS preflight for `/chat` is accepted.
- `/memory` requires `user_id` and returns expected shape when provided.

Mandatory behavior checks:

- `/chat` persists user and assistant messages.
- `/chat` propagates sensitive-write approval resolution.
- `/chat` uses ADK retrieval hits when present.
- `/chat` falls back to SQLite retrieval when ADK retrieval not invoked.

## ADK Runtime Test Requirements

Mandatory assertions:

- root graph shape matches coordinator + orchestrator + specialists + templates.
- all `LlmAgent` nodes share required `GenerateContentConfig`.
- `Runner` is created with `auto_create_session=True`.
- final response prefers root final event text when available.
- `search_memory` telemetry is extracted and surfaced correctly.
- route decision structured log payload is emitted and parseable.

Failure-path assertions:

- tool permission-denied errors are surfaced in final answer and route status.
- runtime failure paths raise model-runtime envelope behavior at API layer.

## Tool and Skill Lifecycle Test Requirements

Mandatory coverage:

- `read_file`/`write_file`/`append_file`/`create_file` path and status behavior.
- strict mode sensitive-write protection for identity/soul.
- default mode allows identity/soul writes.
- `list_skills`/`read_skill`/`create_skill`/`execute_skill` end-to-end.
- local skill registry appears in root system instruction.

## Retrieval and Compression Test Requirements

Mandatory coverage:

- schema initialization idempotency.
- message ordering and retrieval output shape.
- deterministic retrieval preference and fallback behavior.
- compression trigger and summary persistence behavior.

## Observability Test Requirements

Structured log validation is mandatory for contracts that expose logs.

At minimum validate:

- `operation` lifecycle stages for `/chat`.
- `tool_execution` request/response phase records.
- `route_decision` payload contract.

Recommended key assertions:

- category/status/phase fields exist and have expected values.
- payload contains session/user identifiers when relevant.

## Mocking Rules

- Do not call external model/network APIs in automated tests.
- Mock ADK runner/session/types for `_invoke_agent` behavior tests.
- Keep fake event structures close to actual ADK event shape.

## Determinism Rules

- No dependency on wall-clock order unless explicitly fixed.
- No random behavior without deterministic seeds.
- No dependence on pre-existing local DB state.

## Required Commands

From repository root:

```bash
PYTHONPATH=. uv run pytest Avatar/test/test_agent.py Avatar/test/test_main.py -q
```

Full regression command:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
```

## Failure Triage Workflow

When tests fail:

1. Classify failure type: contract, environment, or regression.
2. Fix runtime code or docs so code/tests/spec align.
3. Re-run targeted test(s).
4. Re-run full suite before closing task.
5. Update change-log with test result summary.

## Documentation Sync Rule

Any runtime behavior change that affects these contracts must update:

- `adk-spec.md`
- `fastapi-sqlite-spec.md`
- `memory-system-spec.md`
- `env-setup.md`
- `testing-spec.md`
- `change-log.md`

## Acceptance Criteria

- Core test suite passes locally.
- API, ADK, memory, and persistence contracts are verified by tests.
- Log contract checks are present for observability-critical flows.
- No unresolved divergence between code, tests, and specs.
