# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestMemoriesPagination:
    """Test suite for memory listing pagination functionality."""

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

    def test_memories_pagination_basic(self, client):
        """Test basic pagination functionality with multiple pages."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Store 5 distinct memories
        memory_texts = [
            "First memory for pagination test",
            "Second memory for pagination test",
            "Third memory for pagination test",
            "Fourth memory for pagination test",
            "Fifth memory for pagination test"
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
        
        # Page 1: GET with limit=2, offset=0
        page1_response = client.get("/api/v1/memories?limit=2&offset=0", headers=headers)
        assert page1_response.status_code == 200
        
        page1_data = page1_response.json()
        assert "total_memories" in page1_data
        assert "memories" in page1_data
        assert page1_data["total_memories"] == 5
        assert len(page1_data["memories"]) == 2
        
        # Collect page 1 items
        page1_items = {memory["memory_id"] for memory in page1_data["memories"]}
        page1_texts = {memory["text"] for memory in page1_data["memories"]}
        
        # Page 2: GET with limit=2, offset=2
        page2_response = client.get("/api/v1/memories?limit=2&offset=2", headers=headers)
        assert page2_response.status_code == 200
        
        page2_data = page2_response.json()
        assert page2_data["total_memories"] == 5
        assert len(page2_data["memories"]) == 2
        
        # Collect page 2 items and verify they differ from page 1
        page2_items = {memory["memory_id"] for memory in page2_data["memories"]}
        page2_texts = {memory["text"] for memory in page2_data["memories"]}
        
        # Assert no overlap between pages
        assert len(page1_items.intersection(page2_items)) == 0, "Page 1 and Page 2 should not have overlapping memory IDs"
        assert len(page1_texts.intersection(page2_texts)) == 0, "Page 1 and Page 2 should not have overlapping texts"
        
        # Page 3: GET with limit=2, offset=4
        page3_response = client.get("/api/v1/memories?limit=2&offset=4", headers=headers)
        assert page3_response.status_code == 200
        
        page3_data = page3_response.json()
        assert page3_data["total_memories"] == 5
        assert len(page3_data["memories"]) == 1  # Only one item left
        
        # Collect page 3 items and verify they differ from previous pages
        page3_items = {memory["memory_id"] for memory in page3_data["memories"]}
        page3_texts = {memory["text"] for memory in page3_data["memories"]}
        
        # Assert no overlap with previous pages
        assert len(page1_items.intersection(page3_items)) == 0, "Page 1 and Page 3 should not have overlapping items"
        assert len(page2_items.intersection(page3_items)) == 0, "Page 2 and Page 3 should not have overlapping items"
        assert len(page1_texts.intersection(page3_texts)) == 0, "Page 1 and Page 3 should not have overlapping texts"
        assert len(page2_texts.intersection(page3_texts)) == 0, "Page 2 and Page 3 should not have overlapping texts"

    def test_memories_pagination_requires_auth_when_enabled(self, client):
        """Test that pagination endpoints require authentication when API key is set."""
        # Store one memory first (with auth) to have data for testing
        headers = {"X-API-KEY": "test-secret"}
        store_payload = {
            "text": "Memory for pagination auth test",
            "language": "en"
        }
        store_response = client.post("/api/v1/store", json=store_payload, headers=headers)
        assert store_response.status_code == 201
        
        # Test GET /api/v1/memories with pagination params but without header
        pagination_response = client.get("/api/v1/memories?limit=2&offset=0")
        assert pagination_response.status_code == 401
        
        pagination_error = pagination_response.json()
        assert "detail" in pagination_error or "error" in pagination_error
        
        # Error message should be meaningful
        error_message = pagination_error.get("detail") or pagination_error.get("error", "")
        assert isinstance(error_message, str)
        assert len(error_message) > 0

    def test_memories_pagination_invalid_params(self, client):
        """Test that pagination endpoints validate parameters correctly."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Store one memory to have data for testing
        store_payload = {
            "text": "Memory for pagination validation test",
            "language": "en"
        }
        store_response = client.post("/api/v1/store", json=store_payload, headers=headers)
        assert store_response.status_code == 201
        
        # Test limit=0 (invalid)
        response = client.get("/api/v1/memories?limit=0", headers=headers)
        assert response.status_code == 422
        
        # Test limit=-1 (invalid)
        response = client.get("/api/v1/memories?limit=-1", headers=headers)
        assert response.status_code == 422
        
        # Test limit=101 (exceeds max)
        response = client.get("/api/v1/memories?limit=101", headers=headers)
        assert response.status_code == 422
        
        # Test offset=-1 (invalid)
        response = client.get("/api/v1/memories?offset=-1", headers=headers)
        assert response.status_code == 422
        
        # Test limit=foo (non-integer)
        response = client.get("/api/v1/memories?limit=foo", headers=headers)
        assert response.status_code == 422
        
        # Test offset=bar (non-integer)
        response = client.get("/api/v1/memories?offset=bar", headers=headers)
        assert response.status_code == 422