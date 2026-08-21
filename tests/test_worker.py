"""Tests for worker processing logic (job_service layer)."""

import pytest


@pytest.fixture()
def worker_session():
    """Provide a database session for worker tests with in-memory SQLite."""
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


def test_job_create_and_get(worker_session):
    """Create a job and retrieve it."""
    from app.services.job_service import create_job, get_job

    items = [
        {
            "conversation": {"model_response": "Test.", "input_tokens": 10, "output_tokens": 5},
            "context": [{"text": "Ctx."}],
        },
    ]
    job = create_job(worker_session, items)
    assert job.status == "queued"
    assert job.total_items == 1

    retrieved = get_job(worker_session, job.id)
    assert retrieved is not None
    assert retrieved.id == job.id


def test_job_mark_completed(worker_session):
    """Mark a job as completed."""
    from app.db.models import EvaluationRun
    from app.services.job_service import create_job, get_job, mark_job_completed

    # Create a run first so the FK is valid
    run = EvaluationRun(
        conversation={"model_response": "x"},
        context={"chunks": [{"text": "y"}]},
    )
    worker_session.add(run)
    worker_session.commit()

    job = create_job(worker_session, [{"conversation": {}, "context": []}])
    mark_job_completed(worker_session, job.id, evaluation_run_id=run.id)

    updated = get_job(worker_session, job.id)
    assert updated.status == "completed"


def test_job_mark_failed(worker_session):
    """Mark a job as failed with error message."""
    from app.services.job_service import create_job, get_job, mark_job_failed

    job = create_job(worker_session, [{"conversation": {}, "context": []}])
    mark_job_failed(worker_session, job.id, "Something went wrong")

    updated = get_job(worker_session, job.id)
    assert updated.status == "failed"
    assert updated.error_message == "Something went wrong"


def test_job_list_and_count(worker_session):
    """List and count jobs."""
    from app.services.job_service import count_jobs, create_job, list_jobs

    for _ in range(3):
        create_job(worker_session, [{"conversation": {}, "context": []}])

    assert count_jobs(worker_session) == 3
    assert len(list_jobs(worker_session)) == 3
    assert len(list_jobs(worker_session, limit=2)) == 2


def test_job_mark_started(worker_session):
    """Mark a job as running sets started_at."""
    from app.services.job_service import create_job, get_job, mark_job_started

    job = create_job(worker_session, [{"conversation": {}, "context": []}])
    mark_job_started(worker_session, job.id)

    updated = get_job(worker_session, job.id)
    assert updated.status == "running"
    assert updated.started_at is not None


def test_job_idempotency(worker_session):
    """A completed job stays completed on re-read."""
    from app.db.models import EvaluationRun
    from app.services.job_service import create_job, get_job, mark_job_completed

    # Create a run first so the FK is valid
    run = EvaluationRun(
        conversation={"model_response": "x"},
        context={"chunks": [{"text": "y"}]},
    )
    worker_session.add(run)
    worker_session.commit()

    job = create_job(worker_session, [{"conversation": {}, "context": []}])
    mark_job_completed(worker_session, job.id, evaluation_run_id=run.id)

    updated = get_job(worker_session, job.id)
    assert updated.status == "completed"
    assert updated.evaluation_run_id == run.id
