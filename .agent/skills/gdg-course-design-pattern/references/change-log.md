# Change Log

## 2026-04-16

### Entry 1

- Summary: Added post-change-test-and-sync skill to standardize post-code-change verification workflow.
- Files: .agent/skills/post-change-test-and-sync/SKILL.md
- Tests Added/Updated: N/A (documentation-only skill definition)
- Test Result: N/A

### Entry 2

- Summary: Fixed ADK SessionNotFoundError on /chat by enabling runner auto session creation.
- Files: Avatar/app/main.py, Avatar/test/test_main.py
- Tests Added/Updated: Added test_invoke_agent_uses_auto_create_session; ran targeted and full pytest.
- Test Result: PASS (targeted: 1 passed, full suite: 10 passed)

### Entry 3

- Summary: Fixed missing chat reply path by collecting final response across multi-agent final events; prevented accidental frontend page reload on send.
- Files: Avatar/app/main.py, Avatar/app/agent.py, Avatar/demo/index.html, Avatar/test/test_main.py
- Tests Added/Updated: Added test_invoke_agent_prefers_root_final_response_text; ran targeted and full pytest.
- Test Result: PASS (targeted: 1 passed, full suite: 11 passed)

### Entry 4

- Summary: Suppressed noisy google-genai non-text-part warning logs while keeping other warnings intact.
- Files: Avatar/app/main.py
- Tests Added/Updated: No new tests; reran targeted and full pytest under explicit PYTHONPATH.
- Test Result: PASS (targeted: 9 passed, full suite: 11 passed)

### Entry 5

- Summary: Added fine-grained frontend API trace logs so demo clearly shows when requests are triggered and what each response returns.
- Files: Avatar/demo/index.html
- Tests Added/Updated: No new tests; reran full pytest regression suite.
- Test Result: PASS (full suite: 11 passed)

### Entry 6

- Summary: Added ADK native demo adapter package so Google ADK Web UI can load the Avatar agent directly.
- Files: Avatar/adk_agents/avatar/agent.py, Avatar/adk_agents/avatar/__init__.py
- Tests Added/Updated: No new tests; verified ADK web endpoints (/list-apps, /apps/avatar/app-info) and reran full pytest.
- Test Result: PASS (adk web load check passed, full suite: 11 passed)

### Entry 7

- Summary: Personalized startup/identity/soul/memory default prompts, and set startup onboarding intent to ask: "please define me. My soul, my identity, and what should I do for you".
- Files: Avatar/data/startup.md, Avatar/data/identity.md, Avatar/data/soul.md, Avatar/data/memory.md
- Tests Added/Updated: No new tests; reran full pytest regression suite.
- Test Result: PASS (full suite: 11 passed)

### Entry 8

- Summary: Updated ConversationOrchestrator from fixed sequential flow to adaptive specialist routing so root delegation can choose per-request agent flow.
- Files: Avatar/app/agent.py, Avatar/test/test_agent.py, .agent/skills/gdg-course-design-pattern/references/adk-spec.md
- Tests Added/Updated: Updated agent graph assertion to validate adaptive orchestrator semantics; ran targeted and full pytest suites.
- Test Result: PASS (targeted: 2 passed, full suite: 11 passed)

### Entry 9

- Summary: Added structured runtime route logs that record which sub-agents were selected for each ADK invocation.
- Files: Avatar/app/main.py, Avatar/test/test_main.py
- Tests Added/Updated: Added test_invoke_agent_logs_structured_route_decision; reran targeted and full pytest suites.
- Test Result: PASS (targeted: 1 passed, full suite: 12 passed)

## 2026-04-17

### Entry 10

- Summary: Added `master.md` memory contract, ensured runtime memory files are loaded on each `/chat` invocation, and fixed ADK `collected_context` missing-key crash by removing brittle instruction placeholders.
- Files: Avatar/app/agent.py, Avatar/app/main.py, Avatar/data/master.md, Avatar/data/startup.md, Avatar/test/test_agent.py, Avatar/test/test_main.py
- Tests Added/Updated: Updated memory fixtures/contracts for `master.md`; added regression assertions that root instruction includes `MASTER IMPRESSION` and `ResponseComposer` no longer uses `{collected_context}`/`{retrieval_context}` placeholders.
- Test Result: PASS (full suite: 12 passed with `PYTHONPATH=. uv run pytest -q`)

### Entry 11

- Summary: Added structured mutation/terminal tool activity logs, fixed false-success behavior after `TOOL_PERMISSION_DENIED`, and enabled explicit approval for sensitive `identity.md`/`soul.md` updates via request flag or clear user write intent.
- Files: Avatar/app/agent.py, Avatar/app/main.py, Avatar/test/test_agent.py, Avatar/test/test_main.py, .agent/skills/gdg-course-design-pattern/references/adk-spec.md, .agent/skills/gdg-course-design-pattern/references/memory-system-spec.md
- Tests Added/Updated: Expanded sensitive write tests to cover `write_file`/`append_file`/`create_file`, added log payload assertions for mutation tools, added approval-flag propagation test, and added `_invoke_agent` regression test ensuring tool permission failure is surfaced in final response and route status.
- Test Result: PASS (full suite: 15 passed with `PYTHONPATH=. uv run pytest -q`)

### Entry 12

- Summary: Strengthened identity/soul write-intent detection for natural language phrases (for example "add this into identity"), added explicit memory-file purpose routing for `identity.md`/`master.md`/`memory.md`/`soul.md`, and upgraded `MemoryMaintenanceAgent` to use full file mutation tools.
- Files: Avatar/app/agent.py, Avatar/app/main.py, Avatar/data/startup.md, Avatar/test/test_agent.py, Avatar/test/test_main.py, .agent/skills/gdg-course-design-pattern/references/adk-spec.md, .agent/skills/gdg-course-design-pattern/references/memory-system-spec.md
- Tests Added/Updated: Updated approval propagation test with natural-language identity intent phrasing; expanded agent graph assertions for memory file purpose contract and `MemoryMaintenanceAgent` toolset.
- Test Result: PASS (full suite: 15 passed with `PYTHONPATH=. uv run pytest -q`)

### Entry 13

- Summary: Lowered `identity.md`/`soul.md` write permission to be allowed by default, introduced optional strict guard mode via `STRICT_SENSITIVE_WRITE_GUARD=true`, and added explicit storage/persistence logs (`storage_config`, `chat_persisted`) to diagnose `chat.db` path confusion.
- Files: Avatar/app/agent.py, Avatar/app/main.py, Avatar/test/test_agent.py, Avatar/README.md, .agent/skills/gdg-course-design-pattern/references/adk-spec.md, .agent/skills/gdg-course-design-pattern/references/memory-system-spec.md
- Tests Added/Updated: Updated sensitive-write protection test to run under strict mode; added regression test confirming identity/soul writes are allowed by default.
- Test Result: PASS (full suite: 16 passed with `PYTHONPATH=. uv run pytest -q`)

### Entry 14

- Summary: Added fine-grained operation logging so each API/tool step emits structured request/response logs, including `/chat` transaction stages, `/memory` fetch stages, and complete tool-level logs for read/write/retrieval operations.
- Files: Avatar/app/main.py, Avatar/app/agent.py, Avatar/test/test_main.py, Avatar/test/test_agent.py, Avatar/README.md, .agent/skills/gdg-course-design-pattern/references/adk-spec.md
- Tests Added/Updated: Added `test_chat_emits_step_operation_logs` and `test_read_and_search_memory_logs_include_request_and_response`.
- Test Result: PASS (full suite: 18 passed with `PYTHONPATH=. uv run pytest -q`)

## 2026-04-18

### Entry 15

- Summary: Reorganized the repository by moving main ADK program assets into `Avatar/` subfolder and updated path references under `.agent/skills/gdg-course-design-pattern` to match the new structure.
- Files: Avatar/app/, Avatar/adk_agents/, Avatar/data/, Avatar/demo/, Avatar/test/, Avatar/README.md, .agent/skills/gdg-course-design-pattern/SKILL.md, .agent/skills/gdg-course-design-pattern/references/*.md
- Tests Added/Updated: N/A (filesystem layout and documentation path-reference update)
- Test Result: N/A

## 2026-04-19

### Entry 16

- Summary: Fixed ADK Web loader `ModuleNotFoundError` for app `avatar` by correcting adapter import path from `Avatar.app.agent` to `app.agent` in the ADK native package entry module.
- Files: Avatar/adk_agents/avatar/agent.py
- Tests Added/Updated: No new tests; validated `import avatar` under ADK-style `PYTHONPATH=adk_agents` and ran targeted regression tests for agent and API behavior.
- Test Result: PASS (import smoke check: `AvatarCoordinator`; pytest: 18 passed with `PYTHONPATH=. uv run pytest Avatar/test/test_agent.py Avatar/test/test_main.py -q`)

### Entry 17

- Summary: Fully synchronized `.agent/skills/gdg-course-design-pattern` architecture and reference specifications with the current implementation (model defaults, adaptive orchestration, request contracts, retrieval/compression behavior, environment setup, and testing expectations).
- Files: .agent/skills/gdg-course-design-pattern/SKILL.md, .agent/skills/gdg-course-design-pattern/references/adk-spec.md, .agent/skills/gdg-course-design-pattern/references/fastapi-sqlite-spec.md, .agent/skills/gdg-course-design-pattern/references/memory-system-spec.md, .agent/skills/gdg-course-design-pattern/references/env-setup.md, .agent/skills/gdg-course-design-pattern/references/testing-spec.md
- Tests Added/Updated: N/A (documentation synchronization only)
- Test Result: N/A

## 2026-04-20

### Entry 18

- Summary: Migrated chat context flow from manual prompt assembly to ADK-native session state injection, and enabled ADK native memory tools (`preload_memory` / `load_memory`) in the agent graph.
- Files: Avatar/app/main.py, Avatar/app/agent.py, Avatar/test/test_main.py, Avatar/README.md, .agent/skills/gdg-course-design-pattern/references/adk-spec.md
- Tests Added/Updated: Added `test_chat_passes_runtime_context_to_adk_session_state`; updated `_invoke_agent` test stubs for `runtime_context` argument; reran full pytest.
- Test Result: PASS (full suite: 19 passed with `PYTHONPATH=. .venv/bin/python -m pytest -q`)

### Entry 19

- Summary: Migrated agent orchestration to ADK LLM-as-tool style using `AgentTool`, so `AvatarCoordinator` and `ConversationOrchestrator` perform dynamic specialist calls via native ADK tool invocation.
- Files: Avatar/app/agent.py, Avatar/test/test_agent.py, Avatar/README.md, README.md, .agent/skills/gdg-course-design-pattern/references/adk-spec.md, .agent/skills/gdg-course-design-pattern/references/fastapi-sqlite-spec.md
- Tests Added/Updated: Updated `test_agent_graph_shape` to assert AgentTool-based graph shape (`root/tools` and orchestrator specialist tools) instead of static sub-agent wiring; reran full pytest.
- Test Result: PASS (full suite: 19 passed with `PYTHONPATH=. .venv/bin/python -m pytest -q`)

### Entry 20

- Summary: Implemented ADK-first context/retrieval flow by removing host-side runtime context composition for `/chat`, using ADK tool telemetry (`search_memory`) as primary retrieval source, and keeping SQLite fallback retrieval for response-schema compatibility.
- Files: Avatar/app/main.py, Avatar/app/agent.py, Avatar/test/test_main.py, README.md, Avatar/README.md, google-adk-trail/README.md, .agent/skills/gdg-course-design-pattern/SKILL.md, .agent/skills/gdg-course-design-pattern/references/adk-spec.md, .agent/skills/gdg-course-design-pattern/references/fastapi-sqlite-spec.md, .agent/skills/gdg-course-design-pattern/references/env-setup.md
- Tests Added/Updated: Replaced runtime-context session injection test with ADK tool-first retrieval/fallback tests; added telemetry regression test `test_invoke_agent_collects_search_memory_hits_in_telemetry`; reran targeted and full pytest.
- Test Result: PASS (targeted: 21 passed with `PYTHONPATH=. .venv/bin/python -m pytest Avatar/test/test_main.py Avatar/test/test_agent.py -q`; full suite: 21 passed with `PYTHONPATH=. .venv/bin/python -m pytest -q`)

### Entry 21

- Summary: Cleaned duplicated/outdated documentation lines after ADK-first migration, corrected `/memory` README examples to include `master`, and aligned run commands for root vs `Avatar/` execution contexts.
- Files: README.md, Avatar/README.md, .agent/skills/gdg-course-design-pattern/references/env-setup.md
- Tests Added/Updated: No new tests; reran full pytest regression suite to confirm no behavioral regressions.
- Test Result: PASS (full suite: 21 passed with `PYTHONPATH=. .venv/bin/python -m pytest -q`)

### Entry 22

- Summary: Synchronized gdg-course-design-pattern specs with the current Avatar implementation, corrected outdated workspace paths, and removed spec mismatches (layout, transaction semantics, compression persistence, and memory read/write precedence wording).
- Files: .agent/skills/gdg-course-design-pattern/SKILL.md, .agent/skills/gdg-course-design-pattern/references/env-setup.md, .agent/skills/gdg-course-design-pattern/references/fastapi-sqlite-spec.md, .agent/skills/gdg-course-design-pattern/references/adk-spec.md, .agent/skills/gdg-course-design-pattern/references/memory-system-spec.md, .agent/skills/gdg-course-design-pattern/references/testing-spec.md, .agent/skills/gdg-course-design-pattern/references/change-log.md
- Tests Added/Updated: No code tests added (documentation/spec synchronization only).
- Test Result: N/A
