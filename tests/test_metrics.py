"""Tests for Prometheus metrics module."""

from __future__ import annotations


def test_metrics_inc_api_requests():
    """API request counter increments without error."""
    from app.observability.metrics import inc_api_requests

    inc_api_requests("GET", "/health", 200)
    inc_api_requests("POST", "/api/v1/evaluations", 201)
    inc_api_requests("GET", "/api/v1/runs/123", 404)


def test_metrics_inc_evaluations():
    """Evaluation counters increment without error."""
    from app.observability.metrics import (
        inc_evaluations_completed,
        inc_evaluations_failed,
        inc_evaluations_started,
        observe_evaluation_duration,
    )

    inc_evaluations_started("rag")
    inc_evaluations_completed("rag")
    inc_evaluations_started("basic")
    inc_evaluations_failed("basic")
    observe_evaluation_duration("rag", 1.5)
    observe_evaluation_duration("basic", 0.3)


def test_metrics_inc_jobs():
    """Job counters increment without error."""
    from app.observability.metrics import (
        inc_job_retries,
        inc_jobs_completed,
        inc_jobs_failed,
        inc_jobs_queued,
        observe_job_duration,
    )

    inc_jobs_queued()
    inc_jobs_completed()
    inc_jobs_failed()
    inc_job_retries()
    observe_job_duration(2.5)


def test_metrics_inc_judge():
    """Judge counters increment without error."""
    from app.observability.metrics import (
        inc_judge_calls,
        inc_judge_failures,
        observe_judge_duration,
    )

    inc_judge_calls("openai")
    inc_judge_failures("openai")
    observe_judge_duration("openai", 3.0)


def test_metrics_active_workers():
    """Active workers gauge works."""
    from app.observability.metrics import set_active_workers

    set_active_workers(3)
    set_active_workers(0)


def test_metrics_response():
    """Metrics endpoint returns valid response."""
    from app.observability.metrics import get_metrics_response

    body, content_type = get_metrics_response()
    assert isinstance(body, bytes)
    assert len(body) > 0
    assert "text/plain" in content_type or "prometheus" in content_type


def test_metrics_idempotent_init():
    """Metrics can be initialized multiple times without error."""
    from app.observability.metrics import _ensure_metrics, _metrics

    _ensure_metrics()
    count_before = len(_metrics)
    _ensure_metrics()
    assert len(_metrics) == count_before
