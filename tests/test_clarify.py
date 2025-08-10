# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

"""
Immutable tests for Marvin's clarify/ambiguity flow.
These tests validate the expected behavior when query results are ambiguous
and require user clarification to select the correct memory.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
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
    """Create a TestClient with isolated database and mocked embeddings for clarify tests."""
    
    # Create deterministic embeddings for clarify scenarios
    def mock_embed_text(text: str):
        """Mock embedding function that returns sparse/orthogonal vectors for test scenarios."""
        import math
        
        if "Code for Dalia from work is 1234" in text:
            # First Dalia memory - unit vector on index 0
            vector = [0.0] * 1536
            vector[0] = 1.0
            return vector
        elif "Code for Aunt Dalia is 2580" in text:
            # Second Dalia memory - unit vector on index 1 (orthogonal to first)
            vector = [0.0] * 1536
            vector[1] = 1.0
            return vector
        elif "What is Dalia's code?" in text:
            # Query vector - normalized sum of both memories (creates equal similarity)
            # (v0 + v1) / sqrt(2) where v0=[1,0,0...] and v1=[0,1,0...]
            vector = [0.0] * 1536
            vector[0] = 1.0 / math.sqrt(2)  # ≈ 0.707
            vector[1] = 1.0 / math.sqrt(2)  # ≈ 0.707
            return vector
        elif "Password for email is secret123" in text:
            # Different context memory - orthogonal to both Dalia memories
            vector = [0.0] * 1536
            vector[2] = 1.0
            return vector
        elif "What is Dalia's work code?" in text:
            # Slightly favor first memory for clear winner test
            vector = [0.0] * 1536
            vector[0] = 0.9   # Higher weight to first memory
            vector[1] = 0.1   # Lower weight to second memory
            return vector
        else:
            # Default vector for any other text - orthogonal to all test vectors
            vector = [0.0] * 1536
            vector[100] = 1.0  # Use a different index
            return vector
    
    # Mock OpenAI client to avoid real API calls
    mock_openai_client = MagicMock()
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock()]
    mock_embedding_response.data[0].embedding = [0.1] * 1536  # Default embedding
    mock_openai_client.embeddings.create.return_value = mock_embedding_response
    
    # Patch OpenAI before importing agent modules
    with patch('openai.OpenAI', return_value=mock_openai_client):
        # Clear module cache to force reimport with mocked OpenAI
        modules_to_clear = [m for m in sys.modules.keys() if m.startswith('agent')]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Now import and configure after mocking
        from agent.config import Settings
        
        # Mock the settings with test configuration
        test_settings = Settings(
            openai_api_key="sk-test-key-for-clarify-testing",
            db_path=test_db,
            host="0.0.0.0",
            port=5000,
            cors_origins=["http://localhost:3000"],
            log_level="INFO",
            app_name="Marvin Memory Service",
            app_version="1.0.0"
        )
        
        # Patch settings and embedding function
        with patch('agent.config.settings', test_settings), \
             patch('agent.memory.embed_text', side_effect=mock_embed_text):
            
            # Import app after patching settings to ensure it uses test config
            from agent.main import app
            
            # Initialize the test database
            from agent.memory import init_db
            init_db()
            
            # Create and return the test client
            with TestClient(app) as test_client:
                yield test_client


class TestClarificationFlow:
    """Test the clarify/ambiguity flow for handling similar memories."""
    
    def test_query_requires_clarification_on_close_candidates(self, client):
        """Test that query returns clarification_required when candidates have close similarity scores."""
        # Step 1: Store two very similar memories about "Dalia"
        memory1_payload = {
            "text": "Code for Dalia from work is 1234",
            "language": "he"
        }
        
        memory2_payload = {
            "text": "Code for Aunt Dalia is 2580", 
            "language": "he"
        }
        
        # Store first memory
        store1_response = client.post("/api/v1/store", json=memory1_payload)
        assert store1_response.status_code == 201
        store1_data = store1_response.json()
        memory1_id = store1_data["memory_id"]
        
        # Store second memory
        store2_response = client.post("/api/v1/store", json=memory2_payload)
        assert store2_response.status_code == 201
        store2_data = store2_response.json()
        memory2_id = store2_data["memory_id"]
        
        # Step 2: Query with ambiguous text
        query_payload = {
            "query": "What is Dalia's code?"
        }
        
        query_response = client.post("/api/v1/query", json=query_payload)
        
        # Step 3: Assert clarification is required
        assert query_response.status_code == 200
        
        query_data = query_response.json()
        
        # Should indicate clarification is required
        assert "clarification_required" in query_data
        assert query_data["clarification_required"] is True
        
        # Should provide a clarification question mentioning "Dalia"
        assert "clarification_question" in query_data
        assert "Dalia" in query_data["clarification_question"]
        
        # Should return candidates with close similarity scores
        assert "candidates" in query_data
        candidates = query_data["candidates"]
        assert len(candidates) >= 2
        
        # Verify the candidates are our stored memories
        candidate_ids = {candidate["memory_id"] for candidate in candidates}
        assert memory1_id in candidate_ids
        assert memory2_id in candidate_ids
        
        # Verify similarity scores are close (gap <= 0.05)
        scores = [candidate["similarity_score"] for candidate in candidates[:2]]
        score_gap = abs(scores[0] - scores[1])
        assert score_gap <= 0.05, f"Score gap {score_gap} should be <= 0.05 for clarification to trigger"
        
        # All candidates should have required fields
        for candidate in candidates:
            assert "memory_id" in candidate
            assert "text" in candidate
            assert "similarity_score" in candidate
            assert candidate["memory_id"] in [memory1_id, memory2_id]
    
    def test_clarify_endpoint_resolves_selection(self, client):
        """Test that the clarify endpoint correctly resolves user selection."""
        # Step 1: Set up the same scenario as above
        memory1_payload = {
            "text": "Code for Dalia from work is 1234",
            "language": "he"
        }
        
        memory2_payload = {
            "text": "Code for Aunt Dalia is 2580",
            "language": "he"
        }
        
        # Store memories
        store1_response = client.post("/api/v1/store", json=memory1_payload)
        assert store1_response.status_code == 201
        memory1_id = store1_response.json()["memory_id"]
        
        store2_response = client.post("/api/v1/store", json=memory2_payload)
        assert store2_response.status_code == 201
        memory2_id = store2_response.json()["memory_id"]
        
        # Step 2: Query to get clarification candidates
        query_payload = {
            "query": "What is Dalia's code?"
        }
        
        query_response = client.post("/api/v1/query", json=query_payload)
        assert query_response.status_code == 200
        
        query_data = query_response.json()
        assert query_data["clarification_required"] is True
        candidates = query_data["candidates"]
        
        # Step 3: Use clarify endpoint to select first candidate
        chosen_candidate = candidates[0]
        chosen_memory_id = chosen_candidate["memory_id"]
        chosen_text = chosen_candidate["text"]
        
        clarify_payload = {
            "query": "What is Dalia's code?",
            "chosen_memory_id": chosen_memory_id
        }
        
        clarify_response = client.post("/api/v1/clarify", json=clarify_payload)
        
        # Step 4: Assert clarification is resolved correctly
        assert clarify_response.status_code == 200
        
        clarify_data = clarify_response.json()
        
        # Should indicate clarification was resolved
        assert "clarification_resolved" in clarify_data
        assert clarify_data["clarification_resolved"] is True
        
        # Should return the chosen memory details
        assert "memory_id" in clarify_data
        assert clarify_data["memory_id"] == chosen_memory_id
        
        assert "text" in clarify_data
        assert clarify_data["text"] == chosen_text
        
        # Verify the returned text matches what we expect
        assert clarify_data["memory_id"] in [memory1_id, memory2_id]
        if clarify_data["memory_id"] == memory1_id:
            assert clarify_data["text"] == "Code for Dalia from work is 1234"
        else:
            assert clarify_data["text"] == "Code for Aunt Dalia is 2580"
    
    def test_clarify_endpoint_with_invalid_memory_id(self, client):
        """Test that clarify endpoint handles invalid memory IDs properly."""
        # Store at least one memory for context
        memory_payload = {
            "text": "Code for Dalia from work is 1234",
            "language": "he"
        }
        
        store_response = client.post("/api/v1/store", json=memory_payload)
        assert store_response.status_code == 201
        
        # Try to clarify with non-existent memory ID
        clarify_payload = {
            "query": "What is Dalia's code?",
            "chosen_memory_id": "non-existent-id-12345"
        }
        
        clarify_response = client.post("/api/v1/clarify", json=clarify_payload)
        
        # Should return error for invalid memory ID
        assert clarify_response.status_code in [400, 404, 422]  # Bad request, not found, or validation error
        
        error_data = clarify_response.json()
        assert "error" in error_data or "detail" in error_data
    
    def test_query_no_clarification_needed_for_clear_winner(self, client):
        """Test that normal query behavior works when no clarification is needed."""
        # Store two memories with different contexts
        memory1_payload = {
            "text": "Code for Dalia from work is 1234",
            "language": "he"
        }
        
        memory2_payload = {
            "text": "Password for email is secret123",  # Very different context
            "language": "he"
        }
        
        # Store memories
        store1_response = client.post("/api/v1/store", json=memory1_payload)
        assert store1_response.status_code == 201
        
        store2_response = client.post("/api/v1/store", json=memory2_payload)
        assert store2_response.status_code == 201
        
        # Query for something that clearly matches first memory
        query_payload = {
            "query": "What is Dalia's work code?"  # Should clearly match first memory
        }
        
        query_response = client.post("/api/v1/query", json=query_payload)
        assert query_response.status_code == 200
        
        query_data = query_response.json()
        
        # Should NOT require clarification (this may pass even before clarify feature is implemented)
        # This test validates that normal query behavior isn't broken
        assert "candidates" in query_data
        assert len(query_data["candidates"]) > 0
        
        # If clarification_required exists, it should be False for this clear case
        if "clarification_required" in query_data:
            assert query_data["clarification_required"] is False
    
    def test_clarify_endpoint_validation(self, client):
        """Test that clarify endpoint validates required fields."""
        # Test missing query field
        clarify_payload_missing_query = {
            "chosen_memory_id": "some-id"
        }
        
        response = client.post("/api/v1/clarify", json=clarify_payload_missing_query)
        assert response.status_code == 422  # Validation error
        
        # Test missing chosen_memory_id field
        clarify_payload_missing_id = {
            "query": "What is Dalia's code?"
        }
        
        response = client.post("/api/v1/clarify", json=clarify_payload_missing_id)
        assert response.status_code == 422  # Validation error
        
        # Test empty fields
        clarify_payload_empty = {
            "query": "",
            "chosen_memory_id": ""
        }
        
        response = client.post("/api/v1/clarify", json=clarify_payload_empty)
        assert response.status_code == 422  # Validation error