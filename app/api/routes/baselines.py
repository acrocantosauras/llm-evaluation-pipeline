import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_project, rate_limit_api
from app.api.schemas.baselines import (
    BaselineCreate,
    BaselineResponse,
    ComparisonResponse,
    QualityGateCreate,
    QualityGateResponse,
    RegressionEntry,
)
from app.db.models import Project
from app.db.session import get_db
from app.services.baseline_service import (
    create_baseline,
    detect_regressions,
    get_baseline,
    list_baselines,
)
from app.services.evaluation_service import get_run
from app.services.quality_gate_service import (
    create_quality_gate,
    get_quality_gate,
    list_quality_gates,
)

router = APIRouter(prefix="/api/v1", tags=["baselines"], dependencies=[Depends(rate_limit_api)])


# ── Baselines ──────────────────────────────────────────────────────────────────


@router.post("/baselines", response_model=BaselineResponse, status_code=201)
def create_new_baseline(
    request: BaselineCreate,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> BaselineResponse:
    """Create a baseline from an existing evaluation run."""
    try:
        baseline = create_baseline(db, run_id, request.name, request.description, project_id=project.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return BaselineResponse(
        baseline_id=baseline.id,
        name=baseline.name,
        description=baseline.description,
        run_id=baseline.run_id,
        created_at=baseline.created_at,
    )


@router.get("/baselines", response_model=list[BaselineResponse])
def list_all_baselines(
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> list[BaselineResponse]:
    """List all baselines."""
    baselines = list_baselines(db, project_id=project.id)
    return [
        BaselineResponse(
            baseline_id=b.id,
            name=b.name,
            description=b.description,
            run_id=b.run_id,
            created_at=b.created_at,
        )
        for b in baselines
    ]


@router.get("/baselines/{baseline_id}", response_model=BaselineResponse)
def get_single_baseline(
    baseline_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> BaselineResponse:
    """Get a specific baseline."""
    baseline = get_baseline(db, baseline_id, project_id=project.id)
    if not baseline:
        raise HTTPException(status_code=404, detail=f"Baseline {baseline_id} not found")

    return BaselineResponse(
        baseline_id=baseline.id,
        name=baseline.name,
        description=baseline.description,
        run_id=baseline.run_id,
        created_at=baseline.created_at,
    )


@router.get("/runs/{run_id}/compare/{baseline_id}", response_model=ComparisonResponse)
def compare_run_to_baseline(
    run_id: uuid.UUID,
    baseline_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> ComparisonResponse:
    """Compare an evaluation run against a baseline for regressions."""
    baseline = get_baseline(db, baseline_id, project_id=project.id)
    if not baseline:
        raise HTTPException(status_code=404, detail=f"Baseline {baseline_id} not found")

    baseline_run = get_run(db, baseline.run_id, project_id=project.id)
    current_run = get_run(db, run_id, project_id=project.id)
    if not baseline_run:
        raise HTTPException(status_code=404, detail="Baseline run not found")
    if not current_run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    result = detect_regressions(baseline_run, current_run)

    return ComparisonResponse(
        overall=result["overall"],
        baseline_id=result["baseline_id"],
        regressions=[RegressionEntry(**r) for r in result["regressions"]],
        improvements=[RegressionEntry(**r) for r in result["improvements"]],
    )


# ── Quality Gates ──────────────────────────────────────────────────────────────


logger = logging.getLogger(__name__)


@router.post("/quality-gates", response_model=QualityGateResponse, status_code=201)
def create_new_quality_gate(
    request: QualityGateCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> QualityGateResponse:
    """Create a new quality gate configuration."""
    try:
        gate = create_quality_gate(db, request.name, request.thresholds, project_id=project.id)
    except Exception as exc:
        logger.exception("Failed to create quality gate")
        raise HTTPException(
            status_code=409, detail=f"Quality gate '{request.name}' already exists or creation failed"
        ) from exc
    return QualityGateResponse(
        gate_id=gate.id,
        name=gate.name,
        thresholds=gate.thresholds,
        enabled=gate.enabled,
        created_at=gate.created_at,
    )


@router.get("/quality-gates", response_model=list[QualityGateResponse])
def list_all_quality_gates(
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> list[QualityGateResponse]:
    """List all quality gates."""
    gates = list_quality_gates(db, project_id=project.id)
    return [
        QualityGateResponse(
            gate_id=g.id,
            name=g.name,
            thresholds=g.thresholds,
            enabled=g.enabled,
            created_at=g.created_at,
        )
        for g in gates
    ]


@router.get("/quality-gates/{gate_id}", response_model=QualityGateResponse)
def get_single_quality_gate(
    gate_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> QualityGateResponse:
    """Get a specific quality gate."""
    gate = get_quality_gate(db, gate_id, project_id=project.id)
    if not gate:
        raise HTTPException(status_code=404, detail=f"Quality gate {gate_id} not found")

    return QualityGateResponse(
        gate_id=gate.id,
        name=gate.name,
        thresholds=gate.thresholds,
        enabled=gate.enabled,
        created_at=gate.created_at,
    )
