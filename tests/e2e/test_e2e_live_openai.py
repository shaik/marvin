# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

"""
End-to-end tests for Marvin Memory Assistant using live OpenAI API.
These tests require a running backend service and real OpenAI API access.
"""

import os
import pytest
import httpx
from uuid import uuid4


# Skip the entire module unless both environment variables are set
def pytest_configure():
    """Configure pytest to skip module if required env vars are missing."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    live_e2e = os.getenv("LIVE_E2E", "").strip()
    
    if not openai_key or live_e2e != "1":
        pytest.skip(
            "Skipping live E2E tests: requires OPENAI_API_KEY and LIVE_E2E=1",
            allow_module_level=True
        )


# Configuration
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 20.0  # seconds


@pytest.mark.e2e
def test_health_live():
    """Test that the live service health endpoint returns correctly."""
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(f"{BASE_URL}/health")
        
        # Assert successful response
        assert response.status_code == 200
        
        # Assert JSON structure
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        
        # Verify specific values
        assert data["status"] == "healthy"


@pytest.mark.e2e
def test_store_query_live_round_trip():
    """Test storing a memory and querying it back using live OpenAI."""
    # Generate unique suffix for test isolation
    suffix = uuid4().hex[:8]
    text = f"I borrowed the blue notebook from Maya on Tuesday ({suffix})."
    query = "Where is the blue notebook I borrowed?"
    
    with httpx.Client(timeout=TIMEOUT) as client:
        # Step 1: Store the memory
        store_payload = {
            "text": text,
            "language": "he"
        }
        
        store_response = client.post(f"{BASE_URL}/api/v1/store", json=store_payload)
        
        # Assert successful storage (accept 200, 201, or 409 for duplicates)
        assert store_response.status_code in [200, 201, 409]
        
        store_data = store_response.json()
        assert "memory_id" in store_data
        assert store_data["memory_id"] != ""
        assert len(store_data["memory_id"]) > 0
        
        # If it's a duplicate, that's okay - we just need the memory_id for querying
        if store_response.status_code == 409:
            assert "duplicate_detected" in store_data
            assert store_data["duplicate_detected"] is True
        else:
            assert "duplicate_detected" in store_data
        
        # Step 2: Query the memory back
        query_payload = {
            "query": query
        }
        
        query_response = client.post(f"{BASE_URL}/api/v1/query", json=query_payload)
        
        # Assert successful query
        assert query_response.status_code == 200
        
        query_data = query_response.json()
        assert "candidates" in query_data
        assert len(query_data["candidates"]) > 0
        
        # Verify we get results and that one of the candidates is relevant
        top_candidate = query_data["candidates"][0]
        assert "text" in top_candidate
        assert "memory_id" in top_candidate
        assert "similarity_score" in top_candidate
        
        # Check if our specific memory is in the results (if not duplicate)
        if store_response.status_code != 409:
            # Look for our suffix in any of the candidates
            found_our_memory = any(suffix in candidate.get("text", "") for candidate in query_data["candidates"])
            assert found_our_memory, f"Expected to find suffix '{suffix}' in one of the candidates"
        else:
            # If it was a duplicate, just verify we get meaningful results
            assert len(query_data["candidates"]) > 0
            assert "blue notebook" in top_candidate["text"].lower() or "notebook" in top_candidate["text"].lower() or "borrowed" in top_candidate["text"].lower() or "lent" in top_candidate["text"].lower()


@pytest.mark.e2e
def test_duplicate_detection_live():
    """Test duplicate detection using live OpenAI with the same memory stored twice."""
    # Generate unique suffix for test isolation
    suffix = uuid4().hex[:8]
    text = f"I borrowed the red backpack from Sarah on Friday ({suffix})."
    
    store_payload = {
        "text": text,
        "language": "he"
    }
    
    with httpx.Client(timeout=TIMEOUT) as client:
        # Step 1: Store the memory for the first time
        first_response = client.post(f"{BASE_URL}/api/v1/store", json=store_payload)
        
        # Assert successful first storage (may be duplicate if similar exists)
        assert first_response.status_code in [200, 201, 409]
        
        first_data = first_response.json()
        assert "memory_id" in first_data
        original_memory_id = first_data["memory_id"]
        
        # Store the text we actually used (may be from existing memory if duplicate)
        actual_text = text
        if first_response.status_code == 409 and "existing_memory_preview" in first_data:
            actual_text = first_data["existing_memory_preview"]
        
        # Step 2: Store the exact same memory again
        second_response = client.post(f"{BASE_URL}/api/v1/store", json=store_payload)
        
        # Assert response indicates duplicate detection
        # Accept either 409 (conflict) or 201/200 with duplicate_detected=True
        assert second_response.status_code in [200, 201, 409]
        
        second_data = second_response.json()
        
        if second_response.status_code == 409:
            # If 409, duplicate should be indicated in response
            assert "duplicate_detected" in second_data
            assert second_data["duplicate_detected"] is True
        else:
            # If 200/201, duplicate_detected should be True
            assert "duplicate_detected" in second_data
            assert second_data["duplicate_detected"] is True
        
        # Verify duplicate details
        assert "existing_memory_preview" in second_data
        assert second_data["existing_memory_preview"] == actual_text
        
        # Verify similarity score if present
        if "similarity_score" in second_data:
            assert second_data["similarity_score"] >= 0.97, f"Expected similarity >= 0.97, got {second_data['similarity_score']}"
        
        # Verify memory_id matches original (should reference existing memory)
        assert "memory_id" in second_data
        assert second_data["memory_id"] == original_memory_id


@pytest.mark.e2e
def test_api_error_handling_live():
    """Test that the live API properly handles invalid requests."""
    with httpx.Client(timeout=TIMEOUT) as client:
        # Test empty text storage
        empty_payload = {
            "text": "",
            "language": "he"
        }
        
        response = client.post(f"{BASE_URL}/api/v1/store", json=empty_payload)
        assert response.status_code == 422  # Validation error
        
        # Test empty query
        empty_query_payload = {
            "query": ""
        }
        
        response = client.post(f"{BASE_URL}/api/v1/query", json=empty_query_payload)
        assert response.status_code == 422  # Validation error


@pytest.mark.e2e  
def test_api_versioning_live():
    """Test that API versioning works correctly on live service."""
    with httpx.Client(timeout=TIMEOUT) as client:
        # Test legacy endpoint redirect
        response = client.post(f"{BASE_URL}/store")
        
        # Should return information about new endpoint
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "new_endpoint" in data
        assert "/api/v1/store" in data["new_endpoint"]