# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestUpdateFlow:
    """Test suite for updating existing memories after duplicate detection."""

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
        
        # Mock different embeddings for original vs updated text
        def mock_embed_text(text):
            """Return different vectors for original vs updated text."""
            if "2580" in text:  # Original text
                return [0.1] * 1536
            elif "9247" in text:  # Updated text
                return [0.2] * 1536
            else:
                return [0.15] * 1536  # Default for other texts
        
        mock_embedding_response.data[0].embedding = [0.1] * 1536  # Default for OpenAI client
        mock_openai_client.embeddings.create.return_value = mock_embedding_response

        # Clear module cache to force re-import with mocks
        modules_to_clear = [key for key in sys.modules.keys() if key.startswith('agent')]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        with patch('openai.OpenAI', return_value=mock_openai_client), \
             patch('agent.config.settings', mock_settings), \
             patch('agent.memory.embed_text', side_effect=mock_embed_text):

            # Import after patching
            from agent.main import app
            from agent.memory import init_db

            # Initialize the test database
            init_db()

            yield TestClient(app)

    def test_update_after_duplicate_prompt(self, client):
        """Test updating memory after duplicate detection prompt."""
        # Step 1: Store initial memory
        store_payload = {
            "text": "The door code for Aunt Dalia is 2580.",
            "language": "en"
        }
        
        store_response = client.post("/api/v1/store", json=store_payload)
        assert store_response.status_code == 201
        store_data = store_response.json()
        
        # Should not be duplicate on first store
        assert "duplicate_detected" in store_data
        assert store_data["duplicate_detected"] is False
        assert "memory_id" in store_data
        assert store_data["memory_id"] is not None
        
        stored_memory_id = store_data["memory_id"]
        
        # Step 2: Store same text again to trigger duplicate detection
        duplicate_response = client.post("/api/v1/store", json=store_payload)
        assert duplicate_response.status_code == 409
        duplicate_data = duplicate_response.json()
        
        # Should detect duplicate and return same memory ID
        assert "duplicate_detected" in duplicate_data
        assert duplicate_data["duplicate_detected"] is True
        assert "existing_memory_preview" in duplicate_data
        assert "2580" in duplicate_data["existing_memory_preview"]
        assert "similarity_score" in duplicate_data
        assert duplicate_data["similarity_score"] >= 0.85
        assert "memory_id" in duplicate_data
        assert duplicate_data["memory_id"] == stored_memory_id
        
        # Step 3: Update the memory with new text
        update_payload = {
            "memory_id": stored_memory_id,
            "new_text": "The door code for Aunt Dalia is 9247."
        }
        
        update_response = client.post("/api/v1/update", json=update_payload)
        assert update_response.status_code == 200
        update_data = update_response.json()
        
        # Should confirm successful update
        assert "success" in update_data
        assert update_data["success"] is True
        assert "before" in update_data
        assert "after" in update_data
        assert "2580" in update_data["before"]
        assert "9247" in update_data["after"]
        
        # Step 4: Query to verify the memory was updated
        query_payload = {
            "query": "What is Aunt Dalia's door code?"
        }
        
        query_response = client.post("/api/v1/query", json=query_payload)
        assert query_response.status_code == 200
        query_data = query_response.json()
        
        # Should return the updated text
        assert "candidates" in query_data
        assert len(query_data["candidates"]) > 0
        
        top_candidate = query_data["candidates"][0]
        assert "text" in top_candidate
        assert "9247" in top_candidate["text"]
        
        # Should not contain the old code
        assert "2580" not in top_candidate["text"]

    def test_update_validation_missing_fields(self, client):
        """Test that update endpoint validates required fields."""
        # Test missing all fields
        update_payload_empty = {}
        
        response = client.post("/api/v1/update", json=update_payload_empty)
        assert response.status_code == 422  # Validation error
        
        # Test empty memory_id and new_text
        update_payload_empty_fields = {
            "memory_id": "",
            "new_text": ""
        }
        
        response = client.post("/api/v1/update", json=update_payload_empty_fields)
        assert response.status_code == 422  # Validation error
        
        # Test missing memory_id
        update_payload_missing_id = {
            "new_text": "Some new text"
        }
        
        response = client.post("/api/v1/update", json=update_payload_missing_id)
        assert response.status_code == 422  # Validation error
        
        # Test missing new_text
        update_payload_missing_text = {
            "memory_id": "some-id-12345"
        }
        
        response = client.post("/api/v1/update", json=update_payload_missing_text)
        assert response.status_code == 422  # Validation error
        
        # Test invalid memory_id (non-existent)
        update_payload_invalid = {
            "memory_id": "non-existent-id-12345",
            "new_text": "Some new text"
        }
        
        response = client.post("/api/v1/update", json=update_payload_invalid)
        assert response.status_code in [400, 404]  # Not found or bad request error