import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import EvaluationJob

logger = logging.getLogger(__name__)


def _safe_redis_call(func, *args, **kwargs):
    """Execute a Redis call, returning None on any connection error."""
    try:
        return func(*args, **kwargs)
    except Exception:
        return None


def create_job(
    db: Session,
    items: list[dict],
    quality_gate_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> EvaluationJob:
    """Create a new evaluation job."""
    job = EvaluationJob(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        project_id=project_id,
        status="queued",
        total_items=len(items),
        completed_items=0,
        failed_items=0,
        items={"items": items},
        quality_gate_id=quality_gate_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: uuid.UUID, project_id: uuid.UUID | None = None) -> EvaluationJob | None:
    """Get a job by ID, with live progress from Redis (if available)."""
    query = db.query(EvaluationJob).filter(EvaluationJob.id == job_id)
    if project_id is not None:
        query = query.filter(EvaluationJob.project_id == project_id)
    job = query.first()
    if job:
        from app.services.redis_queue import get_job_progress, get_job_state

        redis_state = _safe_redis_call(get_job_state, str(job_id))
        redis_progress = _safe_redis_call(get_job_progress, str(job_id))
        if redis_state:
            job.status = redis_state["state"]
        if redis_progress:
            job.total_items = redis_progress["total"]
            job.completed_items = redis_progress["completed"]
            job.failed_items = redis_progress["failed"]
    return job


def list_jobs(
    db: Session,
    offset: int = 0,
    limit: int = 20,
    project_id: uuid.UUID | None = None,
) -> list[EvaluationJob]:
    """List jobs with pagination, optionally scoped to a project."""
    query = db.query(EvaluationJob)
    if project_id is not None:
        query = query.filter(EvaluationJob.project_id == project_id)
    return query.order_by(EvaluationJob.created_at.desc()).offset(offset).limit(limit).all()


def count_jobs(db: Session, project_id: uuid.UUID | None = None) -> int:
    """Count total jobs, optionally scoped to a project."""
    query = db.query(EvaluationJob)
    if project_id is not None:
        query = query.filter(EvaluationJob.project_id == project_id)
    return query.count()


def mark_job_started(db: Session, job_id: uuid.UUID) -> None:
    """Mark a job as running."""
    job = db.query(EvaluationJob).filter(EvaluationJob.id == job_id).first()
    if job and job.status == "queued":
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()


def mark_job_completed(
    db: Session,
    job_id: uuid.UUID,
    evaluation_run_id: uuid.UUID | None = None,
    batch_results: dict | None = None,
) -> None:
    """Mark a job as completed."""
    job = db.query(EvaluationJob).filter(EvaluationJob.id == job_id).first()
    if job:
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.completed_items = job.total_items
        if evaluation_run_id:
            job.evaluation_run_id = evaluation_run_id
        if batch_results:
            job.batch_results = batch_results
        db.commit()


def mark_job_failed(db: Session, job_id: uuid.UUID, error_message: str) -> None:
    """Mark a job as failed."""
    job = db.query(EvaluationJob).filter(EvaluationJob.id == job_id).first()
    if job:
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message
        db.commit()
