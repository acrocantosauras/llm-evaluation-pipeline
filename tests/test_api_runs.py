import uuid

from tests.conftest import VALID_REQUEST


def _create_run(client) -> str:
    """Helper: create an evaluation run and return the run_id."""
    response = client.post("/api/v1/evaluations", json=VALID_REQUEST)
    assert response.status_code == 201
    return response.json()["run_id"]


def test_get_run_existing(client):
    """GET /api/v1/runs/{id} returns existing run."""
    run_id = _create_run(client)

    response = client.get(f"/api/v1/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["status"] == "completed"
    assert "results" in data


def test_get_run_not_found(client):
    """GET /api/v1/runs/{id} returns 404 for unknown ID."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/runs/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_runs_empty(client):
    """GET /api/v1/runs returns empty list when no runs exist."""
    response = client.get("/api/v1/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == []
    assert data["total"] == 0


def test_list_runs_with_data(client):
    """GET /api/v1/runs returns created runs."""
    _create_run(client)
    _create_run(client)

    response = client.get("/api/v1/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["runs"]) == 2


def test_list_runs_pagination(client):
    """GET /api/v1/runs respects offset and limit."""
    for _ in range(5):
        _create_run(client)

    # First page
    response = client.get("/api/v1/runs?offset=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) == 2
    assert data["total"] == 5
    assert data["offset"] == 0
    assert data["limit"] == 2

    # Second page
    response = client.get("/api/v1/runs?offset=2&limit=2")
    data = response.json()
    assert len(data["runs"]) == 2

    # Last page
    response = client.get("/api/v1/runs?offset=4&limit=2")
    data = response.json()
    assert len(data["runs"]) == 1


def test_list_runs_invalid_offset(client):
    """Negative offset should return 422."""
    response = client.get("/api/v1/runs?offset=-1")
    assert response.status_code == 422


def test_list_runs_limit_too_high(client):
    """Limit > 100 should return 422."""
    response = client.get("/api/v1/runs?limit=101")
    assert response.status_code == 422


def test_run_persists_across_requests(client):
    """Evaluation result should persist and be retrievable."""
    run_id = _create_run(client)

    # Retrieve it
    response = client.get(f"/api/v1/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["results"]["relevance"] == 0.85
    assert data["results"]["estimated_cost"] == 0.001
