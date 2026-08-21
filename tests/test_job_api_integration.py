BATCH_REQUEST = {
    "items": [
        {
            "conversation": {"model_response": "Drug X reduces fever.", "input_tokens": 20, "output_tokens": 10},
            "context": [{"text": "Drug X is used to treat fever."}],
        },
    ]
}


def test_submit_and_check_job_flow(client):
    """Submit an async job and verify it appears in job list."""
    # Submit
    resp = client.post("/api/v1/evaluations/async", json=BATCH_REQUEST)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # Check status
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["job_id"] == job_id

    # Check it appears in list
    list_resp = client.get("/api/v1/jobs")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1


def test_quality_gate_with_run(client):
    """Create a quality gate, then create a run through the sync API."""
    # Create gate
    gate_resp = client.post(
        "/api/v1/quality-gates",
        json={
            "name": "test-gate",
            "thresholds": {"relevance": {"min": 0.50}},
        },
    )
    assert gate_resp.status_code == 201

    # Create an evaluation
    eval_resp = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Answer.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Context."}],
        },
    )
    assert eval_resp.status_code == 201
    run_id = eval_resp.json()["run_id"]

    # Create baseline from that run
    baseline_resp = client.post(f"/api/v1/baselines?run_id={run_id}", json={"name": "test-baseline"})
    assert baseline_resp.status_code == 201
    baseline_id = baseline_resp.json()["baseline_id"]

    # Create second run
    eval2_resp = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Another.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Context."}],
        },
    )
    run2_id = eval2_resp.json()["run_id"]

    # Compare
    compare_resp = client.get(f"/api/v1/runs/{run2_id}/compare/{baseline_id}")
    assert compare_resp.status_code == 200
    data = compare_resp.json()
    assert "overall" in data
    assert "regressions" in data
    assert "improvements" in data


def test_end_to_end_flow(client):
    """Full flow: sync eval → baseline → second eval → comparison."""
    # 1. Create evaluation
    r1 = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Ibuprofen helps pain.", "input_tokens": 20, "output_tokens": 10},
            "context": [{"text": "Ibuprofen is a pain reliever."}],
        },
    )
    assert r1.status_code == 201
    run1_id = r1.json()["run_id"]

    # 2. Mark as baseline
    b = client.post(f"/api/v1/baselines?run_id={run1_id}", json={"name": "v1.0"})
    assert b.status_code == 201
    baseline_id = b.json()["baseline_id"]

    # 3. Create another evaluation
    r2 = client.post(
        "/api/v1/evaluations",
        json={
            "conversation": {"model_response": "Ibuprofen helps pain.", "input_tokens": 20, "output_tokens": 10},
            "context": [{"text": "Ibuprofen is a pain reliever."}],
        },
    )
    run2_id = r2.json()["run_id"]

    # 4. Compare — same inputs should show no regression
    cmp = client.get(f"/api/v1/runs/{run2_id}/compare/{baseline_id}")
    assert cmp.status_code == 200
    assert cmp.json()["overall"] == "no_regression"

    # 5. Retrieve the run
    run_resp = client.get(f"/api/v1/runs/{run1_id}")
    assert run_resp.status_code == 200
    assert run_resp.json()["run_id"] == run1_id

    # 6. List runs
    runs_list = client.get("/api/v1/runs")
    assert runs_list.status_code == 200
    assert runs_list.json()["total"] == 2
