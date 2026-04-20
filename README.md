# Avatar Local Agent OS

這個專案是依照 `gdg-course-design-pattern` 建立的 **Local Agent OS**：

- FastAPI API 層（`/chat`, `/memory`, `/health`）
- SQLite 持久化（sessions / messages / embeddings / compressions）
- Google ADK 多代理流程（Root Coordinator + Orchestrator + Specialists + Flow Templates）
- Markdown 記憶體（`data/identity.md`, `data/soul.md`, `data/startup.md`, `data/master.md`, `data/memory.md`）
- Local Skills（`data/skills/<skill_name>/SKILL.md` + optional `run.py`）

Google ADK 參考：

- [adk.dev](https://adk.dev/)
- [ADK docs](https://adk.dev/docs/)

## 專案結構

```text
Avatar/
├── adk_agents/
│   └── avatar/
│       ├── __init__.py
│       └── agent.py      # ADK web/CLI auto-discovery root agent
├── app/
│   ├── agent.py        # ADK Agent Graph + Tool Guardrails
│   ├── main.py         # FastAPI routes + DB transaction flow
│   └── retrieval.py    # Embedding + top-k retrieval + persistence helpers
├── data/
│   ├── identity.md
│   ├── soul.md
│   ├── startup.md
│   ├── master.md
│   └── memory.md
│   └── skills/         # Local skill registry
├── test/
│   ├── test_agent.py
│   └── test_main.py
├── requirements.txt
└── pyproject.toml
```

## Agent Flow（Google ADK）

```text
AvatarCoordinator (root)
├── ConversationOrchestrator (AgentTool dynamic routing)
│   ├── ContextCollector
│   ├── MemoryRetriever
│   └── ResponseComposer
│   ├── SequentialFlowTemplate
│   ├── ParallelFlowTemplate
│   └── LoopFlowTemplate
└── MemoryMaintenanceAgent
```

流程：

1. `POST /chat` 驗證請求並建立 session。
2. 儲存 user message + embedding。
3. 交給 ADK Runner，讓 orchestrator 透過 `search_memory` / `load_memory` / `read_runtime_context` 與 flow template 工具動態取用 context。
4. 若本回合沒有 ADK retrieval tool 命中，API 會執行 SQLite fallback retrieval 以維持回傳相容性。
5. 儲存 assistant message + embedding。
6. 達到門檻時觸發 compression 並寫入 `compressions`。

## 啟用說明

1. 在專案根目錄建立並設定 `.env`：

```bash
cp .env.example .env
```

2. 在 `.env` 設定 API key（建議用 `GOOGLE_API_KEY`）：

- `GOOGLE_API_KEY`（建議；與 `.env.example` 一致）
- `GEMINI_API_KEY`（相容備援）
- 若兩者同時設定，runtime 會優先使用 `GOOGLE_API_KEY`

3. 安裝依賴：

```bash
uv sync
# 或
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. 啟動 API（建議由 repo root 執行）：

```bash
uvicorn Avatar.app.main:app --reload --port 8000
```

5. 若要啟用 ADK Web（從 `Avatar/` 目錄）：

```bash
PYTHONPATH=adk_agents adk web
```

## API Contract

### `GET /health`

回傳健康狀態。

### `POST /chat`

Request:

```json
{
  "user_id": "string",
  "session_id": "string (optional)",
  "message": "string",
  "metadata": {
    "locale": "zh-TW",
    "channel": "web"
  }
}
```

Success:

```json
{
  "success": true,
  "session_id": "session-...",
  "response": "...",
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0
  },
  "retrieval": {
    "hit_count": 0,
    "sources": []
  }
}
```

### `GET /memory?user_id=...&session_id=...`

Success:

```json
{
  "success": true,
  "memory_files": {
    "identity": "...",
    "soul": "...",
    "startup": "...",
    "master": "...",
    "memory": "..."
  },
  "recent_messages": []
}
```

### Error Envelope

所有非 2xx 回應都使用統一格式：

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "human readable",
    "details": {}
  }
}
```

## 環境設定

必要環境變數：

- `GOOGLE_API_KEY` 或 `GEMINI_API_KEY`：ADK / Gemini 呼叫需要（建議前者）

可選：

- `AVATAR_DATA_DIR`：覆蓋 data 目錄（測試用）
- `AVATAR_DB_PATH`：覆蓋 SQLite 路徑（測試用）
- `STRICT_SENSITIVE_WRITE_GUARD`：是否啟用 `identity.md`/`soul.md` 嚴格寫入保護（預設 `false`；設為 `true` 後才需要顯式授權）

預設資料庫路徑：`data/chat.db`（不是專案根目錄的 `chat.db`）。

## 操作日誌（Observability）

系統會輸出結構化 JSON log（`uvicorn.error` logger），方便追蹤每次操作：

- `operation=%s`：API 級步驟（例如 `/chat` 的 `request_received`、`retrieve_context`、`invoke_agent`、`transaction commit/rollback`、`response_ready`）。
- `tool_execution=%s`：工具級 request/response（`read_file`、`write_file`、`append_file`、`create_file`、`search_memory`），包含 category、status、phase、target/details。
- `tool_activity=%s`：ADK event 解析出的工具呼叫活動（含 terminal/file mutation 類型）。
- `route_decision=%s`：本次 ADK 路由決策與 tool failure 摘要。
- `chat_persisted=%s`：每次 chat 成功 commit 後的 session/message 寫入結果與 `db_path`。

若要確認資料是否真的寫入，優先看同一次請求中的 `chat_persisted` 與 `operation=chat.transaction(commit)`。

## 本機執行

```bash
uvicorn Avatar.app.main:app --reload --port 8000
```

## 測試

```bash
pytest -q
```

## 設計重點

- 不依賴 Firebase/Firestore。
- ADK-first：有 ADK 等價方法時優先使用 ADK 原生工具流程。
- 保持 `identity > soul > master` 的核心提示優先順序；`startup` 作為 runtime/session guidance 在需要時由工具流取用。
- Tool path guardrails 僅允許 `data/`。
- 透過交易確保單次 chat 請求寫入一致性。
- retrieval 排序 deterministic，便於測試與重現。
- 所有 LlmAgent 共享 `GenerateContentConfig`（`automatic_function_calling.disable=true` + `include_server_side_tool_invocations=true`）以確保 built-in tools 正常執行。
