# Environment Setup

This document defines the standard local setup for developing and running the Avatar Local Agent OS.

## ADK References

- [Google ADK official docs](https://adk.dev/)
- [ADK docs index](https://adk.dev/docs/)
- [ADK quickstart](https://adk.dev/docs/quickstart)
- For ADK-related code changes, read the relevant ADK docs first and prioritize ADK-native methods when available.

## Prerequisites

- Python 3.10+
- uv (recommended) or pip + virtualenv
- Local filesystem access for Avatar/data/ directory
- No Firebase CLI or npm dependencies required

## Required Environment Variables

- `GEMINI_API_KEY`: API key for generation and embeddings

Optional:

- `AVATAR_DATA_DIR`: override runtime memory directory (default Avatar/data)
- `AVATAR_DB_PATH`: override SQLite path (default <AVATAR_DATA_DIR>/chat.db)
- `EMBEDDING_MODEL_NAME`: embedding model label persisted to DB metadata (default local-hash-embedding-v1)
- `EMBEDDING_DIMENSIONS`: embedding dimensions (8 to 256, default 64)
- `STRICT_SENSITIVE_WRITE_GUARD`: when true, identity/soul writes require explicit approval
- `CORS_ALLOW_ORIGINS`: comma-separated CORS origins (default *)
- `CORS_ALLOW_CREDENTIALS`: CORS credentials flag (true or false, default false)

## Dependency Baseline

- fastapi
- uvicorn
- google-adk
- google-genai
- python-dotenv
- pydantic
- pytest
- httpx

Note:

- `sqlite3` is built into CPython and does not need separate installation.

## Recommended Project Layout

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
      chat.db
      identity.md
      soul.md
      startup.md
      master.md
      memory.md
    test/
      test_agent.py
      test_main.py
```

## Local Setup Steps

1. From repository root, create and activate a virtual environment (or use uv).
2. Install dependencies from requirements.txt or pyproject.toml.
3. Create .env and set GEMINI_API_KEY.
4. Ensure Avatar/data memory files exist (identity.md, soul.md, startup.md, master.md, memory.md).
5. Start API server with auto reload.

Recommended install commands from repository root:

```bash
uv sync
# or
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Runtime Profiles

- Development:
  - Verbose logs
  - Real model calls allowed
- Test:
  - Use mocks for model calls
  - Use isolated SQLite test DB or `:memory:`

## Execution

From repository root:

```bash
uvicorn Avatar.app.main:app --reload --port 8000
```

From Avatar/ folder (alternative):

```bash
uvicorn app.main:app --reload --port 8000
```

ADK Web/CLI loading (from Avatar/):

```bash
PYTHONPATH=adk_agents adk web
```

Run tests from repository root:

```bash
PYTHONPATH=. uv run pytest Avatar/test/test_agent.py Avatar/test/test_main.py -q
```

## Quick Health Verification

- `GET /health` should return healthy status.
- `GET /memory?user_id=<id>` should return memory file payload and recent history shape.
- `POST /chat` should return a valid response envelope.
- Startup logs should include `storage_config` with effective `data_dir` and `db_path`.

## Migration Notes From Firebase Version

- Remove Firebase config files and Firebase SDK imports.
- Replace cloud session storage with local SQLite tables.
- Replace cloud function entrypoints with FastAPI app startup.

## Troubleshooting

- Missing API key: verify `.env` load path and variable name.
- Import errors: confirm virtual environment and installed dependencies.
- ADK loader import error (`No module named 'Avatar'`): verify adapter import path uses `from app.agent import create_root_agent` and run ADK with `PYTHONPATH=adk_agents` from Avatar/.
- SQLite lock errors: ensure short-lived connections and proper transaction scope.
- Test import error (`ModuleNotFoundError: No module named 'app'`): run tests with `PYTHONPATH=. uv run pytest ...` from repository root.
