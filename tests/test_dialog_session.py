import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys


@pytest.fixture(scope="function")
def test_db():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def client(test_db):
    def mock_embed_text(text: str):
        import math
        if "blue shirt" in text:
            v = [0.0] * 1536
            v[0] = 1.0
            return v
        elif "red shirt" in text:
            v = [0.0] * 1536
            v[1] = 1.0
            return v
        elif "What color shirt did I wear?" in text:
            v = [0.0] * 1536
            v[0] = 1.0 / math.sqrt(2)
            v[1] = 1.0 / math.sqrt(2)
            return v
        else:
            v = [0.0] * 1536
            v[100] = 1.0
            return v

    mock_openai_client = MagicMock()
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock()]
    mock_embedding_response.data[0].embedding = [0.1] * 1536
    mock_openai_client.embeddings.create.return_value = mock_embedding_response

    with patch('openai.OpenAI', return_value=mock_openai_client):
        modules_to_clear = [m for m in sys.modules.keys() if m.startswith('agent')]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        from agent.config import Settings
        test_settings = Settings(
            openai_api_key="sk-test-key-for-dialog",
            db_path=test_db,
            host="0.0.0.0",
            port=5000,
            cors_origins=["http://localhost:3000"],
            log_level="INFO",
            app_name="Marvin Memory Service",
            app_version="1.0.0"
        )

        with patch('agent.config.settings', test_settings), \
             patch('agent.memory.embed_text', side_effect=mock_embed_text):
            from agent.main import app
            from agent.memory import init_db
            init_db()
            with TestClient(app) as test_client:
                yield test_client


class TestBlueRedShirtDialog:
    def test_multi_turn_dialog(self, client):
        blue_payload = {"text": "I wore a blue shirt yesterday", "language": "he"}
        red_payload = {"text": "I wore a red shirt yesterday", "language": "he"}

        store_blue = client.post("/api/v1/store", json=blue_payload)
        assert store_blue.status_code == 201
        blue_id = store_blue.json()["memory_id"]

        store_red = client.post("/api/v1/store", json=red_payload)
        assert store_red.status_code == 201
        red_id = store_red.json()["memory_id"]

        query_payload = {"query": "What color shirt did I wear?"}
        query_resp = client.post("/api/v1/query", json=query_payload)
        assert query_resp.status_code == 200
        data = query_resp.json()
        assert data.get("clarification_required") is True
        assert "session_id" in data
        session_id = data["session_id"]
        candidates = data["candidates"]
        ids = {c["memory_id"] for c in candidates}
        assert blue_id in ids and red_id in ids

        chosen = [c for c in candidates if "blue shirt" in c["text"]][0]
        clarify_payload = {
            "session_id": session_id,
            "query": "What color shirt did I wear?",
            "chosen_memory_id": chosen["memory_id"],
        }
        clarify_resp = client.post("/api/v1/clarify", json=clarify_payload)
        assert clarify_resp.status_code == 200
        clarify_data = clarify_resp.json()
        assert clarify_data["clarification_resolved"] is True
        assert clarify_data["memory_id"] == chosen["memory_id"]
        assert "blue shirt" in clarify_data["text"]
