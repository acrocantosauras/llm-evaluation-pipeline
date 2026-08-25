import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_project, rate_limit_api
from app.api.schemas.evaluations import (
    EvaluationRequest,
    EvaluationResponse,
    MetricResultSchema,
)
from app.db.models import Project
from app.db.session import get_db
from app.observability import metrics
from app.services.evaluation_service import get_metric_results, run_evaluation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["evaluations"], dependencies=[Depends(rate_limit_api)])


@router.post("/evaluations", response_model=EvaluationResponse, status_code=201)
def create_evaluation(
    request: EvaluationRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_current_project),
) -> EvaluationResponse:
    """Submit an evaluation request.

    Runs the evaluation engine and persists the result.
    Supports profiles: basic, rag, rag_strict, judge.
    Requires authentication.
    """
    profile = request.profile
    metrics.inc_evaluations_started(profile)
    started = time.time()
    try:
        conversation = {
            "model_response": request.conversation.model_response,
            "question": request.conversation.question,
            "input_tokens": request.conversation.input_tokens,
            "output_tokens": request.conversation.output_tokens,
            "reference_answer": request.conversation.reference_answer,
            "citations": [c.model_dump() for c in request.conversation.citations],
        }
        if request.conversation.latency_ms is not None:
            conversation["latency_ms"] = request.conversation.latency_ms

        context = {"chunks": [c.model_dump() for c in request.context]}

        run = run_evaluation(
            db,
            conversation,
            context,
            profile=request.profile,
            judge_config=request.judge_config,
            project_id=project.id,
        )

        # Get advanced metric results
        metric_records = get_metric_results(db, run.id)
        metric_results = [
            MetricResultSchema(
                metric=m.metric,
                score=m.score,
                evaluator_version=m.evaluator_version,
                passed=m.passed,
                details=m.details or {},
                error=m.error,
            )
            for m in metric_records
        ]

        metrics.inc_evaluations_completed(profile)
        metrics.observe_evaluation_duration(profile, time.time() - started)

        return EvaluationResponse(
            run_id=run.id,
            status=run.status,
            results={
                "relevance": run.relevance,
                "hallucination": run.hallucination,
                "latency_ms": run.latency_ms,
                "estimated_cost": run.estimated_cost,
            },
            profile=run.profile,
            composite_score=run.composite_score,
            metric_results=metric_results,
            created_at=run.created_at,
        )
    except Exception as exc:
        metrics.inc_evaluations_failed(profile)
        logger.exception("Evaluation failed")
        raise HTTPException(status_code=500, detail="Evaluation processing failed") from exc
