"""Tests for duplicate detection returning proper status code."""


def test_duplicate_store_returns_409(client):
    payload = {
        "text": "I lent a red pen to Alex.",
        "language": "he",
    }

    first = client.post("/api/v1/store", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/store", json=payload)
    assert second.status_code == 409
    data = second.json()
    assert data["duplicate_detected"] is True
    assert data["existing_memory_preview"] == "I lent a red pen to Alex."


def test_similar_store_allowed(client):
    from unittest.mock import patch

    first = {"text": "the blue shirt is in the top drawer", "language": "he"}
    second = {"text": "my blue shirt is in the top drawer", "language": "he"}

    with patch("agent.memory.embed_text") as mock_embed:
        mock_embed.side_effect = [
            [1.0] + [0.0] * 1535,
            [0.0, 1.0] + [0.0] * 1534,
        ]

        resp1 = client.post("/api/v1/store", json=first)
        assert resp1.status_code == 201

        resp2 = client.post("/api/v1/store", json=second)
        assert resp2.status_code == 201
        assert resp2.json()["duplicate_detected"] is False
