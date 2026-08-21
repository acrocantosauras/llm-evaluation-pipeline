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


def create_quality_gate(
    db: Session,
    name: str,
    thresholds: dict | None = None,
) -> QualityGate:
    """Create a new quality gate configuration."""
    gate = QualityGate(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        name=name,
        thresholds=thresholds or DEFAULT_THRESHOLDS,
        enabled=True,
    )
    db.add(gate)
    db.commit()
    db.refresh(gate)
    return gate


def get_quality_gate(db: Session, gate_id: uuid.UUID) -> QualityGate | None:
    """Get a quality gate by ID."""
    return db.query(QualityGate).filter(QualityGate.id == gate_id).first()


def get_quality_gate_by_name(db: Session, name: str) -> QualityGate | None:
    """Get a quality gate by name."""
    return db.query(QualityGate).filter(QualityGate.name == name).first()


def list_quality_gates(db: Session) -> list[QualityGate]:
    """List all quality gates."""
    return db.query(QualityGate).filter(QualityGate.enabled.is_(True)).all()


def evaluate_gate(thresholds: dict, results: dict) -> dict:
    """Evaluate evaluation results against quality gate thresholds.

    Args:
        thresholds: Gate threshold configuration.
        results: Evaluation results dict with metric values.

    Returns:
        Dict with overall status and individual check results.
    """
    checks = {}

    # Relevance: higher is better → check minimum
    if "relevance" in thresholds and results.get("relevance") is not None:
        min_val = thresholds["relevance"].get("min", 0)
        value = results["relevance"]
        checks["relevance"] = {
            "value": value,
            "threshold": min_val,
            "passed": value >= min_val,
            "direction": "higher_is_better",
        }

    # Hallucination unsupported fraction: lower is better → check maximum
    if "hallucination_fraction_unsupported" in thresholds and results.get("hallucination"):
        max_val = thresholds["hallucination_fraction_unsupported"].get("max", 1.0)
        fraction = 1.0 - results["hallucination"].get("fraction_supported", 1.0)
        checks["hallucination_fraction_unsupported"] = {
            "value": round(fraction, 4),
            "threshold": max_val,
            "passed": fraction <= max_val,
            "direction": "lower_is_better",
        }

    # Latency: lower is better → check maximum
    if "latency_ms" in thresholds and results.get("latency_ms") is not None:
        max_val = thresholds["latency_ms"].get("max", float("inf"))
        value = results["latency_ms"]
        checks["latency_ms"] = {
            "value": value,
            "threshold": max_val,
            "passed": value <= max_val,
            "direction": "lower_is_better",
        }

    # Cost: lower is better → check maximum
    if "estimated_cost" in thresholds and results.get("estimated_cost") is not None:
        max_val = thresholds["estimated_cost"].get("max", float("inf"))
        value = results["estimated_cost"]
        checks["estimated_cost"] = {
            "value": value,
            "threshold": max_val,
            "passed": value <= max_val,
            "direction": "lower_is_better",
        }

    all_passed = all(c["passed"] for c in checks.values()) if checks else True

    return {
        "status": GateOutcome.PASS if all_passed else GateOutcome.FAIL,
        "checks": checks,
    }
