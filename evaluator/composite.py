"""Composite scoring — configurable weighted combination of metrics.

Composite scoring is a configurable product-level decision.
A weighted average is not scientifically "correct" — it reflects
organizational priorities, not objective truth.
"""

from .base import MetricResult


def compute_composite(
    results: list[MetricResult],
    weights: dict[str, float],
) -> dict:
    """Compute a composite score from individual metric results.

    Args:
        results: List of MetricResult from evaluators.
        weights: Dict mapping metric names to weights. Weights should sum to 1.0.

    Returns:
        Dict with composite_score, per-metric contributions, and metadata.
    """
    if not weights:
        return {"composite_score": 0.0, "contributions": {}, "error": "no_weights"}

    # Normalize weights to sum to 1.0
    total_weight = sum(weights.values())
    if total_weight == 0:
        return {"composite_score": 0.0, "contributions": {}, "error": "zero_total_weight"}

    normalized_weights = {k: v / total_weight for k, v in weights.items()}

    # Map results by metric name
    result_map = {r.metric: r for r in results}

    contributions = {}
    weighted_sum = 0.0
    total_weight_used = 0.0
    missing_metrics = []

    for metric, weight in normalized_weights.items():
        if metric in result_map:
            r = result_map[metric]
            if r.error:
                missing_metrics.append(metric)
                continue
            contribution = r.score * weight
            contributions[metric] = {
                "score": r.score,
                "weight": round(weight, 4),
                "contribution": round(contribution, 4),
                "evaluator_version": r.evaluator_version,
            }
            weighted_sum += contribution
            total_weight_used += weight
        else:
            missing_metrics.append(metric)

    # If we have missing metrics, redistribute weight proportionally
    if missing_metrics and total_weight_used > 0:
        redistribution_factor = 1.0 / (1.0 - total_weight_used) if total_weight_used < 1.0 else 1.0
        weighted_sum *= redistribution_factor

    composite_score = round(min(weighted_sum, 1.0), 4)

    return {
        "composite_score": composite_score,
        "contributions": contributions,
        "missing_metrics": missing_metrics,
        "weights_used": {k: round(v, 4) for k, v in normalized_weights.items()},
    }


def validate_weights(weights: dict[str, float]) -> list[str]:
    """Validate weight configuration. Returns list of warnings."""
    warnings = []
    if not weights:
        warnings.append("No weights provided")
        return warnings

    negative = [k for k, v in weights.items() if v < 0]
    if negative:
        warnings.append(f"Negative weights: {negative}")

    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        warnings.append(f"Weights sum to {total}, not 1.0 (will be normalized)")

    return warnings
