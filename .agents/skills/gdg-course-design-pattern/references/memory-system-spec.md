# Local Memory System Specification

This document defines the markdown-memory and local-skill contracts for Avatar Local Agent OS.

## Scope

Covers:

- Required memory files under `Avatar/data/`.
- Memory file roles and invariants.
- Read and write precedence.
- Data-path write policy.
- Local skill registry contract under `Avatar/data/skills/`.

Does not define API envelopes; see `fastapi-sqlite-spec.md`.

## Directory Contract

Base data root:

- `Avatar/data/` (overrideable by `AVATAR_DATA_DIR`)

Required markdown files:

- `identity.md`
- `soul.md`
- `startup.md`
- `master.md`
- `memory.md`

Required directory:

- `skills/`

Encoding and formatting:

- UTF-8 text
- normalized line endings
- explicit headings to preserve stable parsing by LLM agents

## Memory File Roles

### `identity.md`

Purpose:

- User-requested role/persona/mission constraints for the assistant.

Hard invariants:

- Must include role-level constraints.
- Takes highest precedence during instruction composition.

Recommended sections:

- `# Identity`
- `## Role`
- `## Mission`
- `## Hard Constraints`
- `## Communication Style`

### `soul.md`

Purpose:

- Assistant values, self-reflection, and decision heuristics.

Hard invariants:

- Must not override identity hard constraints.
- Changes should be infrequent and intentional.

Recommended sections:

- `# Soul`
- `## Core Values`
- `## Decision Heuristics`
- `## Reflection Loop`

### `master.md`

Purpose:

- Durable profile memory about the user (preferences, stable habits, collaboration style).

Hard invariants:

- Facts should be explicit and evidence-based.
- Avoid speculative assumptions.

Recommended sections:

- `# Master`
- `## Impression`
- `## Working Style Notes`

### `startup.md`

Purpose:

- Session startup guidance and boot-time context.

Hard invariants:

- Intended as runtime/session guidance.
- Can be read when startup/session context is needed.

Recommended sections:

- `# Startup`
- `## Current Focus`
- `## Session Checklist`
- `## Immediate Context`

### `memory.md`

Purpose:

- Long-term factual memory timeline and decision ledger.

Hard invariants:

- Prefer append-oriented updates.
- Corrections should preserve traceability.

Recommended sections:

- `# Memory`
- `## User Preferences`
- `## Project Facts`
- `## Decisions`
- `## Open Questions`
- `## Timeline`

## Runtime Read Priority

Instruction composition priority in current implementation:

1. `identity.md`
2. `soul.md`
3. `master.md`
4. local skills registry summary and file-purpose routing guidance
5. `startup.md` as optional runtime/session guidance through tool flow

Operational note:

- `memory.md` is not directly inlined in root instruction by default; it is available via tools and retrieval flow.

## Purpose-Based Write Routing

When user intent is ambiguous, route writes by purpose:

- role/persona definition -> `identity.md`
- user profile/preferences -> `master.md`
- general remembered facts/tasks/decisions -> `memory.md`
- assistant self-reflection/personality policy -> `soul.md`

Do not default all writes to `memory.md`.

## Write Policy

Write behavior for file mutation tools:

- Any file under the effective data root (`Avatar/data/` or `AVATAR_DATA_DIR`) is writable.
- No per-file approval gate is applied to `identity.md` or `soul.md`.
- This unconditional allow rule also applies to `skills/`, markdown memory files, and other files under `Avatar/data`.
- Paths outside data root are denied.

## Safe Update Algorithm

1. Resolve and validate target path under data root.
2. Read current content when diff-aware update is needed.
3. Validate intent against file-purpose routing.
4. Ensure target path remains inside data root.
5. Apply update via tool contract.
6. Verify tool result (`Success`) before claiming completion.

Tool semantics:

- `write_file`: atomic replace
- `append_file`: newline-normalized append
- `create_file`: create-if-absent

## Local Skill Registry Contract

Location:

- `Avatar/data/skills/<skill_name>/`

Required file per skill:

- `SKILL.md`

Optional executable:

- `run.py`

Name policy:

- regex: `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`

Runtime constraints:

- max auto-discovered skills: `MAX_LOCAL_SKILLS = 20`
- execution timeout bounded by `SKILL_EXEC_TIMEOUT_SECONDS`
- skill output size bounded by `MAX_FILE_BYTES`

## Skill Tool Contracts

- `list_skills`: returns JSON metadata list
- `read_skill`: returns markdown body
- `create_skill`: creates skill directory + files
- `execute_skill`: runs `run.py` with JSON payload via stdin and env

Execution I/O contract:

- stdin contains normalized JSON
- env includes `AVATAR_SKILL_INPUT_JSON`
- non-zero exit becomes `TOOL_RUNTIME_ERROR`

## Privacy and Redaction

Do not persist:

- credentials
- API tokens
- sensitive secret material unless explicitly required and approved

Prefer:

- concise factual summaries
- durable signals over verbatim long transcripts

## Recommended Size Management

Suggested operational limits:

- Keep `memory.md` compact and navigable.
- For large growth, summarize stale sections into concise history notes while preserving important decisions.

## Acceptance Criteria

- Required files and `skills/` directory exist and are readable.
- File mutation tools allow writes for all in-scope data files.
- Purpose-based routing is reflected in responder/memory-maintenance behavior.
- Local skill lifecycle functions (create/list/read/execute) work within guardrails.
- Memory contracts remain consistent with ADK instruction composition.
