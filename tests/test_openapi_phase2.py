def test_openapi_includes_phase2_endpoints(client):
    """OpenAPI schema includes all Phase 2 endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema["paths"]

    # Phase 1 endpoints still exist
    assert "/health" in paths
    assert "/api/v1/evaluations" in paths
    assert "/api/v1/runs" in paths

    # Phase 2 endpoints
    assert "/api/v1/evaluations/async" in paths
    assert "/api/v1/jobs" in paths
    assert "/api/v1/jobs/{job_id}" in paths
    assert "/api/v1/jobs/{job_id}/cancel" in paths
    assert "/api/v1/jobs/{job_id}/quality-gate" in paths
    assert "/api/v1/baselines" in paths
    assert "/api/v1/quality-gates" in paths
