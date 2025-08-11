# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestReadOnlyEndpoints:
    """Test suite for read-only memory endpoints."""

    def one_hot_embed(self, text: str, dim: int = 1536) -> list[float]:
        """Generate deterministic one-hot vector based on text hash."""
        idx = abs(hash(text)) % dim
        v = [0.0] * dim
        v[idx] = 1.0
        return v

    @pytest.fixture
    def test_db(self):
        """Create a temporary database for each test."""
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db.close()
        return temp_db.name

    @pytest.fixture
    def client(self, test_db):
        """Create a TestClient with isolated database and mocked dependencies."""
        # Create mock settings with API auth enabled
        from agent.config import Settings
        mock_settings = Settings(
            openai_api_key="sk-test-key-for-testing-only",
            db_path=test_db,
            api_auth_key="test-secret"
        )

        # Mock OpenAI client
        mock_openai_client = MagicMock()
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock()]
        mock_embedding_response.data[0].embedding = [0.1] * 1536  # Simple constant vector
        mock_openai_client.embeddings.create.return_value = mock_embedding_response

        # Clear module cache to force re-import with mocks
        modules_to_clear = [key for key in sys.modules.keys() if key.startswith('agent')]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        with patch('openai.OpenAI', return_value=mock_openai_client), \
             patch('agent.config.settings', mock_settings), \
             patch('agent.memory.embed_text', side_effect=lambda s: self.one_hot_embed(s)):

            # Import after patching
            from agent.main import app
            from agent.memory import init_db

            # Initialize the test database
            init_db()

            yield TestClient(app)

    def test_list_memories_returns_all_items(self, client):
        """Test that list memories endpoint returns all stored items."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Store three distinct memories
        memory_texts = [
            "First memory for list test",
            "Second memory for list test", 
            "Third memory for list test"
        ]
        
        stored_ids = []
        for text in memory_texts:
            store_payload = {
                "text": text,
                "language": "en"
            }
            store_response = client.post("/api/v1/store", json=store_payload, headers=headers)
            assert store_response.status_code == 201
            store_data = store_response.json()
            stored_ids.append(store_data["memory_id"])
        
        # GET /api/v1/memories with auth header
        list_response = client.get("/api/v1/memories", headers=headers)
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        
        # Assert structure and count
        assert "total_memories" in list_data
        assert "memories" in list_data
        assert list_data["total_memories"] == 3
        assert len(list_data["memories"]) == 3
        
        # Assert each memory has required fields
        for memory in list_data["memories"]:
            assert "memory_id" in memory
            assert "text" in memory
            assert memory["memory_id"] is not None
            assert memory["text"] is not None
            # similarity_score is optional for list view

    def test_get_memory_by_id_returns_item(self, client):
        """Test that get memory by ID returns the correct item."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Store one memory
        store_payload = {
            "text": "Memory for ID retrieval test",
            "language": "en"
        }
        
        store_response = client.post("/api/v1/store", json=store_payload, headers=headers)
        assert store_response.status_code == 201
        store_data = store_response.json()
        memory_id = store_data["memory_id"]
        
        # GET /api/v1/memories/{id} with auth header
        get_response = client.get(f"/api/v1/memories/{memory_id}", headers=headers)
        assert get_response.status_code == 200
        
        get_data = get_response.json()
        
        # Assert structure and content
        assert "memory_id" in get_data
        assert "text" in get_data
        assert get_data["memory_id"] == memory_id
        assert get_data["text"] == "Memory for ID retrieval test"

    def test_get_memory_by_id_404_when_missing(self, client):
        """Test that get memory by ID returns 404 for non-existent ID."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Use a random UUID that doesn't exist
        random_id = str(uuid.uuid4())
        
        # GET /api/v1/memories/{random_id} with auth header
        get_response = client.get(f"/api/v1/memories/{random_id}", headers=headers)
        assert get_response.status_code == 404
        
        error_data = get_response.json()
        
        # Assert clear error body
        assert "detail" in error_data or "error" in error_data
        
        # Error message should be meaningful
        error_message = error_data.get("detail") or error_data.get("error", "")
        assert isinstance(error_message, str)
        assert len(error_message) > 0

    def test_export_returns_full_snapshot(self, client):
        """Test that export endpoint returns complete memory snapshot."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Store two memories with different languages and locations
        memories_to_store = [
            {"text": "First export memory", "language": "en", "location": "office"},
            {"text": "Second export memory", "language": "he", "location": None}
        ]
        
        for memory_data in memories_to_store:
            store_response = client.post("/api/v1/store", json=memory_data, headers=headers)
            assert store_response.status_code == 201
        
        # GET /api/v1/export with auth header
        export_response = client.get("/api/v1/export", headers=headers)
        assert export_response.status_code == 200
        
        export_data = export_response.json()
        
        # Assert structure and count
        assert "count" in export_data
        assert "items" in export_data
        assert export_data["count"] == 2
        assert len(export_data["items"]) == 2
        
        # Assert each item has all required fields
        for item in export_data["items"]:
            assert "id" in item
            assert "text" in item
            assert "timestamp" in item
            assert "language" in item
            assert "location" in item  # Can be null but should be present
            
            # Validate field types and presence
            assert isinstance(item["id"], str)
            assert isinstance(item["text"], str)
            assert isinstance(item["timestamp"], str)
            assert isinstance(item["language"], str)
            # location can be str or None
            assert item["location"] is None or isinstance(item["location"], str)
            
            # Validate non-empty strings
            assert len(item["id"]) > 0
            assert len(item["text"]) > 0
            assert len(item["timestamp"]) > 0
            assert len(item["language"]) > 0

    def test_readonly_endpoints_require_auth_when_enabled(self, client):
        """Test that read-only endpoints require authentication when API key is set."""
        # Store one memory first (with auth) to have data for testing
        headers = {"X-API-KEY": "test-secret"}
        store_payload = {
            "text": "Memory for auth testing",
            "language": "en"
        }
        store_response = client.post("/api/v1/store", json=store_payload, headers=headers)
        assert store_response.status_code == 201
        memory_id = store_response.json()["memory_id"]
        
        # Test GET /api/v1/memories without header
        list_response = client.get("/api/v1/memories")
        assert list_response.status_code == 401
        
        list_error = list_response.json()
        assert "detail" in list_error or "error" in list_error
        
        # Test GET /api/v1/memories/{id} without header
        get_response = client.get(f"/api/v1/memories/{memory_id}")
        assert get_response.status_code == 401
        
        get_error = get_response.json()
        assert "detail" in get_error or "error" in get_error
        
        # Test GET /api/v1/export without header
        export_response = client.get("/api/v1/export")
        assert export_response.status_code == 401
        
        export_error = export_response.json()
        assert "detail" in export_error or "error" in export_error