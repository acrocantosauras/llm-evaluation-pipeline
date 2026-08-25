import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.enums import GateOutcome
from app.db.models import QualityGate

# Default thresholds for a standard quality gate
DEFAULT_THRESHOLDS = {
    "relevance": {"min": 0.80},
    "hallucination_fraction_unsupported": {"max": 0.10},
    "latency_ms": {"max": 2000},
    "estimated_cost": {"max": 0.01},
}

# Direction map: which metrics are higher_is_better vs lower_is_better
METRIC_DIRECTION = {
    "relevance": "higher_is_better",
    "faithfulness": "higher_is_better",
    "context_precision": "higher_is_better",
    "context_recall": "higher_is_better",
    "answer_relevancy": "higher_is_better",
    "citation_correctness": "higher_is_better",
    "hallucination_fraction_unsupported": "lower_is_better",
    "latency_ms": "lower_is_better",
    "estimated_cost": "lower_is_better",
    "composite_score": "higher_is_better",
    "llm_judge": "higher_is_better",
}


def create_quality_gate(
    db: Session,
    name: str,
    thresholds: dict | None = None,
    project_id: uuid.UUID | None = None,
) -> QualityGate:
    """Create a new quality gate configuration."""
    gate = QualityGate(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        project_id=project_id,
        name=name,
        thresholds=thresholds or DEFAULT_THRESHOLDS,
        enabled=True,
    )
    db.add(gate)
    db.commit()
    db.refresh(gate)
    return gate


def get_quality_gate(db: Session, gate_id: uuid.UUID, project_id: uuid.UUID | None = None) -> QualityGate | None:
    """Get a quality gate by ID, optionally scoped to a project."""
    query = db.query(QualityGate).filter(QualityGate.id == gate_id)
    if project_id is not None:
        query = query.filter(QualityGate.project_id == project_id)
    return query.first()


def get_quality_gate_by_name(db: Session, name: str, project_id: uuid.UUID | None = None) -> QualityGate | None:
    """Get a quality gate by name, optionally scoped to a project."""
    query = db.query(QualityGate).filter(QualityGate.name == name)
    if project_id is not None:
        query = query.filter(QualityGate.project_id == project_id)
    return query.first()


def list_quality_gates(db: Session, project_id: uuid.UUID | None = None) -> list[QualityGate]:
    """List all quality gates, optionally scoped to a project."""
    query = db.query(QualityGate).filter(QualityGate.enabled.is_(True))
    if project_id is not None:
        query = query.filter(QualityGate.project_id == project_id)
    return query.all()


def evaluate_gate(thresholds: dict, results: dict) -> dict:
    """Evaluate evaluation results against quality gate thresholds.

    Now supports both legacy metrics and new advanced metrics.
    Uses METRIC_DIRECTION to determine threshold logic.
    """
    checks = {}

    for metric_name, threshold_config in thresholds.items():
        if metric_name not in METRIC_DIRECTION:
            continue

        direction = METRIC_DIRECTION[metric_name]
        value = _extract_metric_value(metric_name, results)
        if value is None:
            continue

        if direction == "higher_is_better":
            min_val = threshold_config.get("min", 0)
            checks[metric_name] = {
                "value": value,
                "threshold": min_val,
                "passed": value >= min_val,
                "direction": direction,
            }
        else:
            max_val = threshold_config.get("max", float("inf"))
            checks[metric_name] = {
                "value": value,
                "threshold": max_val,
                "passed": value <= max_val,
                "direction": direction,
            }

    all_passed = all(c["passed"] for c in checks.values()) if checks else True

    return {
        "status": GateOutcome.PASS if all_passed else GateOutcome.FAIL,
        "checks": checks,
    }


def _extract_metric_value(metric_name: str, results: dict) -> float | None:
    """Extract a metric value from results dict, handling various formats."""
    # Direct value
    if metric_name in results and results[metric_name] is not None:
        return float(results[metric_name])

    # Hallucination fraction
    if metric_name == "hallucination_fraction_unsupported" and results.get("hallucination"):
        return 1.0 - results["hallucination"].get("fraction_supported", 1.0)

    # Metric results array (from advanced evaluators)
    if "metric_results" in results:
        for mr in results["metric_results"]:
            if mr.get("metric") == metric_name and mr.get("error") is None:
                return float(mr["score"])

    return None
