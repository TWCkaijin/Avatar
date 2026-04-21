# Identity & Baseline Data Specification

This document defines the canonical content expectations for `Avatar/data/*.md`.

## Scope

Covers:

- Bootstrap fallback baselines created by runtime when files are missing.
- Production content contract for identity/soul/startup/master/memory.
- Update policy and quality checks for profile memory updates.

## Two-Level Baseline Model

Avatar uses two baseline levels:

1. **Bootstrap fallback baseline** (runtime-generated minimal content)
2. **Operational profile baseline** (project/team curated content)

Both are valid, but operational profile baseline is preferred for real usage.

## Bootstrap Fallback Baseline (From Runtime)

Defined in `Avatar/app/main.py::MEMORY_BASELINES` and applied when files are absent.

Minimal fallback bodies:

- `identity.md` -> `# Identity / ## Role / Local Agent OS assistant`
- `soul.md` -> `# Soul / ## Core Values / - Truthful`
- `startup.md` -> `# Startup / ## Current Focus / Boot sequence`
- `master.md` -> `# Master / ## Impression / - Pending`
- `memory.md` -> `# Memory / ## Timeline / - Initialization complete`

## Operational Profile Baseline (Preferred)

Current repository uses richer profile content under `Avatar/data/`.

### `identity.md` (Current Profile)

Intent:

- Defines active persona identity and mission.

Current profile style includes:

- named persona
- role declaration
- competencies
- mission
- personality

### `soul.md` (Current Profile)

Intent:

- Defines value system, philosophy, and decision axioms.

Current profile style includes:

- core principles
- philosophy statement
- axioms
- decision heuristics

### `startup.md` (Current Profile)

Intent:

- Defines first-turn startup behavior and checklist.

Current profile style includes:

- startup conversational framing
- first-turn bootstrap question
- session checklist
- immediate context reminders

### `master.md` (Current Profile)

Intent:

- Stores durable user profile and collaboration preferences.

Current profile style includes:

- relationship context
- interaction style
- role alignment
- domain-specific preferences

### `memory.md` (Current Profile)

Intent:

- Stores timeline, milestones, and ongoing directives.

Current profile style includes:

- major milestones
- key history
- ongoing directives

## Required Invariants Per File

### Identity invariants

- Must clearly define role and mission.
- Must include explicit hard constraints or governing principles.
- Must remain the highest-priority instruction layer.

### Soul invariants

- Must not contradict identity hard constraints.
- Must emphasize stable values and decision heuristics.

### Startup invariants

- Must be startup/session oriented.
- Must not override identity/soul constraints.

### Master invariants

- Must focus on user profile memory, not transient task logs.
- Facts should be durable and evidence-based.

### Memory invariants

- Should function as durable history and directive ledger.
- Prefer concise, traceable updates.

## Update Policy

When updating profile files:

1. Determine target file by purpose first.
2. Preserve existing section structure unless migration is intentional.
3. Avoid destructive rewrites of unrelated sections.
4. Keep user-specific facts in `master.md` rather than `memory.md` when applicable.
5. Record major profile shifts in change-log when they affect system behavior.

## Purpose Routing Matrix

- Role/persona rewrite -> `identity.md`
- Assistant value/heuristic rewrite -> `soul.md`
- Startup bootstrap behavior rewrite -> `startup.md`
- User preference/profile rewrite -> `master.md`
- Timeline, directives, notable events -> `memory.md`

## Content Quality Rules

- Use explicit headings.
- Keep statements falsifiable when possible.
- Avoid storing credentials/secrets.
- Prefer concise operational phrasing over prose-heavy narrative in critical sections.

## Suggested Validation Checklist

After profile updates:

- `identity.md` still expresses role + mission clearly.
- `soul.md` still aligns with identity constraints.
- `startup.md` still supports first-turn startup intent.
- `master.md` stores user-profile durable facts.
- `memory.md` remains a readable timeline/direction ledger.

## Acceptance Criteria

- All five data files exist and are readable.
- Runtime can safely build system instruction from identity/soul/master.
- Startup guidance remains available for session bootstrap.
- Profile updates remain purpose-routed and traceable.
