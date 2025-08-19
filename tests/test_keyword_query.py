import pytest
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def one_hot_embed(text: str, dim: int = 1536) -> list[float]:
    idx = abs(hash(text)) % dim
    v = [0.0] * dim
    v[idx] = 1.0
    return v


@pytest.fixture
def client(test_db):
    mock_openai_client = MagicMock()
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock()]
    mock_embedding_response.data[0].embedding = [0.1] * 1536
    mock_openai_client.embeddings.create.return_value = mock_embedding_response

    modules_to_clear = [m for m in list(sys.modules) if m.startswith('agent')]
    for m in modules_to_clear:
        del sys.modules[m]

    with patch('openai.OpenAI', return_value=mock_openai_client):
        from agent.config import Settings
        test_settings = Settings(
            openai_api_key='sk-test-key-for-testing-only',
            db_path=test_db,
            api_auth_key=None,
            llm_decider_model='gpt-4o-mini',
            llm_decider_confidence_min=0.70
        )
        with patch('agent.config.settings', test_settings), \
             patch('agent.memory.embed_text', side_effect=one_hot_embed):
            from agent.main import app
            from agent.memory import init_db
            init_db()
            with TestClient(app) as c:
                yield c


def test_color_specific_query(client):
    client.post('/api/v1/store', json={'text': 'the blue shirt is in the top drawer', 'language': 'en'})
    client.post('/api/v1/store', json={'text': 'the pink shirt is in the top shelf', 'language': 'en'})

    resp = client.post('/api/v1/query', json={'query': 'where is the blue shirt?'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['candidates'][0]['text'] == 'the blue shirt is in the top drawer'

    resp = client.post('/api/v1/query', json={'query': 'where is the shirt?'})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('clarification_required') is True
