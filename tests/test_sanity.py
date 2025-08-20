# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

"""
Sanity tests for Marvin Memory Assistant
These immutable tests ensure core functionality works correctly.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock
import sys


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary SQLite database for each test."""
    # Create a temporary file for the test database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)  # Close the file descriptor, we only need the path
    
    yield db_path
    
    # Cleanup: remove the temporary database file
    try:
        os.unlink(db_path)
    except OSError:
        pass  # File might not exist or already be deleted


@pytest.fixture(scope="function")
def client(test_db):
    """Create a TestClient with isolated database for each test."""
    
    # Mock the OpenAI client before any imports
    mock_openai_client = MagicMock()
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock()]
    mock_embedding_response.data[0].embedding = [0.1] * 1536  # Mock 1536-dim embedding
    mock_openai_client.embeddings.create.return_value = mock_embedding_response
    
    # Create mock OpenAI class
    mock_openai_class = Mock(return_value=mock_openai_client)
    
    # Patch OpenAI before importing agent modules
    with patch('openai.OpenAI', mock_openai_class):
        # Clear module cache to force reimport with mocked OpenAI
        modules_to_clear = [m for m in sys.modules.keys() if m.startswith('agent')]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Now import and configure after mocking
        from agent.config import Settings
        
        # Mock the settings with test configuration
        test_settings = Settings(
            openai_api_key="sk-test-key-for-testing-only",
            db_path=test_db,
            host="0.0.0.0",
            port=5000,
            cors_origins=["http://localhost:3000"],
            log_level="INFO",
            app_name="Marvin Memory Service",
            app_version="1.0.0"
        )
        
        # Patch the settings in both config and memory modules
        with patch('agent.config.settings', test_settings):
            # Import app after patching settings to ensure it uses test config
            from agent.main import app
            
            # Initialize the test database
            from agent.memory import init_db
            init_db()
            
            # Create and return the test client
            with TestClient(app) as test_client:
                yield test_client


class TestServiceStartup:
    """Test service startup and health checks."""
    
    def test_health_endpoint(self, client):
        """Test that the health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
        
        # Verify response structure
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data


class TestStoreQueryRoundTrip:
    """Test basic store and query functionality."""
    
    def test_store_and_query_memory(self, client):
        """Test storing a memory and then querying it back."""
        # Step 1: Store a memory
        store_payload = {
            "text": "I lent a red pen to Alex.",
            "language": "he"
        }
        
        store_response = client.post("/api/v1/store", json=store_payload)
        assert store_response.status_code == 201
        
        store_data = store_response.json()
        assert "duplicate_detected" in store_data
        assert store_data["duplicate_detected"] is False
        assert "memory_id" in store_data
        assert store_data["memory_id"] != ""
        assert len(store_data["memory_id"]) > 0
        
        # Step 2: Query the memory back
        query_payload = {
            "query": "Where is my red pen?"
        }
        
        query_response = client.post("/api/v1/query", json=query_payload)
        assert query_response.status_code == 200
        
        query_data = query_response.json()
        assert "candidates" in query_data
        assert len(query_data["candidates"]) > 0
        
        # Verify the first candidate matches our stored memory
        first_candidate = query_data["candidates"][0]
        assert "text" in first_candidate
        assert first_candidate["text"] == "I lent a red pen to Alex."
        assert "memory_id" in first_candidate
        assert "similarity_score" in first_candidate


class TestDuplicateDetection:
    """Test duplicate detection functionality."""
    
    def test_duplicate_detection_on_second_store(self, client):
        """Test that storing the same memory twice detects a duplicate."""
        # Payload for storing memory
        store_payload = {
            "text": "I lent a red pen to Alex.",
            "language": "he"
        }
        
        # Step 1: Store the memory for the first time
        first_store_response = client.post("/api/v1/store", json=store_payload)
        assert first_store_response.status_code == 201
        
        first_store_data = first_store_response.json()
        assert first_store_data["duplicate_detected"] is False
        original_memory_id = first_store_data["memory_id"]
        
        # Step 2: Store the exact same memory again
        second_store_response = client.post("/api/v1/store", json=store_payload)

        # A duplicate store should respond with a 409 Conflict
        assert second_store_response.status_code == 409
        
        second_store_data = second_store_response.json()
        assert "duplicate_detected" in second_store_data
        assert second_store_data["duplicate_detected"] is True
        assert "existing_memory_preview" in second_store_data
        assert second_store_data["existing_memory_preview"] == "I lent a red pen to Alex."
        assert "similarity_score" in second_store_data
        assert second_store_data["similarity_score"] >= 0.97  # Should be high similarity
        
        # The memory_id should be the same as the original (existing memory)
        assert "memory_id" in second_store_data
        assert second_store_data["memory_id"] == original_memory_id


class TestAPIEndpointVersioning:
    """Test that API endpoints are properly versioned."""
    
    def test_legacy_endpoint_redirects(self, client):
        """Test that legacy endpoints provide migration information."""
        # Test legacy store endpoint
        legacy_response = client.post("/store")
        assert legacy_response.status_code == 200
        
        legacy_data = legacy_response.json()
        assert "message" in legacy_data
        assert "new_endpoint" in legacy_data
        assert "/api/v1/store" in legacy_data["new_endpoint"]


class TestErrorHandling:
    """Test proper error handling and validation."""
    
    def test_store_with_empty_text(self, client):
        """Test that storing empty text returns proper error."""
        store_payload = {
            "text": "",
            "language": "he"
        }
        
        response = client.post("/api/v1/store", json=store_payload)
        assert response.status_code == 422  # Validation error
        
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data
    
    def test_query_with_empty_query(self, client):
        """Test that querying with empty text returns proper error."""
        query_payload = {
            "query": ""
        }
        
        response = client.post("/api/v1/query", json=query_payload)
        assert response.status_code == 422  # Validation error
        
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data
    
    def test_invalid_top_k_parameter(self, client):
        """Test that invalid top_k parameter returns proper error."""
        query_payload = {
            "query": "test query",
            "top_k": 0  # Invalid: must be positive
        }
        
        response = client.post("/api/v1/query", json=query_payload)
        assert response.status_code == 422  # Validation error
        
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data