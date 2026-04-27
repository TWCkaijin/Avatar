import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv


from google.adk.agents import Agent as LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools.agent_tool import AgentTool
from google.genai.types import GenerateContentConfig


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")
AVATAR_DATA_DIR = os.getenv("AVATAR_DATA_DIR", str(REPO_ROOT / "Avatar" / "data"))
MAX_FILE_BYTES = 512 * 1024

AGENT_MODEL = "gemini-3-flash-preview"
AGENT_GENERATE_CONTENT_CONFIG = GenerateContentConfig(
    automatic_function_calling={"disable": True}, # type: ignore
    tool_config={"include_server_side_tool_invocations": True} # type: ignore
) # type: ignore

logger = logging.getLogger("uvicorn.error")

def load_system_instruction() -> str:
    parts = []
    # 讀取身分、靈魂、使用者印象以及歷史記憶
    for f in ['identity.md', 'soul.md', 'master.md', 'memory.md']:
        p = Path(AVATAR_DATA_DIR) / f
        if p.exists():
            parts.append(p.read_text('utf-8'))
            
    skills_dir = Path(AVATAR_DATA_DIR) / "skills"
    skills = []
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                skills.append(d.name)
    if skills:
        parts.append("Available Local Skills: " + ", ".join(skills))
    else:
        parts.append("No local skills available.")
    
    parts.append("Purpose routing: role->identity.md, user facts->master.md, timeline->memory.md, personality->soul.md.")
    return "\n\n".join(parts)


def read_file(path: str) -> str:
    target = Path(AVATAR_DATA_DIR) / path
    if not str(target.resolve()).startswith(str(Path(AVATAR_DATA_DIR).resolve())):
         return "TOOL_PERMISSION_DENIED"
    try:
        content = target.read_text('utf-8')
        if len(content.encode('utf-8')) > MAX_FILE_BYTES:
             return "TOOL_IO_ERROR: oversized"
        return content
    except Exception as e:
        return f"TOOL_IO_ERROR: {str(e)}"

def write_file(path: str, content: str) -> str:
    target = Path(AVATAR_DATA_DIR) / path
    if not str(target.resolve()).startswith(str(Path(AVATAR_DATA_DIR).resolve())):
         return "TOOL_PERMISSION_DENIED"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, 'utf-8')
        logger.info(f"tool_activity=file_mutation phase=response status=success path={path}")
        return "Success"
    except Exception as e:
        return f"TOOL_IO_ERROR: {str(e)}"

def append_file(path: str, content: str) -> str:
    target = Path(AVATAR_DATA_DIR) / path
    if not str(target.resolve()).startswith(str(Path(AVATAR_DATA_DIR).resolve())):
         return "TOOL_PERMISSION_DENIED"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'a', encoding='utf-8') as f:
            if not content.startswith('\n'):
                f.write('\n')
            f.write(content)
        return "Success"
    except Exception as e:
        return f"TOOL_IO_ERROR: {str(e)}"

def create_file(path: str, content: str) -> str:
    target = Path(AVATAR_DATA_DIR) / path
    if not str(target.resolve()).startswith(str(Path(AVATAR_DATA_DIR).resolve())):
         return "TOOL_PERMISSION_DENIED"
    if target.exists():
        return "TOOL_VALIDATION_ERROR: File already exists"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, 'utf-8')
        return "Success"
    except Exception as e:
        return f"TOOL_IO_ERROR: {str(e)}"

def search_memory(query: str) -> str:
    from app.retrieval import retrieve_top_k
    db_path = os.getenv("AVATAR_DB_PATH", str(Path(AVATAR_DATA_DIR) / "chat.db"))
    if not Path(db_path).exists():
        return "[]"
    try:
        res = retrieve_top_k(db_path, query)
        logger.info(f"tool_activity=memory_retrieval phase=response status=success")
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return f"TOOL_RUNTIME_ERROR: {str(e)}"

def list_skills() -> str:
    skills_dir = Path(AVATAR_DATA_DIR) / "skills"
    res = []
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                res.append({
                    "name": d.name,
                    "summary": "Local Skill",
                    "path": str(d.name),
                    "has_entrypoint": (d / "run.py").exists(),
                    "entrypoint": "run.py" if (d / "run.py").exists() else None
                })
    return json.dumps(res, ensure_ascii=False)

def read_skill(skill_name: str) -> str:
    import re
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$", skill_name):
        return "TOOL_VALIDATION_ERROR"
    target = Path(AVATAR_DATA_DIR) / "skills" / skill_name / "SKILL.md"
    if target.exists():
        content = target.read_text('utf-8')
        if len(content.encode('utf-8')) > MAX_FILE_BYTES:
            return "TOOL_IO_ERROR: oversized"
        return content
    return "TOOL_IO_ERROR: not found"

def create_skill(skill_name: str, skill_markdown: str, python_code: str = "") -> str:
    import re
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$", skill_name):
        return "TOOL_VALIDATION_ERROR"
    if not skill_markdown.startswith("---") or "---" not in skill_markdown[3:]:
        return "TOOL_VALIDATION_ERROR: missing frontmatter"
    if len(skill_markdown.encode('utf-8')) > MAX_FILE_BYTES or len(skill_markdown) > 4096:
        return "TOOL_VALIDATION_ERROR: oversized"
        
    target_dir = Path(AVATAR_DATA_DIR) / "skills" / skill_name
    if target_dir.exists():
        return "TOOL_VALIDATION_ERROR: duplicate skill"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "SKILL.md").write_text(skill_markdown, 'utf-8')
        if python_code:
            (target_dir / "run.py").write_text(python_code, 'utf-8')
        logger.info(f"tool_execution=create_skill status=success skill={skill_name}")
        return "Success"
    except Exception as e:
        logger.info(f"tool_execution=create_skill status=error error={str(e)}")
        return f"TOOL_IO_ERROR: {str(e)}"

def execute_skill(skill_name: str, input_json: str = "{}") -> str:
    import subprocess
    import sys
    target = Path(AVATAR_DATA_DIR) / "skills" / skill_name / "run.py"
    if not target.exists():
        return "TOOL_VALIDATION_ERROR"
    try:
        env = os.environ.copy()
        env['AVATAR_SKILL_INPUT_JSON'] = input_json
        res = subprocess.run(
            [sys.executable, str(target)], 
            input=input_json, 
            text=True, 
            capture_output=True, 
            env=env,
            timeout=int(os.getenv("SKILL_EXEC_TIMEOUT_SECONDS", "20"))
        )
        if res.returncode != 0:
            return f"TOOL_RUNTIME_ERROR: {res.stderr}"
        return res.stdout or "{}"
    except subprocess.TimeoutExpired:
         return "TOOL_RUNTIME_ERROR: Timeout"
    except Exception as e:
        return f"TOOL_RUNTIME_ERROR: {str(e)}"
        
def preload_memory() -> str:
    """初始化載入記憶時間線"""
    return load_memory()

def load_memory() -> str:
    """從 memory.md 讀取完整的歷史記憶時間線"""
    p = Path(AVATAR_DATA_DIR) / "memory.md"
    if p.exists():
        try:
            return p.read_text('utf-8')
        except Exception as e:
            return f"Error reading memory: {str(e)}"
    return "No memory timeline (memory.md) found."

def read_runtime_context(tool_context=None) -> str:
    return json.dumps({
        "session_state": {},
        "runtime_flags": {"user_id": "system", "session_id": "system"}
    })

def google_search(query: str) -> str:
    return "Search results disabled"

BASE_TOOLS = [google_search]
MEMORY_OP_TOOLS = [read_file, write_file, append_file, create_file]
COMPOSER_TOOLS = [load_memory, read_runtime_context, list_skills, read_skill, create_skill, execute_skill] + MEMORY_OP_TOOLS

def create_memory_maintenance_agent() -> LlmAgent:
    sys_inst = load_system_instruction()
    # 將 Agent 的 Instruction 再強化，明確告訴他有責任維護和更新 markdown 檔案
    extended_inst = sys_inst + "\n\nCRITICAL INSTRUCTION FOR MEMORY MAINTENANCE:\nYou are the Memory Maintenance Agent. Your primary responsibility is to read, write, and update the markdown memory files (identity.md, soul.md, master.md, memory.md) using your tools. When requested to update facts, personality, or identity, YOU MUST USE THE write_file OR append_file tools to modify these files. DO NOT just answer the user; YOU MUST actually execute the file modification tools."
    return LlmAgent(
        name="MemoryMaintenanceAgent",
        model=AGENT_MODEL,
        instruction=extended_inst,
        tools=BASE_TOOLS + MEMORY_OP_TOOLS, # type: ignore
        generate_content_config=AGENT_GENERATE_CONTENT_CONFIG,
        output_key="memory_update_status"
    )

def create_root_agent() -> LlmAgent:
    sys_inst = load_system_instruction()
    
    # 1. 核心流程代理人 (Core Pipeline Agents)
    ContextCollector = LlmAgent(name="ContextCollector", model=AGENT_MODEL, instruction=sys_inst + "\nYou are the Context Collector. Gather all relevant context from the current session state.", tools=BASE_TOOLS + [load_memory, read_runtime_context], generate_content_config=AGENT_GENERATE_CONTENT_CONFIG, output_key="collected_context") # type: ignore
    MemoryRetriever = LlmAgent(name="MemoryRetriever", model=AGENT_MODEL, instruction=sys_inst + "\nYou are the Memory Retriever. Search historical memory using search_memory tool based on collected context.", tools=BASE_TOOLS + [search_memory, load_memory], generate_content_config=AGENT_GENERATE_CONTENT_CONFIG, output_key="retrieval_context") # type: ignore
    ResponseComposer = LlmAgent(name="ResponseComposer", model=AGENT_MODEL, instruction=sys_inst + "\nYou are the final Response Composer. Synthesize all outputs from the session state (collected_context, retrieval_context, research_result, file_result) into a final answer. Remember to use emotion tags.", tools=BASE_TOOLS + COMPOSER_TOOLS, generate_content_config=AGENT_GENERATE_CONTENT_CONFIG, output_key="final_response") # type: ignore

    # 2. 建立各種專家代理人 (Specialists)
    ResearchSpecialist = LlmAgent(
        name="ResearchSpecialist", 
        model=AGENT_MODEL, 
        instruction=sys_inst + "\n\nYou are a Research Specialist. Your job is to search the internet or use available context to answer factual questions. Do not guess; use your tools.", 
        tools=BASE_TOOLS + [search_memory, load_memory], # type: ignore
        generate_content_config=AGENT_GENERATE_CONTENT_CONFIG, 
        output_key="research_result"
    ) # type: ignore
    
    FileSpecialist = LlmAgent(
        name="FileSpecialist", 
        model=AGENT_MODEL, 
        instruction=sys_inst + "\n\nYou are a File Specialist. Your job is to read and manage files in the workspace (except critical memory files like identity.md, soul.md).", 
        tools=BASE_TOOLS + [read_file, list_skills], # type: ignore
        generate_content_config=AGENT_GENERATE_CONTENT_CONFIG, 
        output_key="file_result"
    ) # type: ignore
    
    maint = create_memory_maintenance_agent()
    
    # 3. 定義 Root Agent 的動態路由指令 (Planner / Orchestrator)
    root_inst = sys_inst + """
    
CRITICAL INSTRUCTION: You are the Avatar OS Root Coordinator. You act as a Planner and Orchestrator. You MUST analyze the user's request and route the task to the appropriate sub-agents. 

Available Core Agents (Use for standard answering pipeline):
- ContextCollector: To gather current session context.
- MemoryRetriever: To pull relevant historical memory.
- ResponseComposer: To write the final answer.

Available Specialists (Use for specific actions):
- ResearchSpecialist: For finding external facts or deep searching memory.
- FileSpecialist: For reading workspace files and listing skills.
- MemoryMaintenanceAgent: For updating system memory files (identity.md, soul.md, master.md, memory.md).

How to work:
1. For simple questions, you can route to ResponseComposer directly.
2. For complex answering, use the core pipeline: ContextCollector -> MemoryRetriever -> ResponseComposer.
3. If the user asks to modify identity, rules, or personality, you MUST use the MemoryMaintenanceAgent.
4. If a specific file needs reading, use FileSpecialist. If deep factual checking is needed, use ResearchSpecialist.
5. ALWAYS ensure that ResponseComposer is called at the end to generate the final response with emotion tokens.
    """
    
    AvatarCoordinator = LlmAgent(
        name="AvatarCoordinator",
        model=AGENT_MODEL,
        instruction=root_inst,
        tools=BASE_TOOLS + [ # type: ignore
            preload_memory,
            AgentTool(ContextCollector),
            AgentTool(MemoryRetriever),
            AgentTool(ResponseComposer),
            AgentTool(ResearchSpecialist),
            AgentTool(FileSpecialist),
            AgentTool(maint)
        ],
        generate_content_config=AGENT_GENERATE_CONTENT_CONFIG
    )
    return AvatarCoordinator

def _invoke_agent(message: str, session_id: str, user_id: str) -> dict:
    from google.genai.types import Content, Part
    root_agent = create_root_agent()
    runner = Runner(
        app_name="avatar_local_agent",
        agent=root_agent,
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
        auto_create_session=True
    )
    
    run_config = RunConfig(
        custom_metadata={"context_strategy": "adk_tool_first"}
    )
    
    result = list(runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(parts=[Part.from_text(text=message)], role='user'),
        run_config=run_config
    ))
    # Search for the final response in the events
    output = ""
    for event in result:
        usage = getattr(event, "usage_metadata", None)
        token_count = getattr(usage, "total_token_count", None) if usage else None
        logger.info(
            "adk_event_summary author=%s partial=%s finish_reason=%s tokens=%s",
            getattr(event, "author", None),
            getattr(event, "partial", None),
            getattr(event, "finish_reason", None),
            token_count,
        )
        if getattr(event, "is_final_response", lambda: False)():
            logger.info("Found final response event!")
            if getattr(event, "content", None) and getattr(event.content, "parts", None):
                for part in event.content.parts: # type: ignore
                    text = getattr(part, "text", None)
                    if isinstance(text, str) and text.strip():
                        output += text.strip() + " "
    
    return {"response": output.strip(), "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
