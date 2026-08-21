import uuid

BATCH_REQUEST = {
    "items": [
        {
            "conversation": {"model_response": "Drug X reduces fever.", "input_tokens": 20, "output_tokens": 10},
            "context": [{"text": "Drug X is used to treat fever."}],
        },
        {
            "conversation": {"model_response": "Drug Y causes drowsiness.", "input_tokens": 20, "output_tokens": 10},
            "context": [{"text": "Drug Y may cause drowsiness and nausea."}],
        },
    ]
}


def test_submit_async_evaluation(client):
    """POST /api/v1/evaluations/async returns 202 with job_id."""
    response = client.post("/api/v1/evaluations/async", json=BATCH_REQUEST)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["progress"]["total"] == 2
    assert data["progress"]["completed"] == 0
    uuid.UUID(data["job_id"])


def test_submit_async_single_item(client):
    """Async endpoint works with a single item batch."""
    single = {"items": [BATCH_REQUEST["items"][0]]}
    response = client.post("/api/v1/evaluations/async", json=single)
    assert response.status_code == 202
    assert response.json()["progress"]["total"] == 1


def test_submit_async_empty_items(client):
    """Empty items list should return 422."""
    response = client.post("/api/v1/evaluations/async", json={"items": []})
    assert response.status_code == 422


def test_submit_async_missing_items(client):
    """Missing items field should return 422."""
    response = client.post("/api/v1/evaluations/async", json={})
    assert response.status_code == 422


def test_get_job_status(client):
    """GET /api/v1/jobs/{id} returns job info."""
    resp = client.post("/api/v1/evaluations/async", json=BATCH_REQUEST)
    job_id = resp.json()["job_id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] in ("queued", "running", "completed", "failed", "cancelled")


def test_get_job_not_found(client):
    """GET /api/v1/jobs/{id} returns 404 for unknown job."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/jobs/{fake_id}")
    assert response.status_code == 404


def test_list_jobs_empty(client):
    """GET /api/v1/jobs returns empty list initially."""
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["jobs"] == []
    assert data["total"] == 0


def test_list_jobs_with_data(client):
    """GET /api/v1/jobs returns submitted jobs."""
    client.post("/api/v1/evaluations/async", json=BATCH_REQUEST)
    client.post("/api/v1/evaluations/async", json=BATCH_REQUEST)

    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["jobs"]) == 2


def test_list_jobs_pagination(client):
    """GET /api/v1/jobs respects offset/limit."""
    for _ in range(3):
        client.post("/api/v1/evaluations/async", json=BATCH_REQUEST)

    response = client.get("/api/v1/jobs?offset=0&limit=2")
    data = response.json()
    assert len(data["jobs"]) == 2
    assert data["total"] == 3

    response = client.get("/api/v1/jobs?offset=2&limit=2")
    data = response.json()
    assert len(data["jobs"]) == 1


def test_cancel_job(client):
    """POST /api/v1/jobs/{id}/cancel marks job as cancelled."""
    resp = client.post("/api/v1/evaluations/async", json=BATCH_REQUEST)
    job_id = resp.json()["job_id"]

    response = client.post(f"/api/v1/jobs/{job_id}/cancel")
    # May return 200 (cancelled) or 409 (already terminal)
    assert response.status_code in (200, 409)


def test_cancel_nonexistent_job(client):
    """Cancel a non-existent job returns 404."""
    fake_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/jobs/{fake_id}/cancel")
    assert response.status_code == 404


def test_submit_async_invalid_item(client):
    """Invalid item in batch should return 422."""
    bad_request = {"items": [{"conversation": {}, "context": []}]}
    response = client.post("/api/v1/evaluations/async", json=bad_request)
    assert response.status_code == 422
