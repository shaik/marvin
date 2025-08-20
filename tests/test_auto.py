# DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

import tempfile
import pytest
import sys
import json
import logging
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestAutoEndpoint:
    """Test suite for LLM-powered auto endpoint that decides between store/retrieve actions."""

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
        """Create a TestClient with API key authentication enabled."""
        # Create mock settings with API auth enabled
        from agent.config import Settings
        mock_settings = Settings(
            openai_api_key="sk-test-key-for-testing-only",
            db_path=test_db,
            api_auth_key="test-secret",
            llm_decider_model="gpt-4o-mini",
            llm_decider_confidence_min=0.70
        )

        # Mock OpenAI client
        mock_openai_client = MagicMock()
        
        # Mock embeddings
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock()]
        mock_embedding_response.data[0].embedding = [0.1] * 1536
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
        """Create a TestClient with API key authentication disabled."""
        # Create mock settings with API auth disabled
        from agent.config import Settings
        mock_settings = Settings(
            openai_api_key="sk-test-key-for-testing-only",
            db_path=test_db,
            api_auth_key=None,
            llm_decider_model="gpt-4o-mini",
            llm_decider_confidence_min=0.70
        )

        # Mock OpenAI client
        mock_openai_client = MagicMock()
        
        # Mock embeddings
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock()]
        mock_embedding_response.data[0].embedding = [0.1] * 1536
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

    def test_auto_endpoint_requires_auth_when_enabled(self, client_with_auth):
        """Test that auto endpoint requires valid API key when auth is enabled."""
        # Test without header
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Remember that I bought milk today"}
        )
        assert response.status_code == 401
        assert "detail" in response.json() or "error" in response.json()

        # Test with wrong header
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Remember that I bought milk today"},
            headers={"X-API-KEY": "wrong-key"}
        )
        assert response.status_code == 401

        # Test with valid header
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Remember that I bought milk today"},
            headers={"X-API-KEY": "test-secret"}
        )
        assert response.status_code in [200, 201]  # Should work, exact status depends on LLM decision

    def test_auto_endpoint_open_when_auth_disabled(self, client_no_auth):
        """Test that auto endpoint works without header when auth is disabled."""
        response = client_no_auth.post(
            "/api/v1/auto",
            json={"text": "Remember that I bought milk today"}
        )
        assert response.status_code in [200, 201]  # Should work

    @patch('openai.OpenAI')
    def test_action_store_when_llm_decides_store(self, mock_openai_class, client_with_auth):
        """Test store action when LLM decides to store."""
        # Mock LLM chat completion to return store decision
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "store",
            "normalized_text": "I bought milk from the grocery store today",
            "language": "en",
            "confidence": 0.9,
            "reason": "User wants to record a new memory about purchasing milk"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Get initial memory count
        memories_response = client_with_auth.get(
            "/api/v1/memories",
            headers={"X-API-KEY": "test-secret"}
        )
        initial_count = memories_response.json()["total_memories"]

        # Make auto request
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "I bought milk today"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Assert response
        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "store"
        assert "decision" in data
        assert "result" in data
        assert "duplicate_detected" in data["result"]
        assert "memory_id" in data["result"]

        # Assert memory was stored
        memories_response = client_with_auth.get(
            "/api/v1/memories",
            headers={"X-API-KEY": "test-secret"}
        )
        new_count = memories_response.json()["total_memories"]
        assert new_count == initial_count + 1

    @patch('openai.OpenAI')
    def test_action_retrieve_when_llm_decides_retrieve(self, mock_openai_class, client_with_auth):
        """Test retrieve action when LLM decides to retrieve."""
        # First store a memory to retrieve
        client_with_auth.post(
            "/api/v1/store",
            json={"text": "I bought milk from the store yesterday", "language": "en"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Mock LLM chat completion to return retrieve decision
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "retrieve",
            "normalized_text": "when did I buy milk",
            "language": "en",
            "confidence": 0.85,
            "reason": "User is asking about a past memory regarding milk purchase"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Make auto request
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "When did I buy milk?"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "retrieve"
        assert "decision" in data
        assert "result" in data
        assert "candidates" in data["result"]

    @patch('openai.OpenAI')
    def test_retrieve_returns_multiple_matches(self, mock_openai_class, client_with_auth):
        """Ensure retrieve action can return multiple matching memories."""
        # Store two related memories
        client_with_auth.post(
            "/api/v1/store",
            json={"text": "I left my blue shirt at home", "language": "en"},
            headers={"X-API-KEY": "test-secret"}
        )
        client_with_auth.post(
            "/api/v1/store",
            json={"text": "I left my red shirt at the office", "language": "en"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Mock LLM to choose retrieve
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "retrieve",
            "normalized_text": "where is my shirt",
            "language": "en",
            "confidence": 0.9,
            "reason": "User is asking about a stored shirt"
        })

        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Where is my shirt?"},
            headers={"X-API-KEY": "test-secret"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "retrieve"
        assert len(data["result"]["candidates"]) >= 2

    @patch('openai.OpenAI')
    def test_action_clarify_on_low_confidence(self, mock_openai_class, client_with_auth):
        """Test clarify action when LLM returns low confidence."""
        # Mock LLM chat completion to return low confidence
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "store",
            "normalized_text": "something unclear",
            "language": "en",
            "confidence": 0.5,  # Below threshold
            "reason": "Ambiguous user intent"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Get initial memory count
        memories_response = client_with_auth.get(
            "/api/v1/memories",
            headers={"X-API-KEY": "test-secret"}
        )
        initial_count = memories_response.json()["total_memories"]

        # Make auto request
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Something unclear happened"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "clarify"
        assert "decision" in data
        assert data["result"] is None
        assert "clarify_prompt" in data["decision"]
        assert "clarify_options" in data["decision"]
        assert data["decision"]["clarify_options"] == ["store", "retrieve"]

        # Assert no memory was stored
        memories_response = client_with_auth.get(
            "/api/v1/memories",
            headers={"X-API-KEY": "test-secret"}
        )
        new_count = memories_response.json()["total_memories"]
        assert new_count == initial_count

    @patch('openai.OpenAI')
    def test_action_clarify_on_invalid_json(self, mock_openai_class, client_with_auth):
        """Test clarify action when LLM returns invalid JSON."""
        # Mock LLM chat completion to return invalid JSON
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = "This is not valid JSON at all"
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Get initial memory count
        memories_response = client_with_auth.get(
            "/api/v1/memories",
            headers={"X-API-KEY": "test-secret"}
        )
        initial_count = memories_response.json()["total_memories"]

        # Make auto request
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Do something with this text"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "clarify"
        assert "decision" in data
        assert data["result"] is None

        # Assert no memory was stored
        memories_response = client_with_auth.get(
            "/api/v1/memories",
            headers={"X-API-KEY": "test-secret"}
        )
        new_count = memories_response.json()["total_memories"]
        assert new_count == initial_count

    @patch('openai.OpenAI')
    def test_force_action_store_overrides_clarify(self, mock_openai_class, client_with_auth):
        """Test that force_action=store overrides LLM clarify decision."""
        # Mock LLM to return low confidence (would normally trigger clarify)
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "store",
            "normalized_text": "unclear text",
            "language": "en",
            "confidence": 0.4,  # Low confidence
            "reason": "Unclear intent"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Get initial memory count
        memories_response = client_with_auth.get(
            "/api/v1/memories",
            headers={"X-API-KEY": "test-secret"}
        )
        initial_count = memories_response.json()["total_memories"]

        # Make auto request with force_action
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Unclear text", "force_action": "store"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Assert response shows forced store action
        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "store"
        assert "result" in data
        assert "memory_id" in data["result"]

        # Assert memory was stored despite low confidence
        memories_response = client_with_auth.get(
            "/api/v1/memories",
            headers={"X-API-KEY": "test-secret"}
        )
        new_count = memories_response.json()["total_memories"]
        assert new_count == initial_count + 1

    @patch('openai.OpenAI')
    def test_force_action_retrieve_overrides_clarify(self, mock_openai_class, client_with_auth):
        """Test that force_action=retrieve overrides LLM clarify decision."""
        # First store a memory to retrieve
        client_with_auth.post(
            "/api/v1/store",
            json={"text": "Test memory for retrieval", "language": "en"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Mock LLM to return low confidence (would normally trigger clarify)
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "retrieve",
            "normalized_text": "unclear query",
            "language": "en",
            "confidence": 0.3,  # Low confidence
            "reason": "Unclear query intent"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Make auto request with force_action
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Find something unclear", "force_action": "retrieve"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Assert response shows forced retrieve action
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "retrieve"
        assert "result" in data
        assert "candidates" in data["result"]

    @patch('openai.OpenAI')
    def test_hebrew_store_example(self, mock_openai_class, client_with_auth):
        """Test Hebrew utterance that should become store action."""
        # Mock LLM to decide store for Hebrew input
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "store",
            "normalized_text": "קניתי חלב בסופרמרקט היום",
            "language": "he",
            "confidence": 0.9,
            "reason": "User wants to record a memory about buying milk"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Make auto request with Hebrew text
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "קניתי חלב היום"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Assert store action was taken
        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "store"
        assert data["decision"]["language"] == "he"

    @patch('openai.OpenAI')
    def test_hebrew_retrieve_example(self, mock_openai_class, client_with_auth):
        """Test Hebrew utterance that should become retrieve action."""
        # First store a Hebrew memory
        client_with_auth.post(
            "/api/v1/store",
            json={"text": "קניתי חלב אתמול", "language": "he"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Mock LLM to decide retrieve for Hebrew query
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "retrieve",
            "normalized_text": "מתי קניתי חלב",
            "language": "he",
            "confidence": 0.85,
            "reason": "User is asking about a past memory"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Make auto request with Hebrew query
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "מתי קניתי חלב?"},
            headers={"X-API-KEY": "test-secret"}
        )

        # Assert retrieve action was taken
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "retrieve"
        assert data["decision"]["language"] == "he"

    @patch('openai.OpenAI')
    def test_rate_limit_behavior(self, mock_openai_class, client_with_auth):
        """Test that auto endpoint follows rate limit rules (10/60s)."""
        # Mock LLM to always return valid response
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "store",
            "normalized_text": "test memory",
            "language": "en",
            "confidence": 0.9,
            "reason": "Test"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        headers = {"X-API-KEY": "test-secret"}
        
        # Make 10 requests (should all succeed)
        for i in range(10):
            response = client_with_auth.post(
                "/api/v1/auto",
                json={"text": f"Test memory {i}"},
                headers=headers
            )
            assert response.status_code in [200, 201, 409]  # 409 possible for duplicates

        # 11th request should hit rate limit
        response = client_with_auth.post(
            "/api/v1/auto",
            json={"text": "Rate limit test"},
            headers=headers
        )
        assert response.status_code == 429
        assert "detail" in response.json() or "error" in response.json()

    @patch('openai.OpenAI')
    def test_logging_smoke_test(self, mock_openai_class, client_with_auth, caplog):
        """Test that auto endpoint logs structured auto_decision event."""
        # Mock LLM response
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = json.dumps({
            "action": "store",
            "normalized_text": "test memory for logging",
            "language": "en",
            "confidence": 0.8,
            "reason": "Test logging"
        })
        
        mock_openai_instance = mock_openai_class.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_chat_response

        # Capture logs
        with caplog.at_level(logging.INFO):
            response = client_with_auth.post(
                "/api/v1/auto",
                json={"text": "Test memory for logging"},
                headers={"X-API-KEY": "test-secret"}
            )

        # Assert response success
        assert response.status_code == 201

        # Check for structured log with auto_decision event
        log_records = [record for record in caplog.records if hasattr(record, 'getMessage')]
        auto_decision_logs = [
            record for record in log_records 
            if 'auto_decision' in record.getMessage()
        ]
        
        # Should have at least one auto_decision log
        assert len(auto_decision_logs) >= 1
        
        # Verify the log contains expected keys (this is a smoke test)
        auto_log = auto_decision_logs[0]
        log_message = auto_log.getMessage()
        assert 'action' in log_message or hasattr(auto_log, 'action')
        assert 'confidence' in log_message or hasattr(auto_log, 'confidence')
        assert 'language' in log_message or hasattr(auto_log, 'language')
