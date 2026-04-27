import os
import uuid
import datetime
import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.retrieval import init_db, retrieve_top_k, attempt_compression, get_hash_embedding, DEFAULT_DIMENSIONS
from app.agent import _invoke_agent

import re
import base64
import concurrent.futures
from google import genai
from google.genai import types

def process_tts_chunks_sync(text: str):
    parts = re.split(r'<([a-zA-Z_]+)>', text)
    chunks = []
    
    first_text = parts[0].strip()
    if first_text:
        chunks.append({"emotion": "neutral", "text": first_text})
        
    for i in range(1, len(parts), 2):
        emotion = parts[i]
        chunk_text = parts[i+1].strip()
        if chunk_text:
            chunks.append({"emotion": emotion, "text": chunk_text})
            
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # Extract voice config from identity.md
    voice_name = "Aoede"
    try:
        identity_path = Path(AVATAR_DATA_DIR) / "identity.md"
        if identity_path.exists():
            content = identity_path.read_text('utf-8')
            match = re.search(r"##\s*Voice\s*[-:\n\s]*([A-Za-z0-9]+)", content, re.IGNORECASE)
            if match:
                voice_name = match.group(1).strip()
    except Exception as e:
        logger.warning(f"operation=extract_voice error={str(e)}")
        
    allowed_voices = ['achernar', 'achird', 'algenib', 'algieba', 'alnilam', 'aoede', 'autonoe', 
                      'callirrhoe', 'charon', 'despina', 'enceladus', 'erinome', 'fenrir', 'gacrux', 
                      'iapetus', 'kore', 'laomedeia', 'leda', 'orus', 'puck', 'pulcherrima', 
                      'rasalgethi', 'sadachbia', 'sadaltager', 'schedar', 'sulafat', 'umbriel', 
                      'vindemiatrix', 'zephyr', 'zubenelgenubi']
    if voice_name.lower() not in allowed_voices:
        logger.warning(f"Voice {voice_name} is not supported, falling back to Puck")
        voice_name = "Puck"

    def generate_tts(chunk, chunk_index, model_name):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f'Read the following text exactly as written: "{chunk["text"]}"',
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config={"voice_config": {"prebuilt_voice_config": {"voice_name": voice_name}}} # type: ignore
                )
            )
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        audio_b64 = base64.b64encode(part.inline_data.data).decode('utf-8') # type: ignore
                        return {
                            "chunk_index": chunk_index,
                            "emotion": chunk["emotion"],
                            "text": chunk["text"],
                            "audio_b64": audio_b64,
                            "mime_type": "audio/pcm; rate=24000"
                        }
        except Exception as e:
            return {"chunk_index": chunk_index, "emotion": chunk["emotion"], "text": chunk["text"], "error": str(e)}
        return {"chunk_index": chunk_index, "emotion": chunk["emotion"], "text": chunk["text"], "error": "No audio returned"}

    emotion_chunks_result = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        for i, chunk in enumerate(chunks):
            if i < 3:
                model = 'gemini-3.1-flash-tts-preview'
            elif i < 6:
                model = 'gemini-2.5-flash-preview-tts'
            else:
                emotion_chunks_result.append({
                    "chunk_index": i,
                    "emotion": chunk["emotion"],
                    "text": chunk["text"],
                    "error": "Rate limit: Exceeded maximum TTS calls per request (limit 6)"
                })
                continue
                
            futures.append(executor.submit(generate_tts, chunk, i, model))
            
        for future in concurrent.futures.as_completed(futures):
            emotion_chunks_result.append(future.result())
            
    emotion_chunks_result.sort(key=lambda x: x["chunk_index"])
    return emotion_chunks_result

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")
google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not google_api_key:
    raise RuntimeError("Missing GOOGLE_API_KEY (or GEMINI_API_KEY) in .env")

AVATAR_DATA_DIR = os.getenv("AVATAR_DATA_DIR", str(REPO_ROOT / "Avatar" / "data"))
AVATAR_DB_PATH = os.getenv("AVATAR_DB_PATH", str(Path(AVATAR_DATA_DIR) / "chat.db"))

MAX_MESSAGE_BYTES = 64 * 1024

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Avatar Local Agent OS")

cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
cors_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    os.makedirs(AVATAR_DATA_DIR, exist_ok=True)
    os.makedirs(Path(AVATAR_DATA_DIR) / "skills", exist_ok=True)
    
    # Ensure baseline markdown files exist
    for filename in ["identity.md", "soul.md", "startup.md", "master.md", "memory.md"]:
        fp = Path(AVATAR_DATA_DIR) / filename
        if not fp.exists():
            fp.touch(exist_ok=True)
            
    init_db(AVATAR_DB_PATH)
    logger.info(f"storage_config={json.dumps({'data_dir': AVATAR_DATA_DIR, 'db_path': AVATAR_DB_PATH})}")

def create_error_envelope(code: str, message: str, details: Optional[Dict[str, Any]] = None):
    return {"success": False, "error": {"code": code, "message": message, "details": details or {}}}

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"operation=generic_exception_handler error={str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content=create_error_envelope("INTERNAL_ERROR", str(exc)))

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"operation=http_exception_handler status_code={exc.status_code} detail={exc.detail}")
    code_map = {400: "INVALID_REQUEST", 403: "UNAUTHORIZED_PATH", 404: "NOT_FOUND", 500: "INTERNAL_ERROR", 502: "MODEL_RUNTIME_ERROR"}
    code = code_map.get(exc.status_code, "INTERNAL_ERROR")
    return JSONResponse(status_code=exc.status_code, content=create_error_envelope(code, exc.detail))

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"operation=validation_exception_handler errors={exc.errors()}")
    return JSONResponse(status_code=400, content=create_error_envelope("INVALID_REQUEST", "Validation Error", {"errors": exc.errors()}))

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/health")
def health_check():
    logger.info("operation=health.check success=true")
    return {
        "success": True,
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@app.post("/chat")
def chat(req: ChatRequest):
    logger.info(f"operation=chat.receive_message user_id={req.user_id} session_id={req.session_id} message_length={len(req.message) if req.message else 0}")
    if not req.user_id or len(req.user_id) > 128:
        logger.warning(f"operation=chat.validation_failed reason='Invalid user_id' user_id={req.user_id}")
        raise HTTPException(status_code=400, detail="Invalid user_id")
    if not req.message or not req.message.strip():
        logger.warning(f"operation=chat.validation_failed reason='Empty message' user_id={req.user_id}")
        raise HTTPException(status_code=400, detail="Empty message")
    if len(req.message.encode('utf-8')) > MAX_MESSAGE_BYTES:
        logger.warning(f"operation=chat.validation_failed reason='Message exceeds limit' user_id={req.user_id}")
        raise HTTPException(status_code=400, detail="Message exceeds 64KB UTF-8 limit")
    
    session_id = req.session_id if req.session_id else f"session-{uuid.uuid4().hex}"
    logger.info(f"operation=chat.session_established user_id={req.user_id} session_id={session_id}")
    
    conn = sqlite3.connect(AVATAR_DB_PATH)
    try:
        conn.execute("BEGIN")
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        cursor.execute('''
            INSERT INTO sessions (session_id, user_id, created_at, updated_at) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at
        ''', (session_id, req.user_id, now, now))
        
        cursor.execute('''
            INSERT INTO messages (session_id, user_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, req.user_id, 'user', req.message, now))
        user_message_id = cursor.lastrowid
        
        vec = get_hash_embedding(req.message, DEFAULT_DIMENSIONS)
        cursor.execute('''
            INSERT INTO embeddings (message_id, source_type, source_ref, model, dimensions, vector_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_message_id, 'message', str(user_message_id), 'local-hash-embedding-v1', DEFAULT_DIMENSIONS, json.dumps(vec), now))
        
        try:
            logger.info("operation=chat.invoke_agent")
            agent_result = _invoke_agent(req.message, session_id, req.user_id)
        except Exception as e:
            logger.error(f"operation=chat.invoke_agent error={str(e)}")
            raise HTTPException(status_code=502, detail=f"ADK Runtime Error: {str(e)}")
            
        final_text = agent_result.get('response', '')
        if not final_text:
            raise HTTPException(status_code=500, detail="ADK returned empty response")
            
        retrieval_meta = {"hit_count": 0, "sources": []}
        if agent_result.get('adk_tool_used'):
            retrieval_meta = agent_result.get('retrieval', retrieval_meta)
        else:
            sources = retrieve_top_k(AVATAR_DB_PATH, req.message, exclude_message_id=user_message_id or -1)
            retrieval_meta['sources'] = sources
            retrieval_meta['hit_count'] = len(sources)
            
        assistant_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        cursor.execute('''
            INSERT INTO messages (session_id, user_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, req.user_id, 'model', final_text, assistant_now))
        assistant_message_id = cursor.lastrowid
        
        vec_ast = get_hash_embedding(final_text, DEFAULT_DIMENSIONS)
        cursor.execute('''
            INSERT INTO embeddings (message_id, source_type, source_ref, model, dimensions, vector_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (assistant_message_id, 'message', str(assistant_message_id), 'local-hash-embedding-v1', DEFAULT_DIMENSIONS, json.dumps(vec_ast), assistant_now))
        
        attempt_compression(conn, session_id)
        conn.commit()
        
        logger.info(f"chat_persisted={json.dumps({'db_path': AVATAR_DB_PATH, 'user_id': req.user_id, 'session_id': session_id, 'user_message_id': user_message_id, 'assistant_message_id': assistant_message_id})}")
        
        emotion_chunks = process_tts_chunks_sync(final_text)

        logger.info(f"operation=chat.send_message user_id={req.user_id} session_id={session_id} response_length={len(final_text)}")
        usage_data = agent_result.get('usage')
        if usage_data is None:
            usage_data = {"prompt_tokens": 0, "completion_tokens": 0}
        
        return {
            "success": True,
            "session_id": session_id,
            "response": final_text,
            "emotion_chunks": emotion_chunks,
            "usage": usage_data,
            "retrieval": retrieval_meta
        }
        
    except HTTPException as e:
        conn.rollback()
        logger.warning(f"operation=chat.http_exception status_code={e.status_code} detail={e.detail}")
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"operation=chat.unexpected_error error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/memory")
def get_memory(user_id: str, session_id: Optional[str] = None):
    logger.info(f"operation=get_memory.receive_request user_id={user_id} session_id={session_id}")
    limit = 50
    memory_files = {}
    for mf in ['identity.md', 'soul.md', 'startup.md', 'master.md', 'memory.md']:
        fpath = Path(AVATAR_DATA_DIR) / mf
        if fpath.exists():
            memory_files[mf.replace('.md', '')] = fpath.read_text('utf-8')
        else:
            memory_files[mf.replace('.md', '')] = ""
            
    recent_messages = []
    with sqlite3.connect(AVATAR_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute('SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?', (session_id, limit))
        else:
            cursor.execute('SELECT role, content, created_at FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?', (user_id, limit))
            
        for r in cursor.fetchall():
            recent_messages.append({"role": r['role'], "content": r['content'], "created_at": r['created_at']})
            
    logger.info(f"operation=get_memory.send_response user_id={user_id} session_id={session_id} messages_count={len(recent_messages)}")
    return {
        "success": True,
        "memory_files": memory_files,
        "recent_messages": recent_messages
    }

# Serve static files at the root
STATIC_DIR = os.getenv("AVATAR_STATIC_DIR", str(REPO_ROOT / "Avatar" / "static"))
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    logger.warning(f"operation=startup.static_mount_failed reason='Directory not found' path={STATIC_DIR}")
