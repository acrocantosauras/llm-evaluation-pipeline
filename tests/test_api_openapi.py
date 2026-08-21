def test_openapi_docs_available(client):
    """GET /docs returns 200 (Swagger UI)."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_json_available(client):
    """GET /openapi.json returns the schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/api/v1/evaluations" in schema["paths"]
    assert "/api/v1/runs" in schema["paths"]
