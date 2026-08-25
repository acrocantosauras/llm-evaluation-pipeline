"""Tests for async batch size limits (job safety)."""

import uuid

from app.api.schemas.jobs import MAX_BATCH_ITEMS, AsyncEvaluationRequest


def _item() -> dict:
    return {
        "conversation": {"model_response": "Answer.", "input_tokens": 10, "output_tokens": 5},
        "context": [{"text": "Context."}],
    }


def test_max_batch_size_is_enforced_by_constant():
    """The schema constant exists and is a sane production bound."""
    assert 1 <= MAX_BATCH_ITEMS <= 1000


def test_batch_at_max_size_accepted():
    req = AsyncEvaluationRequest(items=[_item() for _ in range(MAX_BATCH_ITEMS)])
    assert len(req.items) == MAX_BATCH_ITEMS


def test_oversized_batch_rejected():
    import pytest as _pytest
    from pydantic import ValidationError

    with _pytest.raises(ValidationError):
        AsyncEvaluationRequest(items=[_item() for _ in range(MAX_BATCH_ITEMS + 1)])


def test_oversized_api_request_returns_422(client):
    """End-to-end: the API rejects an oversized batch with a validation error."""
    resp = client.post("/api/v1/evaluations/async", json={"items": [_item() for _ in range(MAX_BATCH_ITEMS + 1)]})
    assert resp.status_code == 422
    detail = str(resp.json())
    assert "items" in detail or "too many" in detail.lower() or str(MAX_BATCH_ITEMS) in detail


def test_empty_batch_rejected(client):
    resp = client.post("/api/v1/evaluations/async", json={"items": []})
    assert resp.status_code == 422


def test_max_size_batch_accepted_via_api(client):
    """A batch at exactly the limit is accepted end-to-end."""
    resp = client.post("/api/v1/evaluations/async", json={"items": [_item() for _ in range(MAX_BATCH_ITEMS)]})
    assert resp.status_code == 202
    data = resp.json()
    assert data["progress"]["total"] == MAX_BATCH_ITEMS
    uuid.UUID(data["job_id"])
