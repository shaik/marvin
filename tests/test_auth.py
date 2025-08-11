# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestAPIKeyAuthentication:
    """Test suite for API key authentication behavior."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary database for each test."""
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db.close()
        return temp_db.name

    @pytest.fixture
    def client_with_auth(self, test_db):
        """Create a TestClient with API key authentication enabled."""
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
             patch('agent.memory.embed_text', return_value=[0.1] * 1536):

            # Import after patching
            from agent.main import app
            from agent.memory import init_db

            # Initialize the test database
            init_db()

            yield TestClient(app)

    @pytest.fixture
    def client_no_auth(self, test_db):
        """Create a TestClient with API key authentication disabled."""
        # Create mock settings with API auth disabled (None/unset)
        from agent.config import Settings
        mock_settings = Settings(
            openai_api_key="sk-test-key-for-testing-only",
            db_path=test_db,
            api_auth_key=None
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
             patch('agent.memory.embed_text', return_value=[0.1] * 1536):

            # Import after patching
            from agent.main import app
            from agent.memory import init_db

            # Initialize the test database
            init_db()

            yield TestClient(app)

    def test_protected_endpoints_require_api_key(self, client_with_auth):
        """Test that protected endpoints require valid API key."""
        # Test POST /api/v1/store without header
        store_payload = {
            "text": "Auth test memory",
            "language": "he"
        }
        
        response = client_with_auth.post("/api/v1/store", json=store_payload)
        assert response.status_code == 401
        
        response_data = response.json()
        assert "detail" in response_data or "error" in response_data
        
        # Test POST /api/v1/query without header
        query_payload = {
            "query": "Auth test memory"
        }
        
        response = client_with_auth.post("/api/v1/query", json=query_payload)
        assert response.status_code == 401
        
        response_data = response.json()
        assert "detail" in response_data or "error" in response_data
        
        # Test with WRONG API key header
        headers_wrong = {"X-API-KEY": "wrong-key"}
        
        response = client_with_auth.post("/api/v1/store", json=store_payload, headers=headers_wrong)
        assert response.status_code == 401
        
        response_data = response.json()
        assert "detail" in response_data or "error" in response_data
        
        response = client_with_auth.post("/api/v1/query", json=query_payload, headers=headers_wrong)
        assert response.status_code == 401
        
        response_data = response.json()
        assert "detail" in response_data or "error" in response_data

    def test_protected_endpoints_accept_valid_api_key(self, client_with_auth):
        """Test that protected endpoints accept valid API key."""
        # Correct API key header
        headers_valid = {"X-API-KEY": "test-secret"}
        
        # Test POST /api/v1/store with valid header
        store_payload = {
            "text": "Auth test memory",
            "language": "he"
        }
        
        store_response = client_with_auth.post("/api/v1/store", json=store_payload, headers=headers_valid)
        assert store_response.status_code == 201
        store_data = store_response.json()
        
        # Should not be duplicate on first store
        assert "duplicate_detected" in store_data
        assert store_data["duplicate_detected"] is False
        assert "memory_id" in store_data
        assert store_data["memory_id"] is not None
        
        # Test POST /api/v1/query with valid header
        query_payload = {
            "query": "Auth test memory"
        }
        
        query_response = client_with_auth.post("/api/v1/query", json=query_payload, headers=headers_valid)
        assert query_response.status_code == 200
        query_data = query_response.json()
        
        # Should return the stored memory
        assert "candidates" in query_data
        assert len(query_data["candidates"]) > 0
        
        top_candidate = query_data["candidates"][0]
        assert "text" in top_candidate
        assert "Auth test memory" in top_candidate["text"]

    def test_unprotected_endpoints_remain_open(self, client_with_auth):
        """Test that unprotected endpoints remain accessible without API key."""
        # Test GET /health without header
        health_response = client_with_auth.get("/health")
        assert health_response.status_code == 200
        
        # Test legacy POST /store without header
        store_payload = {
            "text": "Legacy auth test memory",
            "language": "he"
        }
        
        legacy_store_response = client_with_auth.post("/store", json=store_payload)
        assert legacy_store_response.status_code == 200  # Legacy redirect/upgrade hint
        
        legacy_store_data = legacy_store_response.json()
        # Should contain upgrade message
        assert "message" in legacy_store_data or "new_endpoint" in legacy_store_data
        
        # Test legacy POST /query without header
        query_payload = {
            "query": "Legacy auth test memory"
        }
        
        legacy_query_response = client_with_auth.post("/query", json=query_payload)
        assert legacy_query_response.status_code == 200  # Legacy redirect/upgrade hint
        
        legacy_query_data = legacy_query_response.json()
        # Should contain upgrade message
        assert "message" in legacy_query_data or "new_endpoint" in legacy_query_data

    def test_auth_disabled_when_api_key_unset(self, client_no_auth):
        """Test that auth is disabled when API_AUTH_KEY is None/unset."""
        # When API_AUTH_KEY is None, all endpoints should work without headers
        
        # Test POST /api/v1/store without header (should work)
        store_payload = {
            "text": "No auth test memory",
            "language": "he"
        }
        
        store_response = client_no_auth.post("/api/v1/store", json=store_payload)
        assert store_response.status_code == 201
        store_data = store_response.json()
        
        assert "duplicate_detected" in store_data
        assert store_data["duplicate_detected"] is False
        
        # Test POST /api/v1/query without header (should work)
        query_payload = {
            "query": "No auth test memory"
        }
        
        query_response = client_no_auth.post("/api/v1/query", json=query_payload)
        assert query_response.status_code == 200
        query_data = query_response.json()
        
        assert "candidates" in query_data
        assert len(query_data["candidates"]) > 0