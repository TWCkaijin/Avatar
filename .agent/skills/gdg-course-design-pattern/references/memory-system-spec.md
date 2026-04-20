# Local Memory System Specification

This document defines the normative markdown memory contracts for the Local Agent OS.

## Directory Contract

- Base path: `Avatar/data/`
- Required files:
  - `identity.md`
  - `soul.md`
  - `startup.md`
  - `master.md`
  - `memory.md`
- Required directory:
  - `skills/` (local skill registry and executable skill code)

All files must be UTF-8 text and line-ending consistent.

## Local Skills Contract (`Avatar/data/skills/`)

Purpose:

- Stores agent-generated reusable skill definitions and optional executable code.

Layout:

- `Avatar/data/skills/<skill_name>/SKILL.md` (required per registered skill)
- `Avatar/data/skills/<skill_name>/run.py` (optional executable entrypoint)

Invariants:

- `skill_name` must match `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`.
- Skill definitions must stay under `Avatar/data/skills/`.
- Executable skill code may run only from approved skill entrypoints under `Avatar/data/skills/<skill_name>/`.
- Skill execution input must be JSON-compatible and execution must be timeout bounded.

## File Roles And Invariants

### `identity.md`

Purpose:

- Defines role identity and character settings requested by the user.

Invariants:

- Must always contain: role, mission, hard constraints.
- Should be changed only by explicit user instruction.

Recommended structure:

```markdown
# Identity
## Role
## Mission
## Hard Constraints
## Communication Style
```

### `soul.md`

Purpose:

- Defines the assistant's own stable personality principles, values, and reflection heuristics.

Invariants:

- Must not override hard constraints in `identity.md`.
- Should evolve slowly and explicitly.

Recommended structure:

```markdown
# Soul
## Core Values
## Decision Heuristics
## Reflection Loop
```

### `master.md`

Purpose:

- Stores durable memory about the user (master profile, preferences, relationship context).

Invariants:

- User-specific profile facts should be concise, current, and grounded in explicit evidence.
- Should prioritize persistent user preferences over transient task notes.

Recommended structure:

```markdown
# Master
## Basic Info
## Impression
## Working Style Notes
```

### `startup.md`

Purpose:

- Defines boot-time priming instructions and active goals.

Invariants:

- Loaded at session start before first response generation.
- Can include temporary run context, but avoid secrets.

Recommended structure:

```markdown
# Startup
## Current Focus
## Session Checklist
## Immediate Context
```

### `memory.md`

Purpose:

- Stores user-requested memory entries and other important durable facts/decisions.

Invariants:

- Prefer append-only event records with timestamps.
- Corrections should reference prior entries instead of destructive edits.

Recommended structure:

```markdown
# Memory
## User Preferences
## Project Facts
## Decisions
## Open Questions
## Timeline
```

## Read Priority

Effective runtime order:

1. Root instruction loads `identity.md` first.
2. Root instruction then loads `soul.md`.
3. Root instruction then loads `master.md`.
4. Root instruction includes local skill registry context and memory-purpose routing guidance.
5. `startup.md` is treated as runtime/session guidance and is consumed through tool flow when needed (for example via `read_file`, `load_memory`, or runtime hints).
6. Specialist agents load additional durable context through ADK `load_memory` and retrieval context via `search_memory` hits.

## Write Policy

- `identity.md`: write is allowed by default.
- `soul.md`: write is allowed by default.
- Optional strict mode: when `STRICT_SENSITIVE_WRITE_GUARD=true`, writes to `identity.md` and `soul.md` require explicit approval.
- Approval sources: request `allow_sensitive_writes=true`, metadata `allow_sensitive_writes=true`, or clear write-intent language targeting identity/soul.
- `startup.md`: system may update when session objective changes.
- `master.md`: system may update with durable user-profile memory and preference changes.
- `memory.md`: system may append factual observations and decisions.

Purpose routing guidance:

- Role/persona requests should target `identity.md`.
- Durable user profile and preference memory should target `master.md`.
- General remembered facts/tasks/decisions should target `memory.md`.
- Assistant self-reflection or personality principle updates should target `soul.md`.

## Safe Update Algorithm

1. Read current file.
2. Validate path is under allowed base directory.
3. Generate candidate patch.
4. Validate invariants and size limits.
5. Persist changes by tool contract.
6. Append audit note to `memory.md` for material changes.

Tool contract details:

- `write_file`: atomic replace (temp file + rename)
- `append_file`: newline-normalized append
- `create_file`: create-if-absent

## Redaction And Privacy

- Do not persist secrets, tokens, or credentials.
- Redact personal sensitive data unless explicitly required.
- Prefer summarized facts over verbatim transcripts for privacy.

## Size And Rotation

- If `memory.md` exceeds threshold (for example 500 KB), summarize stale sections.
- Persist archival summary in RAG store before pruning.

## Acceptance Criteria

- All required files exist and load without errors.
- Write policies are enforced by tool layer.
- Root instruction always preserves identity-first precedence.
- Strict mode blocks identity/soul writes without explicit approval.
- Purpose-based file routing is documented and enforced by agent instructions.
