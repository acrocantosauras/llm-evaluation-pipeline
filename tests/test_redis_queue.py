import pytest


@pytest.fixture()
def fake_redis(monkeypatch):
    """Provide a fakeredis instance and patch the get_redis_client function."""
    import fakeredis

    fake = fakeredis.FakeRedis(decode_responses=True)

    import app.services.redis_queue as rq

    monkeypatch.setattr(rq, "get_redis_client", lambda: fake)

    yield fake

    fake.flushall()


def test_enqueue_and_dequeue(fake_redis):
    """Enqueue a job and dequeue it."""
    from app.services.redis_queue import dequeue_job, enqueue_job

    enqueue_job("job-123")
    result = dequeue_job()
    assert result == "job-123"


def test_dequeue_empty(fake_redis):
    """Dequeue from empty queue returns None (after timeout)."""
    from app.services.redis_queue import dequeue_job

    result = dequeue_job()
    assert result is None


def test_set_and_get_job_state(fake_redis):
    """Set and get job state."""
    from app.services.redis_queue import get_job_state, set_job_state

    set_job_state("job-456", "running", retry_count=1)
    state = get_job_state("job-456")
    assert state is not None
    assert state["state"] == "running"
    assert state["retry_count"] == 1


def test_get_nonexistent_job_state(fake_redis):
    """Getting state for unknown job returns None."""
    from app.services.redis_queue import get_job_state

    state = get_job_state("nonexistent")
    assert state is None


def test_set_and_get_progress(fake_redis):
    """Set and get job progress."""
    from app.services.redis_queue import get_job_progress, set_job_progress

    set_job_progress("job-789", total=100, completed=50, failed=2)
    progress = get_job_progress("job-789")
    assert progress == {"total": 100, "completed": 50, "failed": 2}


def test_cancel_job(fake_redis):
    """Cancel a queued job."""
    from app.services.redis_queue import cancel_job, get_job_state, set_job_state

    set_job_state("job-cancel", "queued")
    result = cancel_job("job-cancel")
    assert result is True
    assert get_job_state("job-cancel")["state"] == "cancelled"


def test_cancel_completed_job(fake_redis):
    """Cannot cancel an already completed job."""
    from app.services.redis_queue import cancel_job, set_job_state

    set_job_state("job-done", "completed")
    result = cancel_job("job-done")
    assert result is False


def test_cancel_unknown_job(fake_redis):
    """Cannot cancel a job that doesn't exist in Redis."""
    from app.services.redis_queue import cancel_job

    result = cancel_job("unknown-job")
    assert result is False


def test_enqueue_multiple_jobs(fake_redis):
    """Multiple jobs are processed in FIFO order."""
    from app.services.redis_queue import dequeue_job, enqueue_job

    enqueue_job("job-a")
    enqueue_job("job-b")
    enqueue_job("job-c")

    assert dequeue_job() == "job-a"
    assert dequeue_job() == "job-b"
    assert dequeue_job() == "job-c"
    assert dequeue_job() is None
