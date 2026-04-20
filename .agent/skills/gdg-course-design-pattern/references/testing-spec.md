# Testing Specification

This document defines quality gates and verification strategy for Local Agent OS.

## Test Framework And Tooling

- `pytest` for test execution
- `fastapi.testclient.TestClient` for API integration tests
- `pytest` `monkeypatch` and deterministic fake runner/session types for model/runtime mocks

## Test Pyramid

- Unit tests:
  - Tool functions
  - Prompt assembly helpers
  - Retrieval ranking helpers
- Integration tests:
  - API routes with in-memory or isolated SQLite
  - End-to-end request flow with mocked model provider
- Contract tests:
  - Request/response schema validation
  - Error envelope consistency

## Component Test Matrix

### API Layer

- Valid request returns success envelope.
- Invalid payload returns `INVALID_REQUEST`.
- Unexpected exception returns `INTERNAL_ERROR` envelope.
- CORS preflight (`OPTIONS /chat`) is accepted.
- `allow_sensitive_writes` resolution is propagated to `_invoke_agent`.
- `/chat` prefers ADK tool retrieval hits and only uses SQLite fallback when ADK retrieval is not invoked.
- `/chat` operation logs include key lifecycle stages (`request_received`, `retrieve_context`, `invoke_agent`, transaction commit/rollback, `response_ready`).

### ADK Layer

- Agent initializes with required instruction layers.
- Tool invocation failures are surfaced without fabricated output.
- Root coordinator has expected sub-agent graph.
- All LlmAgent nodes register `google_search` as a default tool.
- Workflow orchestrator supports adaptive specialist selection and emits route logs (`route_decision`).
- Workflow orchestrator registers reusable flow template tools (`SequentialFlowTemplate`, `ParallelFlowTemplate`, `LoopFlowTemplate`).
- Flow template tools expose explicit control parameters (`agent_a`/`agent_b` or `flow_agent` + `stop_condition` + `max_iterations`) in their instruction contracts.
- ResponseComposer registers local skill tools (`list_skills`, `read_skill`, `create_skill`, `execute_skill`).
- Local skill tools can create/list/read/execute skills from `Avatar/data/skills` within path/timeout guards.
- File mutation and retrieval tools emit structured request/response logs (`tool_execution`).

### Memory Layer

- Required markdown files are loaded in defined priority order.
- Local skill registry from `Avatar/data/skills` is loaded into system instruction context.
- Reserved file write protections are enforced in strict mode and allowed by default otherwise.
- Tool logging includes request/response phase records for read/write/retrieval calls.

### SQLite/RAG Layer

- Schema initialization is idempotent.
- Message insert and retrieval maintain ordering.
- Embedding retrieval returns deterministic top-k for fixed inputs.

### Compression Layer

- Compression triggers at configured threshold.
- Summary persistence and compressed markers are written correctly.

## Mocking Rules

- Mock model generation and embedding calls in all automated test environments.
- Use temporary directories for memory file operations.
- Use isolated SQLite DB per test module or test case.

## Fixtures

Recommended fixtures:

- `tmp_data_dir`: temporary `Avatar/data/` directory with baseline memory files
- `sqlite_test_db`: isolated SQLite path or `:memory:`
- `mock_model_client`: deterministic responses for generation and embeddings
- `api_client`: FastAPI `TestClient`

## Determinism Requirements

- Tests must not rely on wall-clock timing unless explicitly frozen.
- Tests must not use external network calls.
- Randomness must be seeded where ranking or sampling is involved.

## Quality Gates

- All tests pass in local environment.
- Minimum line coverage target should be 80% for critical modules.
- No skipped tests for core contracts without justification.

## Suggested Commands

```bash
pytest -q
pytest --maxfail=1 --disable-warnings
PYTHONPATH=. uv run pytest Avatar/test/test_agent.py Avatar/test/test_main.py -q
```

Current expectation:

- The repository keeps deterministic automated tests under Avatar/test/ and these tests should pass before updating architecture specs.

## Acceptance Criteria

- API, ADK, memory, and database components each have explicit test coverage.
- Error envelopes are tested across representative failure modes.
- Compression and retrieval logic are verifiable in repeatable test scenarios.
- Multi-agent flow (coordinator -> adaptive orchestrator -> specialists/templates) is validated by route-selection and final-response integration tests.
