import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_project, rate_limit_api
from app.api.schemas.baselines import QualityGateResult
from app.api.schemas.jobs import (
    AsyncEvaluationRequest,
    JobResponse,
    PaginatedJobsResponse,
)
from app.db.models import Project
from app.db.session import get_db
from app.observability import metrics
from app.services import redis_queue
from app.services.job_service import (
    count_jobs,
    create_job,
    get_job,
    list_jobs,
)
from app.services.quality_gate_service import evaluate_gate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["jobs"], dependencies=[Depends(rate_limit_api)])


@router.post("/evaluations/async", response_model=JobResponse, status_code=202)
def submit_async_evaluation(
    request: AsyncEvaluationRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> JobResponse:
    """Submit an asynchronous batch evaluation.

    Returns immediately with a job_id. The worker will process items
    in the background.
    Requires authentication.
    """
    items = [item.model_dump() for item in request.items]

    job = create_job(db, items, quality_gate_id=request.quality_gate_id, project_id=project.id)

    # Dispatch to the arq worker pool
    redis_queue.dispatch_job(str(job.id))
    metrics.inc_jobs_queued()

    return JobResponse(
        job_id=job.id,
        status="queued",
        progress={"total": job.total_items, "completed": 0, "failed": 0},
        created_at=job.created_at,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> JobResponse:
    """Get the status and progress of an evaluation job."""
    job = get_job(db, job_id, project_id=project.id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    progress = None
    if job.total_items > 0:
        progress = {
            "total": job.total_items,
            "completed": job.completed_items,
            "failed": job.failed_items,
        }

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        evaluation_run_id=job.evaluation_run_id,
        batch_results=job.batch_results,
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> JobResponse:
    """Cancel a pending or running evaluation job."""
    job = get_job(db, job_id, project_id=project.id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"Job is already in terminal state: {job.status}",
        )

    cancelled = redis_queue.cancel_job(str(job_id))
    if not cancelled:
        raise HTTPException(status_code=409, detail="Job could not be cancelled")

    # Update DB
    from app.services.job_service import mark_job_failed

    mark_job_failed(db, job_id, "Cancelled by user")

    # Re-fetch to get updated state
    job = get_job(db, job_id)
    return JobResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.get("/jobs", response_model=PaginatedJobsResponse)
def list_evaluation_jobs(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> PaginatedJobsResponse:
    """List evaluation jobs with pagination."""
    jobs = list_jobs(db, offset=offset, limit=limit, project_id=project.id)
    total = count_jobs(db, project_id=project.id)

    job_responses = []
    for job in jobs:
        progress = None
        if job.total_items > 0:
            progress = {
                "total": job.total_items,
                "completed": job.completed_items,
                "failed": job.failed_items,
            }
        job_responses.append(
            JobResponse(
                job_id=job.id,
                status=job.status,
                progress=progress,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
            )
        )

    return PaginatedJobsResponse(jobs=job_responses, total=total, offset=offset, limit=limit)


@router.get("/jobs/{job_id}/quality-gate", response_model=QualityGateResult)
def get_job_quality_gate(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> QualityGateResult:
    """Get the quality gate result for a completed job."""
    job = get_job(db, job_id, project_id=project.id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job has not completed yet")

    if not job.quality_gate_id:
        raise HTTPException(status_code=400, detail="No quality gate configured for this job")

    from app.services.quality_gate_service import get_quality_gate

    gate = get_quality_gate(db, job.quality_gate_id)
    if not gate:
        raise HTTPException(status_code=404, detail="Quality gate not found")

    # Aggregate results from batch
    if job.batch_results and "results" in job.batch_results:
        # Use the average of all completed runs
        run_ids = [
            r["run_id"] for r in job.batch_results["results"] if r.get("status") == "completed" and "run_id" in r
        ]
        if run_ids:
            from sqlalchemy import text

            query = text("""
                SELECT
                    AVG(relevance) as avg_relevance,
                    AVG(latency_ms) as avg_latency,
                    AVG(estimated_cost) as avg_cost
                FROM evaluation_runs
                WHERE id = ANY(:ids)
            """)
            result = db.execute(query, {"ids": [str(rid) for rid in run_ids]}).fetchone()

            avg_results = {
                "relevance": float(result[0]) if result[0] else 0,
                "hallucination": {"fraction_supported": 1.0},  # simplified aggregation
                "latency_ms": float(result[1]) if result[1] else 0,
                "estimated_cost": float(result[2]) if result[2] else 0,
            }

            gate_result = evaluate_gate(gate.thresholds, avg_results)
            return QualityGateResult(**gate_result)

    return QualityGateResult(status="fail", checks={})
