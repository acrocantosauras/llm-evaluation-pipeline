"""Prometheus-compatible metrics for the evaluation platform.

All counters and histograms are created lazily so that missing prometheus_client
does not crash the application — metrics simply become no-ops.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy Prometheus client import
_PROM = None


def _get_prom():
    global _PROM
    if _PROM is None:
        try:
            from prometheus_client import (
                CONTENT_TYPE_LATEST,
                Counter,
                Gauge,
                Histogram,
                generate_latest,
            )

            _PROM = {
                "Counter": Counter,
                "Gauge": Gauge,
                "Histogram": Histogram,
                "generate_latest": generate_latest,
                "CONTENT_TYPE_LATEST": CONTENT_TYPE_LATEST,
            }
        except ImportError:
            logger.warning("prometheus_client not installed — metrics disabled")
            _PROM = False
    return _PROM if _PROM is not False else None


# ── Metric Definitions ────────────────────────────────────────────────────────

_metrics: dict[str, Any] = {}


def _ensure_metrics():
    """Create Prometheus metric objects on first use."""
    if _metrics:
        return
    prom = _get_prom()
    if not prom:
        return
    Counter_ = prom["Counter"]
    Histogram_ = prom["Histogram"]
    Gauge_ = prom["Gauge"]

    # API metrics
    _metrics["api_requests_total"] = Counter_(
        "llm_eval_api_requests_total",
        "Total API requests",
        ["method", "path", "status"],
    )
    _metrics["api_request_duration_seconds"] = Histogram_(
        "llm_eval_api_request_duration_seconds",
        "API request duration",
        ["method", "path"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    # Evaluation metrics
    _metrics["evaluations_started_total"] = Counter_(
        "llm_eval_evaluations_started_total",
        "Total evaluations started",
        ["profile"],
    )
    _metrics["evaluations_completed_total"] = Counter_(
        "llm_eval_evaluations_completed_total",
        "Total evaluations completed",
        ["profile"],
    )
    _metrics["evaluations_failed_total"] = Counter_(
        "llm_eval_evaluations_failed_total",
        "Total evaluations failed",
        ["profile"],
    )
    _metrics["evaluation_duration_seconds"] = Histogram_(
        "llm_eval_evaluation_duration_seconds",
        "Evaluation duration",
        ["profile"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    )

    # Worker metrics
    _metrics["jobs_queued_total"] = Counter_(
        "llm_eval_jobs_queued_total",
        "Total jobs queued",
    )
    _metrics["jobs_completed_total"] = Counter_(
        "llm_eval_jobs_completed_total",
        "Total jobs completed",
    )
    _metrics["jobs_failed_total"] = Counter_(
        "llm_eval_jobs_failed_total",
        "Total jobs failed",
    )
    _metrics["job_duration_seconds"] = Histogram_(
        "llm_eval_job_duration_seconds",
        "Job processing duration",
        buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    )
    _metrics["job_retries_total"] = Counter_(
        "llm_eval_job_retries_total",
        "Total job retries",
    )

    # Judge metrics
    _metrics["judge_calls_total"] = Counter_(
        "llm_eval_judge_calls_total",
        "Total LLM judge calls",
        ["provider"],
    )
    _metrics["judge_failures_total"] = Counter_(
        "llm_eval_judge_failures_total",
        "Total LLM judge failures",
        ["provider"],
    )
    _metrics["judge_duration_seconds"] = Histogram_(
        "llm_eval_judge_duration_seconds",
        "LLM judge call duration",
        ["provider"],
        buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    )

    # Active gauge
    _metrics["active_workers"] = Gauge_(
        "llm_eval_active_workers",
        "Number of active workers",
    )


# ── Public API ────────────────────────────────────────────────────────────────


def inc_api_requests(method: str, path: str, status: int) -> None:
    _ensure_metrics()
    m = _metrics.get("api_requests_total")
    if m:
        m.labels(method=method, path=path, status=str(status)).inc()


def observe_api_duration(method: str, path: str, duration: float) -> None:
    _ensure_metrics()
    m = _metrics.get("api_request_duration_seconds")
    if m:
        m.labels(method=method, path=path).observe(duration)


def inc_evaluations_started(profile: str) -> None:
    _ensure_metrics()
    m = _metrics.get("evaluations_started_total")
    if m:
        m.labels(profile=profile).inc()


def inc_evaluations_completed(profile: str) -> None:
    _ensure_metrics()
    m = _metrics.get("evaluations_completed_total")
    if m:
        m.labels(profile=profile).inc()


def inc_evaluations_failed(profile: str) -> None:
    _ensure_metrics()
    m = _metrics.get("evaluations_failed_total")
    if m:
        m.labels(profile=profile).inc()


def observe_evaluation_duration(profile: str, duration: float) -> None:
    _ensure_metrics()
    m = _metrics.get("evaluation_duration_seconds")
    if m:
        m.labels(profile=profile).observe(duration)


def inc_jobs_queued() -> None:
    _ensure_metrics()
    m = _metrics.get("jobs_queued_total")
    if m:
        m.inc()


def inc_jobs_completed() -> None:
    _ensure_metrics()
    m = _metrics.get("jobs_completed_total")
    if m:
        m.inc()


def inc_jobs_failed() -> None:
    _ensure_metrics()
    m = _metrics.get("jobs_failed_total")
    if m:
        m.inc()


def observe_job_duration(duration: float) -> None:
    _ensure_metrics()
    m = _metrics.get("job_duration_seconds")
    if m:
        m.observe(duration)


def inc_job_retries() -> None:
    _ensure_metrics()
    m = _metrics.get("job_retries_total")
    if m:
        m.inc()


def inc_judge_calls(provider: str) -> None:
    _ensure_metrics()
    m = _metrics.get("judge_calls_total")
    if m:
        m.labels(provider=provider).inc()


def inc_judge_failures(provider: str) -> None:
    _ensure_metrics()
    m = _metrics.get("judge_failures_total")
    if m:
        m.labels(provider=provider).inc()


def observe_judge_duration(provider: str, duration: float) -> None:
    _ensure_metrics()
    m = _metrics.get("judge_duration_seconds")
    if m:
        m.labels(provider=provider).observe(duration)


def set_active_workers(count: int) -> None:
    _ensure_metrics()
    m = _metrics.get("active_workers")
    if m:
        m.set(count)


def get_metrics_response() -> tuple[bytes, str]:
    """Return Prometheus metrics as (body, content_type)."""
    _ensure_metrics()
    prom = _get_prom()
    if prom:
        return prom["generate_latest"](), prom["CONTENT_TYPE_LATEST"]
    return b"# No metrics available (prometheus_client not installed)\n", "text/plain"
