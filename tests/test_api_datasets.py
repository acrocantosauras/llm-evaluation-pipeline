def test_list_datasets_not_implemented(client):
    """GET /api/v1/datasets returns 501 (not yet implemented)."""
    response = client.get("/api/v1/datasets")
    assert response.status_code == 501
    assert "future phase" in response.json()["detail"].lower()
