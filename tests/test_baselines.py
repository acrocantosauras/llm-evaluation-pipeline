import uuid


def test_create_baseline(client):
    """POST /api/v1/baselines creates a baseline from a run."""
    # First create a run
    run_resp = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Test response.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Context."}],
        },
    )
    run_id = run_resp.json()["run_id"]

    # Create baseline
    response = client.post(f"/api/v1/baselines?run_id={run_id}", json={"name": "v1"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "v1"
    assert data["run_id"] == run_id
    uuid.UUID(data["baseline_id"])


def test_create_baseline_unknown_run(client):
    """Creating baseline with unknown run returns 404."""
    fake_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/baselines?run_id={fake_id}", json={"name": "x"})
    assert response.status_code == 404


def test_list_baselines(client):
    """GET /api/v1/baselines lists all baselines."""
    # Create a run and baseline
    run_resp = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Test.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Ctx."}],
        },
    )
    run_id = run_resp.json()["run_id"]
    client.post(f"/api/v1/baselines?run_id={run_id}", json={"name": "b1"})

    response = client.get("/api/v1/baselines")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_baseline(client):
    """GET /api/v1/baselines/{id} returns specific baseline."""
    run_resp = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Test.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Ctx."}],
        },
    )
    run_id = run_resp.json()["run_id"]
    resp = client.post(f"/api/v1/baselines?run_id={run_id}", json={"name": "get-me"})
    baseline_id = resp.json()["baseline_id"]

    response = client.get(f"/api/v1/baselines/{baseline_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "get-me"


def test_compare_no_regression(client):
    """Comparing two identical runs shows no regression."""
    # Create two runs with same input → same mock output
    run1 = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Same.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Ctx."}],
        },
    ).json()

    run2 = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Same.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Ctx."}],
        },
    ).json()

    # Create baseline from run1
    baseline = client.post(f"/api/v1/baselines?run_id={run1['run_id']}", json={"name": "base"}).json()

    # Compare run2 against baseline
    response = client.get(f"/api/v1/runs/{run2['run_id']}/compare/{baseline['baseline_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["overall"] == "no_regression"
    assert len(data["regressions"]) == 0


def test_compare_with_different_runs(client):
    """Comparing runs with different mock outputs detects changes."""
    # Create run with custom latency
    run1 = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Fast.", "input_tokens": 10, "output_tokens": 5, "latency_ms": 100},
            "context": [{"text": "Ctx."}],
        },
    ).json()

    run2 = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Slow.", "input_tokens": 10, "output_tokens": 5, "latency_ms": 5000},
            "context": [{"text": "Ctx."}],
        },
    ).json()

    baseline = client.post(f"/api/v1/baselines?run_id={run1['run_id']}", json={"name": "fast-base"}).json()

    response = client.get(f"/api/v1/runs/{run2['run_id']}/compare/{baseline['baseline_id']}")
    assert response.status_code == 200
    data = response.json()
    # Both runs use mock evaluator with same relevance/cost, but latency differs
    assert "overall" in data
    assert "regressions" in data
    assert "improvements" in data


def test_compare_unknown_baseline(client):
    """Comparing against unknown baseline returns 404."""
    run_resp = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Test.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Ctx."}],
        },
    )
    run_id = run_resp.json()["run_id"]
    fake_baseline = str(uuid.uuid4())
    response = client.get(f"/api/v1/runs/{run_id}/compare/{fake_baseline}")
    assert response.status_code == 404


def test_detect_regressions_service():
    """Test regression detection logic directly."""
    from app.db.models import EvaluationRun
    from app.services.baseline_service import detect_regressions

    baseline_run = EvaluationRun(
        id=uuid.uuid4(),
        conversation={"model_response": "x"},
        context={"chunks": [{"text": "y"}]},
        relevance=0.95,
        hallucination={"fraction_supported": 0.98},
        latency_ms=200,
        estimated_cost=0.001,
    )

    current_run = EvaluationRun(
        id=uuid.uuid4(),
        conversation={"model_response": "x"},
        context={"chunks": [{"text": "y"}]},
        relevance=0.70,
        hallucination={"fraction_supported": 0.80},
        latency_ms=1000,
        estimated_cost=0.005,
    )

    result = detect_regressions(baseline_run, current_run)
    assert result["overall"] == "regression_detected"
    assert len(result["regressions"]) > 0

    # Verify metrics are identified
    regressed_metrics = [r["metric"] for r in result["regressions"]]
    assert "relevance" in regressed_metrics
    assert "latency_ms" in regressed_metrics
