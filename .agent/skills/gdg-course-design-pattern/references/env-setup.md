# Environment Setup

This document defines the canonical local setup for developing, running, and validating Avatar Local Agent OS.

## ADK References

- [ADK Home](https://adk.dev/)
- [ADK Docs](https://adk.dev/docs/)
- [ADK Quickstart](https://adk.dev/docs/quickstart)

When changing ADK graph/tool behavior, read ADK docs first and prefer ADK-native methods.

## Runtime Scope

Project runtime root:

- Repository root contains shared manifests and `.env`.
- Application runtime code lives under `Avatar/`.

Key runtime folders:

- `Avatar/app/`
- `Avatar/adk_agents/`
- `Avatar/data/`
- `Avatar/test/`

## Prerequisites

- Python `3.10+`
- `uv` (recommended) or `venv + pip`
- Local writable filesystem for `Avatar/data/`
- No Firebase CLI/npm dependency required

## Environment Variable Matrix

Required:

- `GOOGLE_API_KEY` or `GEMINI_API_KEY`

Rules:

- Prefer `GOOGLE_API_KEY`.
- `GEMINI_API_KEY` is compatibility fallback.
- If both are set, runtime should use `GOOGLE_API_KEY`.
- Load `.env` via `load_dotenv()` before reading API keys.
- Resolve key as `os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")`.

Optional runtime variables:

- `AVATAR_DATA_DIR`
  - default: `Avatar/data`
  - purpose: override memory/data root
- `AVATAR_DB_PATH`
  - default: `<AVATAR_DATA_DIR>/chat.db`
  - purpose: override SQLite file path
- `EMBEDDING_MODEL_NAME`
  - default: `local-hash-embedding-v1`
  - purpose: embedding metadata label
- `EMBEDDING_DIMENSIONS`
  - default: `64`
  - bounded runtime range: `8..256`
- `STRICT_SENSITIVE_WRITE_GUARD`
  - default: `false`
  - purpose: require explicit approval for `identity.md` / `soul.md` writes
- `SKILL_EXEC_TIMEOUT_SECONDS`
  - default: `20`
  - purpose: timeout for local skill code execution
- `CORS_ALLOW_ORIGINS`
  - default: `*`
  - purpose: CORS allowlist (comma-separated)
- `CORS_ALLOW_CREDENTIALS`
  - default: `false`
  - purpose: credentialed CORS

## Dependency Baseline

Core dependencies:

- `fastapi`
- `uvicorn`
- `google-adk`
- `google-genai`
- `python-dotenv`
- `pydantic`
- `pytest`
- `httpx`

Notes:

- `sqlite3` is built into CPython.
- Keep dependency updates consistent with tests and reference docs.

## Recommended Project Layout

```text
<repo-root>/
  pyproject.toml
  requirements.txt
  README.md
  .env
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
      chat.db
      identity.md
      soul.md
      startup.md
      master.md
      memory.md
      skills/
        <skill_name>/
          SKILL.md
          run.py
    test/
      test_agent.py
      test_main.py
```

## Setup Paths

### Path A (Recommended): `uv`

From repository root:

```bash
uv sync
cp .env.example .env
```

### Path B: `venv + pip`

From repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Path C (Optional): `conda` then pip/uv inside env

Use this only when your team standard requires conda.

```bash
conda create -n avatar python=3.11 pip -y
conda activate avatar
pip install -r requirements.txt
cp .env.example .env
```

## Dotenv Resolution Rules

- Canonical `.env` location is repo root.
- Runtime entrypoints must call `load_dotenv()` before ADK/model initialization.
- `google-adk-trail/*` scripts resolve root `.env` explicitly.

Recommended bootstrap snippet:

```python
import os
from dotenv import load_dotenv

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not google_api_key:
  raise RuntimeError("Missing GOOGLE_API_KEY (or GEMINI_API_KEY) in .env")
```

## Data Bootstrap Requirements

Before first run, ensure these files/directories exist (runtime will create baselines when missing):

- `Avatar/data/identity.md`
- `Avatar/data/soul.md`
- `Avatar/data/startup.md`
- `Avatar/data/master.md`
- `Avatar/data/memory.md`
- `Avatar/data/skills/`

## Run Commands

### API (from repository root)

```bash
uvicorn Avatar.app.main:app --reload --port 8000
```

### API (from `Avatar/` folder)

```bash
uvicorn app.main:app --reload --port 8000
```

### ADK Web (from `Avatar/` folder)

```bash
PYTHONPATH=adk_agents adk web
```

## Test Commands

From repository root:

```bash
PYTHONPATH=. uv run pytest Avatar/test/test_agent.py Avatar/test/test_main.py -q
```

Full suite:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
```

## Health And Runtime Verification

Minimal checks:

- `GET /health` returns `success=true` and `status=healthy`.
- `POST /chat` returns success envelope and retrieval metadata shape.
- `GET /memory?user_id=<id>` returns memory file payload + recent history list.

Log checks:

- `storage_config` on startup (effective `data_dir`, `db_path`)
- `operation` logs for route lifecycle
- `chat_persisted` on successful chat transaction commit

## Operational Notes

- Current core API profile is `/health`, `/chat`, `/memory`.
- Retrieval policy is ADK-tool-first (`search_memory`) with SQLite fallback.
- Strict sensitive-write behavior is disabled by default unless env override is enabled.

## Troubleshooting

### Missing API key

Symptoms:

- model/runtime failures on chat invocation

Checks:

- verify `.env` at repo root
- verify variable names (`GOOGLE_API_KEY` / `GEMINI_API_KEY`)

### ADK import path errors

Symptoms:

- `No module named 'Avatar'` or adapter import failure

Checks:

- adapter should import `from app.agent import create_root_agent`
- run ADK web from `Avatar/` with `PYTHONPATH=adk_agents`

### SQLite lock or persistence issues

Symptoms:

- intermittent DB failures

Checks:

- keep request-scoped short-lived SQLite connections
- ensure transaction rollback on exception paths

### Test import errors

Symptoms:

- `ModuleNotFoundError: No module named 'app'` or similar

Checks:

- run tests from repository root
- include `PYTHONPATH=.` in command

## Migration Notes (Firebase -> Local Agent OS)

- Remove Firebase SDK/config and cloud function assumptions.
- Use local FastAPI entrypoint.
- Use SQLite + markdown memory as the default persistence model.
