import logging
import time
import uuid
from datetime import datetime, timezone

from arq.connections import RedisSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.enums import JobStatus
from app.db.models import EvaluationJob, EvaluationRun  # noqa: F401
from app.observability import metrics
from app.services.redis_queue import (
    get_job_state,
    set_job_progress,
    set_job_state,
)

logger = logging.getLogger(__name__)

# Create engine directly (not via session.py) for worker isolation
settings = get_settings()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _is_cancelled(job_id: str) -> bool:
    """Check if a job has been cancelled."""
    state = get_job_state(job_id)
    return state is not None and state.get("state") == JobStatus.CANCELLED


async def process_evaluation_job(ctx: dict, job_id: str, max_retries: int = 3) -> dict:
    """Process a single evaluation job from the queue.

    This is the main arq task that workers execute.
    """
    db = SessionLocal()
    retry_count = ctx.get("job_try", 1)
    job_started = time.time()
    logger.info("Starting job %s (attempt %d)", job_id, retry_count)
    if retry_count > 1:
        metrics.inc_job_retries()

    try:
        # Check if already completed (idempotency)
        job = db.query(EvaluationJob).filter(EvaluationJob.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error("Job %s not found in database", job_id)
            return {"error": "job_not_found"}

        if job.status == JobStatus.COMPLETED:
            logger.info("Job %s already completed, skipping (idempotency)", job_id)
            return {"status": "already_completed"}

        if job.status == JobStatus.CANCELLED:
            logger.info("Job %s was cancelled before processing", job_id)
            return {"status": "cancelled"}

        # Mark as running (idempotent — already running from a retry is fine)
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        set_job_state(job_id, JobStatus.RUNNING)

        # Load items
        items_data = job.items.get("items", [])
        total = len(items_data)
        completed = 0
        failed = 0
        batch_results = []

        for i, item in enumerate(items_data):
            # Check cancellation before each item
            if _is_cancelled(job_id):
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                set_job_state(job_id, JobStatus.CANCELLED)
                logger.info("Job %s cancelled at item %d/%d", job_id, i, total)
                return {"status": "cancelled"}

            try:
                from evaluator.pipeline import EvaluationPipeline

                pipeline = EvaluationPipeline()
                # The pipeline expects context as {"chunks": [...]}, matching the
                # sync path (app/api/routes/evaluations.py). Batch items carry
                # context as a bare list[ContextChunk], so wrap it here.
                result = pipeline.evaluate(item["conversation"], {"chunks": item["context"]})

                # Persist individual run
                run = EvaluationRun(
                    id=uuid.uuid4(),
                    created_at=datetime.now(timezone.utc),
                    project_id=job.project_id,
                    status="completed",
                    conversation=item["conversation"],
                    context={"chunks": item["context"]},
                    relevance=result.get("relevance"),
                    hallucination=result.get("hallucination"),
                    latency_ms=result.get("latency_ms"),
                    estimated_cost=result.get("estimated_cost"),
                )
                db.add(run)
                db.commit()

                batch_results.append({"run_id": str(run.id), "status": "completed"})
                completed += 1

            except Exception as item_exc:
                logger.exception("Item %d failed in job %s", i, job_id)
                batch_results.append({"index": i, "status": "failed", "error": str(item_exc)})
                failed += 1
                db.rollback()

            # Update progress
            set_job_progress(job_id, total, completed, failed)
            job.completed_items = completed
            job.failed_items = failed
            db.commit()

        # Mark job completed
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.batch_results = {"results": batch_results}
        db.commit()
        set_job_state(job_id, JobStatus.COMPLETED, completed=completed, failed=failed)
        metrics.inc_jobs_completed()
        metrics.observe_job_duration(time.time() - job_started)

        logger.info(
            "Job %s completed: %d/%d succeeded, %d failed",
            job_id,
            completed,
            total,
            failed,
        )
        return {"status": "completed", "completed": completed, "failed": failed}

    except Exception as exc:
        logger.exception("Job %s failed with error", job_id)
        try:
            job = db.query(EvaluationJob).filter(EvaluationJob.id == uuid.UUID(job_id)).first()
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = str(exc)[:1000]
                db.commit()
            set_job_state(job_id, JobStatus.FAILED, error=str(exc)[:500])
        except Exception:
            logger.exception("Failed to update job %s failure state", job_id)

        # Retry if under limit
        if retry_count < max_retries:
            raise  # arq will retry

        metrics.inc_jobs_failed()
        return {"status": "failed", "error": str(exc)[:500]}

    finally:
        db.close()


async def startup(ctx: dict) -> None:
    """Worker startup hook."""
    # Expose a Prometheus metrics endpoint so Prometheus can scrape the worker
    # at worker:8000/metrics (see config/prometheus.yml). Runs in a background
    # thread and does not interfere with the arq asyncio event loop.
    try:
        from prometheus_client import start_http_server

        start_http_server(8000)
        logger.info("Worker metrics server listening on :8000/metrics")
    except Exception:
        logger.warning("Could not start worker metrics server", exc_info=True)
    metrics.set_active_workers(settings.WORKER_CONCURRENCY)
    logger.info("Worker starting up")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown hook."""
    metrics.set_active_workers(0)
    logger.info("Worker shutting down")


# arq worker settings
class WorkerSettings:
    """Configuration for the arq worker."""

    functions = [process_evaluation_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = settings.WORKER_CONCURRENCY
    max_tries = settings.WORKER_MAX_RETRIES
    job_timeout = 300  # 5 minutes per job
    health_check_interval = 10


if __name__ == "__main__":
    # Entrypoint for `python -m app.worker` (used by docker-compose.prod.yml).
    # Mirrors the dev-stack command `arq app.worker.WorkerSettings`.
    from arq import run_worker

    run_worker(WorkerSettings)
