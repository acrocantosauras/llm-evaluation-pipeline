import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import EvaluationBaseline, EvaluationRun


def create_baseline(
    db: Session,
    run_id: uuid.UUID,
    name: str,
    description: str = "",
) -> EvaluationBaseline:
    """Mark an evaluation run as a baseline."""
    # Verify run exists
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
) -> dict:
    """Compare two evaluation runs and detect regressions.

    Args:
        baseline_run: The baseline evaluation run.
        current_run: The current evaluation run to compare.
        tolerances: Per-metric tolerance thresholds for regression detection.
                    Format: {"metric_name": tolerance_value}

    Returns:
        Dict with regression results and overall comparison.
    """
    if tolerances is None:
        tolerances = {
            "relevance": 0.05,  # 5% absolute drop is a regression
            "hallucination_fraction_unsupported": 0.05,
            "latency_ms": 0.20,  # 20% increase is a regression
            "estimated_cost": 0.20,
        }

    # Define metric direction: higher_is_better or lower_is_better
    metric_direction = {
        "relevance": "higher_is_better",
        "hallucination_fraction_unsupported": "lower_is_better",
        "latency_ms": "lower_is_better",
        "estimated_cost": "lower_is_better",
    }

    regressions = []
    improvements = []

    # Extract baseline values
    baseline_fraction_unsupported = 0.0
    if baseline_run.hallucination:
        baseline_fraction_unsupported = 1.0 - baseline_run.hallucination.get("fraction_supported", 1.0)

    current_fraction_unsupported = 0.0
    if current_run.hallucination:
        current_fraction_unsupported = 1.0 - current_run.hallucination.get("fraction_supported", 1.0)

    comparisons = {
        "relevance": (baseline_run.relevance, current_run.relevance),
        "hallucination_fraction_unsupported": (baseline_fraction_unsupported, current_fraction_unsupported),
        "latency_ms": (baseline_run.latency_ms, current_run.latency_ms),
        "estimated_cost": (baseline_run.estimated_cost, current_run.estimated_cost),
    }

    for metric, (baseline_val, current_val) in comparisons.items():
        if baseline_val is None or current_val is None:
            continue

        direction = metric_direction.get(metric, "higher_is_better")
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
