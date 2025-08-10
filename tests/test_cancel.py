# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestCancelFlow:
    """Test suite for cancel/undo functionality with confirmation flow."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary database for each test."""
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db.close()
        return temp_db.name

    @pytest.fixture
    def client(self, test_db):
        """Create a TestClient with isolated database and mocked dependencies."""
        # Create mock settings
        from agent.config import Settings
        mock_settings = Settings()
        mock_settings.db_path = test_db
        mock_settings.openai_api_key = "sk-test-key-for-testing-only"

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

    def test_cancel_returns_confirmation_before_delete(self, client):
        """Test that cancel finds a matching memory and provides confirmation before deletion."""
        # Step 1: Store a memory
        store_payload = {
            "text": "I lent the pink shirt to Hadar.",
            "language": "he"
        }
        
        store_response = client.post("/api/v1/store", json=store_payload)
        assert store_response.status_code == 201
        store_data = store_response.json()
        stored_memory_id = store_data["memory_id"]
        
        # Step 2: Call cancel endpoint with the same text
        cancel_payload = {
            "last_input_text": "I lent the pink shirt to Hadar."
        }
        
        cancel_response = client.post("/api/v1/cancel", json=cancel_payload)
        
        # Step 3: Assert cancel response provides confirmation
        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        
        # Should return confirmation text and target memory ID
        assert "confirmation_text" in cancel_data
        assert "target_memory_id" in cancel_data
        assert cancel_data["confirmation_text"] is not None
        assert "I lent the pink shirt to Hadar" in cancel_data["confirmation_text"]
        assert cancel_data["target_memory_id"] is not None
        assert cancel_data["target_memory_id"] == stored_memory_id
        
        # Step 4: Use delete endpoint to actually remove the memory
        delete_payload = {
            "memory_id": cancel_data["target_memory_id"]
        }
        
        delete_response = client.post("/api/v1/delete", json=delete_payload)
        
        # Step 5: Assert deletion was successful
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        
        assert "success" in delete_data
        assert "deleted_text" in delete_data
        assert delete_data["success"] is True
        assert delete_data["deleted_text"] == "I lent the pink shirt to Hadar."
        
        # Step 6: Verify memory is no longer retrievable via query
        query_payload = {
            "query": "pink shirt Hadar"
        }
        
        query_response = client.post("/api/v1/query", json=query_payload)
        assert query_response.status_code == 200
        query_data = query_response.json()
        
        # Should return no candidates or the deleted text should not appear
        candidates = query_data.get("candidates", [])
        deleted_text_found = any("I lent the pink shirt to Hadar" in candidate.get("text", "") 
                                for candidate in candidates)
        assert not deleted_text_found, "Deleted memory should not appear in query results"

    def test_cancel_handles_missing_match_gracefully(self, client):
        """Test that cancel handles cases where no matching memory is found."""
        # Empty database - no memories stored
        
        # Try to cancel with text that doesn't match any stored memory
        cancel_payload = {
            "last_input_text": "This text was never stored as a memory."
        }
        
        cancel_response = client.post("/api/v1/cancel", json=cancel_payload)
        
        # Should return 404 or 400 with clear error message
        assert cancel_response.status_code in [400, 404]
        
        error_data = cancel_response.json()
        
        # Should have error information
        assert "detail" in error_data or "error" in error_data
        
        # Error message should be meaningful
        error_message = error_data.get("detail") or error_data.get("error", "")
        assert isinstance(error_message, str)
        assert len(error_message) > 0

    def test_cancel_endpoint_validation(self, client):
        """Test that cancel endpoint validates required fields."""
        # Test missing last_input_text field
        cancel_payload_empty = {}
        
        response = client.post("/api/v1/cancel", json=cancel_payload_empty)
        assert response.status_code == 422  # Validation error
        
        # Test empty last_input_text
        cancel_payload_empty_text = {
            "last_input_text": ""
        }
        
        response = client.post("/api/v1/cancel", json=cancel_payload_empty_text)
        assert response.status_code in [400, 422]  # Validation error
        
    def test_delete_endpoint_validation(self, client):
        """Test that delete endpoint validates required fields."""
        # Test missing memory_id field
        delete_payload_empty = {}
        
        response = client.post("/api/v1/delete", json=delete_payload_empty)
        assert response.status_code == 422  # Validation error
        
        # Test empty memory_id
        delete_payload_empty_id = {
            "memory_id": ""
        }
        
        response = client.post("/api/v1/delete", json=delete_payload_empty_id)
        assert response.status_code in [400, 422]  # Validation error
        
        # Test invalid memory_id (non-existent)
        delete_payload_invalid = {
            "memory_id": "non-existent-id-12345"
        }
        
        response = client.post("/api/v1/delete", json=delete_payload_invalid)
        assert response.status_code in [400, 404]  # Not found error