import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas.runs import PaginatedRunsResponse, RunResponse
from app.db.session import get_db
from app.services.evaluation_service import count_runs, get_run, list_runs

router = APIRouter(prefix="/api/v1", tags=["runs"])


def _run_to_response(run) -> RunResponse:
    return RunResponse(
        run_id=run.id,
        status=run.status,
        results={
            "relevance": run.relevance,
            "hallucination": run.hallucination,
            "latency_ms": run.latency_ms,
            "estimated_cost": run.estimated_cost,
        },
        created_at=run.created_at,
    )


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_evaluation_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> RunResponse:
    """Retrieve a specific evaluation run by ID."""
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return _run_to_response(run)


@router.get("/runs", response_model=PaginatedRunsResponse)
def get_evaluation_runs(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    db: Session = Depends(get_db),
) -> PaginatedRunsResponse:
    """List evaluation runs with pagination."""
    runs = list_runs(db, offset=offset, limit=limit)
    total = count_runs(db)
    return PaginatedRunsResponse(
        runs=[_run_to_response(r) for r in runs],
        total=total,
        offset=offset,
        limit=limit,
    )
