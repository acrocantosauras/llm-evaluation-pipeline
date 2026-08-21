import uuid

from tests.conftest import VALID_REQUEST


def test_create_evaluation_success(client):
    """POST /api/v1/evaluations creates a new evaluation run."""
    response = client.post("/api/v1/evaluations", json=VALID_REQUEST)
    assert response.status_code == 201
    data = response.json()

    assert "run_id" in data
    assert data["status"] == "completed"
    assert "results" in data
    assert "relevance" in data["results"]
    assert "hallucination" in data["results"]
    assert "latency_ms" in data["results"]
    assert "estimated_cost" in data["results"]
    assert "created_at" in data

    # Verify the run_id is a valid UUID
    uuid.UUID(data["run_id"])


def test_create_evaluation_response_types(client):
    """Evaluation response should have correct types."""
    response = client.post("/api/v1/evaluations", json=VALID_REQUEST)
    assert response.status_code == 201
    data = response.json()
    results = data["results"]

    assert isinstance(results["relevance"], (int, float))
    assert isinstance(results["hallucination"], dict)
    assert isinstance(results["latency_ms"], (int, float))
    assert isinstance(results["estimated_cost"], (int, float))


def test_create_evaluation_empty_model_response(client):
    """Empty model_response should still produce valid results."""
    request = {
        "conversation": {
            "model_response": "",
            "input_tokens": 10,
            "output_tokens": 0,
        },
        "context": [{"text": "Some context."}],
    }
    response = client.post("/api/v1/evaluations", json=request)
    assert response.status_code == 201


def test_create_evaluation_missing_conversation(client):
    """Missing conversation field should return 422."""
    response = client.post("/api/v1/evaluations", json={"context": [{"text": "ctx"}]})
    assert response.status_code == 422


def test_create_evaluation_missing_context(client):
    """Missing context field should return 422."""
    response = client.post(
        "/api/v1/evaluations",
        json={"conversation": {"model_response": "test"}},
    )
    assert response.status_code == 422


def test_create_evaluation_empty_context(client):
    """Empty context list should return 422 (min_length=1)."""
    response = client.post(
        "/api/v1/evaluations",
        json={"conversation": {"model_response": "test"}, "context": []},
    )
    assert response.status_code == 422


def test_create_evaluation_negative_tokens(client):
    """Negative token counts should return 422."""
    request = {
        "conversation": {
            "model_response": "test",
            "input_tokens": -1,
            "output_tokens": 5,
        },
        "context": [{"text": "ctx"}],
    }
    response = client.post("/api/v1/evaluations", json=request)
    assert response.status_code == 422
