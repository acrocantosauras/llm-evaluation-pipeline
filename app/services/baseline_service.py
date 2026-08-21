import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import EvaluationBaseline, EvaluationRun, MetricResultRecord
from app.services.quality_gate_service import METRIC_DIRECTION

# Default tolerances for regression detection
DEFAULT_TOLERANCES = {
    "relevance": 0.05,
    "hallucination_fraction_unsupported": 0.05,
    "latency_ms": 0.20,
    "estimated_cost": 0.20,
    "faithfulness": 0.05,
    "context_precision": 0.05,
    "context_recall": 0.05,
    "answer_relevancy": 0.05,
    "citation_correctness": 0.05,
    "composite_score": 0.05,
    "llm_judge": 0.05,
}


def create_baseline(
    db: Session,
    run_id: uuid.UUID,
    name: str,
    description: str = "",
) -> EvaluationBaseline:
    """Mark an evaluation run as a baseline."""
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise ValueError(f"Run {run_id} not found")

    baseline = EvaluationBaseline(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        name=name,
        description=description,
        run_id=run_id,
    )
    run.is_baseline = True
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


def get_baseline(db: Session, baseline_id: uuid.UUID) -> EvaluationBaseline | None:
    """Get a baseline by ID."""
    return db.query(EvaluationBaseline).filter(EvaluationBaseline.id == baseline_id).first()


def get_baseline_by_name(db: Session, name: str) -> EvaluationBaseline | None:
    """Get a baseline by name."""
    return db.query(EvaluationBaseline).filter(EvaluationBaseline.name == name).first()


def list_baselines(db: Session) -> list[EvaluationBaseline]:
    """List all baselines."""
    return db.query(EvaluationBaseline).order_by(EvaluationBaseline.created_at.desc()).all()


def detect_regressions(
    baseline_run: EvaluationRun,
    current_run: EvaluationRun,
    tolerances: dict | None = None,
    baseline_metrics: list[MetricResultRecord] | None = None,
    current_metrics: list[MetricResultRecord] | None = None,
) -> dict:
    """Compare two evaluation runs and detect regressions.

    Now supports both legacy metrics and new advanced metrics from metric_results.
    """
    if tolerances is None:
        tolerances = DEFAULT_TOLERANCES

    regressions = []
    improvements = []

    # Legacy metric comparisons
    legacy_comparisons = _get_legacy_comparisons(baseline_run, current_run)
    for metric, (baseline_val, current_val) in legacy_comparisons.items():
        if baseline_val is None or current_val is None:
            continue
        direction = METRIC_DIRECTION.get(metric, "higher_is_better")
        tolerance = tolerances.get(metric, 0.05)
        change = current_val - baseline_val
        is_regression = change < -tolerance if direction == "higher_is_better" else change > tolerance

        entry = {
            "metric": metric,
            "baseline": baseline_val,
            "current": current_val,
            "change": round(change, 6),
            "threshold": tolerance,
            "direction": direction,
            "source": "legacy",
        }
        if is_regression:
            regressions.append(entry)
        elif change != 0:
            improvements.append(entry)

    # Advanced metric comparisons from metric_results table
    if baseline_metrics is not None and current_metrics is not None:
        baseline_map = {m.metric: m for m in baseline_metrics}
        current_map = {m.metric: m for m in current_metrics}

        all_metrics = set(baseline_map.keys()) | set(current_map.keys())
        for metric in all_metrics:
            if metric in ("latency", "cost"):  # Skip legacy wrappers
                continue
            b = baseline_map.get(metric)
            c = current_map.get(metric)
            if not b or not c or b.error or c.error:
                continue

            direction = METRIC_DIRECTION.get(metric, "higher_is_better")
            tolerance = tolerances.get(metric, 0.05)
            change = c.score - b.score
            is_regression = change < -tolerance if direction == "higher_is_better" else change > tolerance

            entry = {
                "metric": metric,
                "baseline": b.score,
                "current": c.score,
                "change": round(change, 6),
                "threshold": tolerance,
                "direction": direction,
                "baseline_version": b.evaluator_version,
                "current_version": c.evaluator_version,
                "source": "metric_results",
            }
            if is_regression:
                regressions.append(entry)
            elif change != 0:
                improvements.append(entry)

    overall = "no_regression"
    if regressions:
        overall = "regression_detected"

    return {
        "overall": overall,
        "baseline_id": str(baseline_run.id) if baseline_run else None,
        "regressions": regressions,
        "improvements": improvements,
    }


def _get_legacy_comparisons(
    baseline_run: EvaluationRun,
    current_run: EvaluationRun,
) -> dict[str, tuple[float | None, float | None]]:
    """Extract legacy metric comparisons."""
    baseline_fraction_unsupported = 0.0
    if baseline_run.hallucination:
        baseline_fraction_unsupported = 1.0 - baseline_run.hallucination.get("fraction_supported", 1.0)

    current_fraction_unsupported = 0.0
    if current_run.hallucination:
        current_fraction_unsupported = 1.0 - current_run.hallucination.get("fraction_supported", 1.0)

    return {
        "relevance": (baseline_run.relevance, current_run.relevance),
        "hallucination_fraction_unsupported": (baseline_fraction_unsupported, current_fraction_unsupported),
        "latency_ms": (baseline_run.latency_ms, current_run.latency_ms),
        "estimated_cost": (baseline_run.estimated_cost, current_run.estimated_cost),
    }
