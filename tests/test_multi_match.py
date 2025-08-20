def test_query_returns_multiple_matches(client):
    """Store two related memories and ensure both are returned using min_score."""
    first = {"text": "I left my blue shirt at home.", "language": "en"}
    second = {"text": "I left my red shirt at the office.", "language": "en"}

    # Store both memories
    assert client.post("/api/v1/store", json=first).status_code == 201
    assert client.post("/api/v1/store", json=second).status_code == 201

    # Query with a min_score threshold to allow multiple matches
    query_payload = {"query": "Where is my shirt?", "min_score": 0.5}
    response = client.post("/api/v1/query", json=query_payload)
    assert response.status_code == 200
    data = response.json()
    texts = [c["text"] for c in data["candidates"]]
    assert first["text"] in texts and second["text"] in texts
