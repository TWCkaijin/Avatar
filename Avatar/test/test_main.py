import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Patch environment variables before importing app
os.environ["AVATAR_DATA_DIR"] = tempfile.mkdtemp()
os.environ["AVATAR_DB_PATH"] = str(Path(os.environ["AVATAR_DATA_DIR"]) / "test.db")

from app.main import app

client = TestClient(app)

def test_health():
    # app.on_event("startup") will be fired by TestClient scope
    with TestClient(app) as c:
        response = c.get("/health")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["status"] == "healthy"

def test_chat_invalid_payload():
    with TestClient(app) as c:
        response = c.post("/chat", json={"user_id": "test", "message": ""})
        # Our explicit raise HTTPException handles "Empty message" and sets code to INVALID_REQUEST
        assert response.status_code == 400
        assert response.json()["success"] is False
        assert response.json()["error"]["code"] == "INVALID_REQUEST"

def test_get_memory_api():
    with TestClient(app) as c:
        response = c.get("/memory", params={"user_id": "test_user"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "identity" in data["memory_files"]
