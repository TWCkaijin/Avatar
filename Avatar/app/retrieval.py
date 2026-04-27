import hashlib
import sqlite3
import json
import math
import datetime
from typing import List, Dict, Any, Optional

DEFAULT_DIMENSIONS = 64

def get_hash_embedding(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> List[float]:
    """Generates a deterministic normalized embedding from blake2b hash."""
    h = hashlib.blake2b(digest_size=min(dimensions, 64))
    h.update(text.encode('utf-8', errors='ignore'))
    digest = h.digest()
    
    vec = []
    for i in range(dimensions):
        val = digest[i % len(digest)]
        vec.append(float(val) - 127.5)
        
    magnitude = math.sqrt(sum(v ** 2 for v in vec))
    if magnitude == 0:
        return [0.0] * dimensions
    return [v / magnitude for v in vec]

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))

def init_db(db_path: str):
    """Idempotently initialize the DB schema."""
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        
        conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            compressed INTEGER NOT NULL DEFAULT 0
        )''')
        
        conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_created ON messages(user_id, created_at)')
        
        conn.execute('''
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            source_type TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            vector_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )''')
        
        conn.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_source ON embeddings(source_type, source_ref)')
        
        conn.execute('''
        CREATE TABLE IF NOT EXISTS compressions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            from_message_id INTEGER NOT NULL,
            to_message_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            created_at TEXT NOT NULL
        )''')

def retrieve_top_k(db_path: str, query: str, top_k: int = 5, exclude_message_id: Optional[int] = None) -> List[Dict[str, Any]]:
    query_vec = get_hash_embedding(query, DEFAULT_DIMENSIONS)
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.id, e.message_id, e.source_type, e.source_ref, e.vector_json,
                   m.content, m.role
            FROM embeddings e
            LEFT JOIN messages m ON e.message_id = m.id
            ORDER BY e.created_at DESC
            LIMIT 256
        ''')
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            if exclude_message_id is not None and row['message_id'] == exclude_message_id:
                continue
            
            vec = json.loads(row['vector_json'])
            score = round(cosine_similarity(query_vec, vec), 6)
            
            content = row['content']
            snippet = content[:240] if content else ""
            
            results.append({
                'source_type': row['source_type'],
                'source_ref': row['source_ref'],
                'score': score,
                'snippet': snippet,
                'role': row['role']
            })
            
        results.sort(key=lambda x: (-x['score'], x['source_type'], x['source_ref']))
        return results[:min(top_k, 12)]

def attempt_compression(conn: sqlite3.Connection, session_id: str):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, role, content 
        FROM messages 
        WHERE session_id = ? AND compressed = 0 
        ORDER BY id ASC
    ''', (session_id,))
    
    rows = cursor.fetchall()
    
    # Check if rows are sqlite3.Row objects (dict-like) or raw tuples
    is_dict_like = len(rows) > 0 and hasattr(rows[0], 'keys')
    
    if len(rows) < 24:
        # Check if the content is not None before checking length to avoid TypeError
        if is_dict_like:
            total_chars = sum(len(r['content']) for r in rows if r['content'])
        else:
            # Tuples from 'SELECT id, role, content' have content at index 2
            total_chars = sum(len(r[2]) for r in rows if r[2])
            
        if total_chars < 12000:
            return
            
    compress_count = min(max(len(rows) // 2, 8), 16)
    if compress_count == 0:
        return
        
    selected = rows[:compress_count]
    if is_dict_like:
        from_id = selected[0]['id']
        to_id = selected[-1]['id']
    else:
        from_id = selected[0][0]
        to_id = selected[-1][0]
    
    summary_lines = []
    for r in selected:
        if is_dict_like:
            role = r['role']
            content = r['content'].replace('\\n', ' ') if r['content'] else ""
        else:
            role = r[1]
            content = r[2].replace('\\n', ' ') if r[2] else ""
            
        summary_lines.append(f"{role}: {content[:140]}")
    
    summary_text = "\\n".join(summary_lines)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    cursor.execute('''
        INSERT INTO compressions (session_id, from_message_id, to_message_id, summary, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, from_id, to_id, summary_text, now))
    compression_id = cursor.lastrowid
    
    ids_to_mark = [r['id'] for r in selected]
    placeholders = ",".join("?" * len(ids_to_mark))
    cursor.execute(f'UPDATE messages SET compressed = 1 WHERE id IN ({placeholders})', ids_to_mark)
    
    # Store summary as a system message
    # using 'system' user_id to identify it's a structural bot event rather than the individual user
    cursor.execute('''
        INSERT INTO messages (session_id, user_id, role, content, created_at, compressed)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (session_id, 'system', 'system', summary_text, now))
    sys_msg_id = cursor.lastrowid
    
    vec = get_hash_embedding(summary_text, DEFAULT_DIMENSIONS)
    cursor.execute('''
        INSERT INTO embeddings (message_id, source_type, source_ref, model, dimensions, vector_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (sys_msg_id, "summary", f"compression:{compression_id}", "local-hash-embedding-v1", DEFAULT_DIMENSIONS, json.dumps(vec), now))
