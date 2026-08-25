"""Tests for the arq worker task: completion, partial failure, and idempotency."""

import asyncio
import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def worker_session():
    """Provide an in-memory SQLite session for worker tests (same as test_worker.py)."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db.models  # noqa: F401
    from app.db.base import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def worker_env(monkeypatch):
    """Mock heavy evaluator modules and point app.worker's session factory at a test session."""
    mock_relevance = types.ModuleType("evaluator.relevance")
    mock_relevance.relevance_score = MagicMock(return_value=0.85)
    mock_hallucination = types.ModuleType("evaluator.hallucination")
    mock_hallucination.hallucination_report = MagicMock(
        return_value={"fraction_supported": 1.0, "flags": [], "details": []}
    )
    mock_latency = types.ModuleType("evaluator.latency")
    mock_latency.measure_latency = MagicMock(return_value=42.5)
    mock_cost = types.ModuleType("evaluator.cost")
    mock_cost.estimate_cost = MagicMock(return_value=0.001)

    class FakePipeline:
        def evaluate(self, conversation, context):
            return {
                "relevance": 0.85,
                "hallucination": {"fraction_supported": 1.0, "flags": [], "details": []},
                "latency_ms": 42.5,
                "estimated_cost": 0.001,
            }

    mock_pipeline = types.ModuleType("evaluator.pipeline")
    mock_pipeline.EvaluationPipeline = FakePipeline

    for mod_name, mock_mod in [
        ("evaluator.relevance", mock_relevance),
        ("evaluator.hallucination", mock_hallucination),
        ("evaluator.latency", mock_latency),
        ("evaluator.cost", mock_cost),
        ("evaluator.pipeline", mock_pipeline),
    ]:
        sys.modules[mod_name] = mock_mod

    yield

    for mod_name in [
        "evaluator.relevance",
        "evaluator.hallucination",
        "evaluator.latency",
        "evaluator.cost",
        "evaluator.pipeline",
    ]:
        sys.modules.pop(mod_name, None)


def _make_item(ok: bool) -> dict:
    if ok:
        return {
            "conversation": {"model_response": "Answer.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Context."}],
        }
    # Malformed item — missing "conversation" → evaluator raises → item fails
    return {"context": [{"text": "Context."}]}


def _run_job(worker_session, monkeypatch, items):
    import app.worker as worker
    from app.services.job_service import create_job

    job = create_job(worker_session, items)
    job_uuid = job.id  # capture before processing (worker closes/detaches the session)
    monkeypatch.setattr(worker, "SessionLocal", lambda: worker_session)

    result = asyncio.run(worker.process_evaluation_job({"job_try": 1}, str(job_uuid)))
    return job_uuid, result


def test_process_evaluation_job_completes(worker_session, worker_env, monkeypatch):
    from app.db.models import EvaluationRun
    from app.services.job_service import get_job

    items = [_make_item(True), _make_item(True)]
    job_id, result = _run_job(worker_session, monkeypatch, items)

    assert result["status"] == "completed"
    assert result["completed"] == 2
    assert result["failed"] == 0

    job = get_job(worker_session, job_id)
    assert job.status == "completed"
    assert job.completed_items == 2

    runs = worker_session.query(EvaluationRun).filter(EvaluationRun.project_id == job.project_id).all()
    assert len(runs) == 2


def test_process_evaluation_job_partial_failure(worker_session, worker_env, monkeypatch):
    """One malformed item fails; the rest complete — partial failure is isolated."""
    from app.services.job_service import get_job

    items = [_make_item(True), _make_item(False), _make_item(True)]
    job_id, result = _run_job(worker_session, monkeypatch, items)

    assert result["status"] == "completed"  # job completes with partial results
    assert result["completed"] == 2
    assert result["failed"] == 1

    job = get_job(worker_session, job_id)
    assert job.completed_items == 2
    assert job.failed_items == 1
    statuses = {r["status"] for r in job.batch_results["results"]}
    assert statuses == {"completed", "failed"}


def test_process_evaluation_job_is_idempotent(worker_session, worker_env, monkeypatch):
    """Re-processing an already-completed job is a no-op (idempotency)."""
    items = [_make_item(True)]
    job_id, first_result = _run_job(worker_session, monkeypatch, items)
    assert first_result["status"] == "completed"

    # Run again through the same path
    import uuid as uuid_mod

    import app.worker as worker

    result = asyncio.run(worker.process_evaluation_job({"job_try": 1}, str(uuid_mod.UUID(str(job_id)))))
    assert result == {"status": "already_completed"}


def test_process_evaluation_job_missing_job(worker_session, worker_env, monkeypatch):
    """A job id not present in the DB returns an explicit error."""
    import uuid

    import app.worker as worker

    monkeypatch.setattr(worker, "SessionLocal", lambda: worker_session)
    result = asyncio.run(worker.process_evaluation_job({"job_try": 1}, str(uuid.uuid4())))
    assert result == {"error": "job_not_found"}
