# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestMetrics:
    """Test suite for Prometheus metrics endpoint functionality."""

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
    def client_with_auth(self, test_db):
        """Create a TestClient with auth enabled and isolated database."""
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

    @pytest.fixture
    def client_no_auth(self, test_db):
        """Create a TestClient with auth disabled and isolated database."""
        # Create mock settings with API auth disabled
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
             patch('agent.memory.embed_text', side_effect=lambda s: self.one_hot_embed(s)):

            # Import after patching
            from agent.main import app
            from agent.memory import init_db

            # Initialize the test database
            init_db()

            yield TestClient(app)

    def test_metrics_requires_auth_when_enabled(self, client_with_auth):
        """Test that metrics endpoint requires authentication when API key is configured."""
        # Test without header - should return 401
        response = client_with_auth.get("/metrics")
        assert response.status_code == 401
        
        # Test with valid header - should return 200
        headers = {"X-API-KEY": "test-secret"}
        response = client_with_auth.get("/metrics", headers=headers)
        assert response.status_code == 200
        
        # Check Content-Type header
        content_type = response.headers.get("content-type", "")
        assert content_type.startswith("text/plain"), f"Expected text/plain content type, got {content_type}"
        
        # Check response body contains expected metrics
        body = response.text
        assert "http_requests_total" in body, "Response should contain http_requests_total metric"
        assert "marvin_memories_total" in body, "Response should contain marvin_memories_total metric"

    def test_metrics_counts_increase(self, client_with_auth):
        """Test that metrics counters increase with API usage."""
        headers = {"X-API-KEY": "test-secret"}
        
        # Make some API calls to generate metrics
        # Call unprotected health endpoint
        health_response = client_with_auth.get("/health")
        assert health_response.status_code == 200
        
        # Call protected query endpoint
        query_payload = {"query": "metrics test query"}
        query_response = client_with_auth.post("/api/v1/query", json=query_payload, headers=headers)
        assert query_response.status_code == 200
        
        # Get metrics
        metrics_response = client_with_auth.get("/metrics", headers=headers)
        assert metrics_response.status_code == 200
        
        # Check Content-Type
        content_type = metrics_response.headers.get("content-type", "")
        assert content_type.startswith("text/plain")
        
        # Parse metrics body
        body = metrics_response.text
        
        # Check for http_requests_total metric with value >= 2
        # (at least health + query calls, plus the metrics call itself)
        assert "http_requests_total" in body, "Response should contain http_requests_total metric"
        
        # Extract the http_requests_total value (basic parsing)
        lines = body.split('\n')
        http_requests_lines = [line for line in lines if line.startswith('http_requests_total')]
        assert len(http_requests_lines) > 0, "Should find at least one http_requests_total line"
        
        # Look for a numeric value >= 2 in any of the http_requests_total lines
        found_sufficient_requests = False
        for line in http_requests_lines:
            # Simple parsing to extract numeric value at end of line
            parts = line.split()
            if len(parts) >= 2:
                try:
                    value = float(parts[-1])
                    if value >= 2:
                        found_sufficient_requests = True
                        break
                except ValueError:
                    continue
        
        assert found_sufficient_requests, f"Expected http_requests_total >= 2, found lines: {http_requests_lines}"
        
        # Check for marvin_memories_total metric (value doesn't matter, just presence)
        assert "marvin_memories_total" in body, "Response should contain marvin_memories_total metric"

    def test_metrics_open_when_auth_disabled(self, client_no_auth):
        """Test that metrics endpoint is open when authentication is disabled."""
        # GET /metrics without any header - should succeed when auth is disabled
        response = client_no_auth.get("/metrics")
        assert response.status_code == 200
        
        # Check Content-Type
        content_type = response.headers.get("content-type", "")
        assert content_type.startswith("text/plain")
        
        # Check response body contains expected metrics
        body = response.text
        assert "http_requests_total" in body, "Response should contain http_requests_total metric"