# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestRateLimit:
    """Test suite for per-API-key rate limiting functionality."""

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
            api_auth_key="test-secret,test-secret-2"
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

    def test_rate_limit_trips_on_11th_request_same_key(self, client):
        """Test that rate limit is enforced after 10 requests with same API key."""
        # Valid API key header
        headers = {"X-API-KEY": "test-secret"}
        
        # Store one memory first to have data for querying
        store_payload = {
            "text": "Rate limit test memory",
            "language": "en"
        }
        store_response = client.post("/api/v1/store", json=store_payload, headers=headers)
        assert store_response.status_code == 201
        
        # Query payload for rate limit testing
        query_payload = {
            "query": "rate limit test"
        }
        
        # Make 10 requests - all should succeed (including the store above, this makes 11 total)
        # But we'll test with 9 more queries to stay within the 10 limit
        successful_requests = 0
        for i in range(9):
            response = client.post("/api/v1/query", json=query_payload, headers=headers)
            if response.status_code == 200:
                successful_requests += 1
            else:
                break
        
        # Should have 9 successful query requests + 1 successful store = 10 total
        assert successful_requests == 9, f"Expected 9 successful queries, got {successful_requests}"
        
        # 11th request (10th query) should trigger rate limit
        response = client.post("/api/v1/query", json=query_payload, headers=headers)
        assert response.status_code == 429
        
        # Response should have error information
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data
        
        # Error message should be meaningful
        error_message = error_data.get("detail") or error_data.get("error", "")
        assert isinstance(error_message, str)
        assert len(error_message) > 0

    def test_rate_limit_isolated_per_key(self, client):
        """Test that rate limits are isolated per API key."""
        # Valid API key header
        headers_key1 = {"X-API-KEY": "test-secret"}
        headers_key2 = {"X-API-KEY": "test-secret-2"}
        
        # Store memory with first key
        store_payload = {
            "text": "Rate limit isolation test memory",
            "language": "en"
        }
        store_response = client.post("/api/v1/store", json=store_payload, headers=headers_key1)
        assert store_response.status_code == 201
        
        query_payload = {
            "query": "isolation test"
        }
        
        # Exhaust rate limit with first key (9 more requests after the store)
        for i in range(9):
            response = client.post("/api/v1/query", json=query_payload, headers=headers_key1)
            assert response.status_code == 200, f"Request {i+1} should succeed"
        
        # 11th request with first key should be rate limited
        response = client.post("/api/v1/query", json=query_payload, headers=headers_key1)
        assert response.status_code == 429
        
        # First request with second key should succeed (fresh bucket)
        response = client.post("/api/v1/query", json=query_payload, headers=headers_key2)
        assert response.status_code == 200, "First request with different API key should succeed"

    def test_unprotected_endpoints_unlimited(self, client):
        """Test that unprotected endpoints are not rate limited."""
        # Test GET /health 20 times without header - should all succeed
        for i in range(20):
            response = client.get("/health")
            assert response.status_code == 200, f"Health check {i+1} should succeed"
        
        # Test legacy POST /store 15 times without header - should all succeed
        store_payload = {
            "text": f"Legacy store test {i+1}",
            "language": "en"
        }
        
        for i in range(15):
            # Use different text for each request to avoid any potential duplicate detection
            payload = {
                "text": f"Legacy store unlimited test memory {i+1}",
                "language": "en"
            }
            response = client.post("/store", json=payload)
            assert response.status_code == 200, f"Legacy store request {i+1} should succeed"
        
        # Test legacy POST /query 15 times without header - should all succeed
        query_payload = {
            "query": "legacy query test"
        }
        
        for i in range(15):
            response = client.post("/query", json=query_payload)
            assert response.status_code == 200, f"Legacy query request {i+1} should succeed"