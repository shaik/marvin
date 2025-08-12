# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestExportDownload:
    """Test suite for export download functionality."""

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

    def test_export_download_with_valid_auth(self, client):
        """Test export download endpoint with valid authentication."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Store 2 memories with different data
        memories_to_store = [
            {"text": "First export download memory", "language": "en", "location": "office"},
            {"text": "Second export download memory", "language": "he", "location": None}
        ]
        
        for memory_data in memories_to_store:
            store_response = client.post("/api/v1/store", json=memory_data, headers=headers)
            assert store_response.status_code == 201
        
        # GET /api/v1/export/download with auth header
        download_response = client.get("/api/v1/export/download", headers=headers)
        assert download_response.status_code == 200
        
        # Check Content-Type header
        assert "content-type" in download_response.headers
        assert download_response.headers["content-type"] == "application/json"
        
        # Check Content-Disposition header
        assert "content-disposition" in download_response.headers
        content_disposition = download_response.headers["content-disposition"]
        assert "attachment" in content_disposition
        assert "filename=marvin_export.json" in content_disposition
        
        # Parse response body as JSON
        response_text = download_response.text
        export_data = json.loads(response_text)
        
        # Should be a list with 2 items
        assert isinstance(export_data, list)
        assert len(export_data) == 2
        
        # Check each item has required fields
        for item in export_data:
            assert "id" in item
            assert "text" in item
            assert "timestamp" in item
            assert "language" in item
            assert "location" in item
            
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

    def test_export_download_requires_auth_when_enabled(self, client):
        """Test that export download requires authentication when API key is set."""
        # Store one memory first (with auth) to have data for testing
        headers = {"X-API-KEY": "test-secret"}
        store_payload = {
            "text": "Memory for export download auth test",
            "language": "en"
        }
        store_response = client.post("/api/v1/store", json=store_payload, headers=headers)
        assert store_response.status_code == 201
        
        # Test GET /api/v1/export/download without header
        download_response = client.get("/api/v1/export/download")
        assert download_response.status_code == 401
        
        download_error = download_response.json()
        assert "detail" in download_error or "error" in download_error
        
        # Error message should be meaningful
        error_message = download_error.get("detail") or download_error.get("error", "")
        assert isinstance(error_message, str)
        assert len(error_message) > 0

    def test_export_download_pretty_formatting(self, client):
        """Test export download with pretty formatting option."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Store 2 memories
        memories_to_store = [
            {"text": "Pretty formatted memory one", "language": "en"},
            {"text": "Pretty formatted memory two", "language": "he"}
        ]
        
        for memory_data in memories_to_store:
            store_response = client.post("/api/v1/store", json=memory_data, headers=headers)
            assert store_response.status_code == 201
        
        # GET /api/v1/export/download?pretty=1 with auth header
        download_response = client.get("/api/v1/export/download?pretty=1", headers=headers)
        assert download_response.status_code == 200
        
        # Check headers are still correct
        assert download_response.headers["content-type"] == "application/json"
        assert "attachment" in download_response.headers["content-disposition"]
        assert "filename=marvin_export.json" in download_response.headers["content-disposition"]
        
        # Parse response body as JSON
        response_text = download_response.text
        export_data = json.loads(response_text)
        
        # Should be a list with 2 items
        assert isinstance(export_data, list)
        assert len(export_data) == 2
        
        # Check that the response contains indentation (pretty formatting)
        # Pretty-printed JSON should contain newlines and spaces
        assert "\n" in response_text, "Pretty-printed JSON should contain newlines"
        assert "  " in response_text, "Pretty-printed JSON should contain indentation spaces"