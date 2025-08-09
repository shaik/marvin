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
