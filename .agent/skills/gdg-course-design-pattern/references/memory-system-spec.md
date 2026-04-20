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

All files must be UTF-8 text and line-ending consistent.

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
Prompt assembly order:
1. `identity.md`
2. `soul.md`
3. `startup.md`
4. `master.md`
5. Relevant slices from `memory.md`
6. Retrieved RAG snippets

## Write Policy
- `identity.md`: write is allowed by default.
- `soul.md`: write is allowed by default.
- Optional strict mode: when `STRICT_SENSITIVE_WRITE_GUARD=true`, writes to `identity.md` and `soul.md` require explicit approval.
- Approval sources: request `allow_sensitive_writes=true`, metadata `allow_sensitive_writes=true`, or clear write-intent language targeting identity/soul.
- `startup.md`: system may update when session objective changes.
- `master.md`: system may update with durable user-profile memory and preference changes.
- `memory.md`: system may append factual observations and decisions.

## Safe Update Algorithm
1. Read current file.
2. Validate path is under allowed base directory.
3. Generate candidate patch.
4. Validate invariants and size limits.
5. Persist changes by tool contract:
	- `write_file`: atomic replace (temp file + rename)
	- `append_file`: newline-normalized append
	- `create_file`: create-if-absent
6. Append audit note to `memory.md` for material changes.

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
- Prompt assembly always preserves identity and constraint precedence.
