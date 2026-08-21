import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import EvaluationRun
from evaluator.pipeline import EvaluationPipeline


def run_evaluation(
    db: Session,
    conversation: dict,
    context: dict,
) -> EvaluationRun:
    """Execute evaluation and persist the result.

    Args:
        db: Database session.
        conversation: Conversation data for the evaluator.
        context: Context data for the evaluator.

    Returns:
        The persisted EvaluationRun record.
    """
    pipeline = EvaluationPipeline()
    result = pipeline.evaluate(conversation, context)

    run = EvaluationRun(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        status="completed",
        conversation=conversation,
        context=context,
        relevance=result.get("relevance"),
        hallucination=result.get("hallucination"),
        latency_ms=result.get("latency_ms"),
        estimated_cost=result.get("estimated_cost"),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run(db: Session, run_id: uuid.UUID) -> EvaluationRun | None:
    """Retrieve an evaluation run by ID."""
    return db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()


def list_runs(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> list[EvaluationRun]:
    """List evaluation runs with pagination."""
    return db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).offset(offset).limit(limit).all()


def count_runs(db: Session) -> int:
    """Count total evaluation runs."""
    return db.query(EvaluationRun).count()
