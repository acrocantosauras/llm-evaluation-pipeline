import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import EvaluationRun, MetricResultRecord
from evaluator.base import EvaluationSample
from evaluator.pipeline import EvaluationPipeline


def run_evaluation(
    db: Session,
    conversation: dict,
    context: dict,
    profile: str = "basic",
    judge_config: dict | None = None,
) -> EvaluationRun:
    """Execute evaluation and persist the result.

    Args:
        db: Database session.
        conversation: Conversation data for the evaluator.
        context: Context data for the evaluator.
        profile: Evaluation profile name (basic, rag, rag_strict, judge).
        judge_config: Optional judge configuration override.

    Returns:
        The persisted EvaluationRun record.
    """
    # Always run the legacy pipeline for backward compatibility
    pipeline = EvaluationPipeline()
    legacy_result = pipeline.evaluate(conversation, context)

    # Run advanced evaluators if profile is not "basic"
    metric_results = []
    composite_score = None

    if profile and profile != "basic":
        from evaluator.profiles import get_profile
        from evaluator.registry import evaluate_with_profile

        sample = _build_sample(conversation, context)
        metric_results = evaluate_with_profile(profile, sample, judge_config=judge_config)

        # Compute composite score if profile has weights
        profile_config = get_profile(profile)
        if profile_config and profile_config.composite_weights:
            from evaluator.composite import compute_composite

            composite_result = compute_composite(metric_results, profile_config.composite_weights)
            composite_score = composite_result.get("composite_score")

    # Create the run
    run = EvaluationRun(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        status="completed",
        profile=profile,
        composite_score=composite_score,
        conversation=conversation,
        context=context,
        relevance=legacy_result.get("relevance"),
        hallucination=legacy_result.get("hallucination"),
        latency_ms=legacy_result.get("latency_ms"),
        estimated_cost=legacy_result.get("estimated_cost"),
    )
    db.add(run)
    db.flush()  # Get the ID before adding metric results

    # Persist metric results
    for mr in metric_results:
        record = MetricResultRecord(
            id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            run_id=run.id,
            metric=mr.metric,
            score=mr.score,
            passed=mr.passed,
            evaluator_version=mr.evaluator_version,
            details=mr.details,
            error=mr.error,
        )
        db.add(record)

    db.commit()
    db.refresh(run)
    return run


def get_metric_results(db: Session, run_id: uuid.UUID) -> list[MetricResultRecord]:
    """Get all metric results for a run."""
    return db.query(MetricResultRecord).filter(MetricResultRecord.run_id == run_id).all()


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


def _build_sample(conversation: dict, context: list[dict] | dict) -> EvaluationSample:
    """Build an EvaluationSample from API input."""
    ctx_list = context.get("chunks", []) if isinstance(context, dict) else context

    return EvaluationSample(
        question=conversation.get("question", ""),
        answer=conversation.get("model_response", ""),
        context=[{"text": c.get("text", ""), "id": c.get("id", "")} for c in ctx_list],
        conversation=conversation,
        citations=conversation.get("citations", []),
        reference_answer=conversation.get("reference_answer", ""),
    )
