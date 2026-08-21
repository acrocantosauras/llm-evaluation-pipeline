import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.evaluations import EvaluationRequest, EvaluationResponse
from app.db.session import get_db
from app.services.evaluation_service import run_evaluation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["evaluations"])


@router.post("/evaluations", response_model=EvaluationResponse, status_code=201)
def create_evaluation(request: EvaluationRequest, db: Session = Depends(get_db)) -> EvaluationResponse:
    """Submit an evaluation request.

    Runs the evaluation engine and persists the result.
    """
    try:
        conversation = {
            "model_response": request.conversation.model_response,
            "input_tokens": request.conversation.input_tokens,
            "output_tokens": request.conversation.output_tokens,
        }
        if request.conversation.latency_ms is not None:
            conversation["latency_ms"] = request.conversation.latency_ms

        context = {"chunks": [c.model_dump() for c in request.context]}

        run = run_evaluation(db, conversation, context)

        return EvaluationResponse(
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
    except Exception as exc:
        logger.exception("Evaluation failed")
        raise HTTPException(status_code=500, detail="Evaluation processing failed") from exc
