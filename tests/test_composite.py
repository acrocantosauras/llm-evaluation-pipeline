"""Tests for composite scoring."""

from evaluator.base import MetricResult
from evaluator.composite import compute_composite, validate_weights


def test_composite_basic():
    """Basic composite score calculation."""
    results = [
        MetricResult(metric="relevance", score=0.9, evaluator_version="1.0.0"),
        MetricResult(metric="faithfulness", score=0.8, evaluator_version="1.0.0"),
    ]
    weights = {"relevance": 0.5, "faithfulness": 0.5}

    composite = compute_composite(results, weights)
    assert composite["composite_score"] == 0.85
    assert len(composite["contributions"]) == 2


def test_composite_normalized_weights():
    """Weights not summing to 1.0 are normalized."""
    results = [
        MetricResult(metric="relevance", score=1.0, evaluator_version="1.0.0"),
    ]
    weights = {"relevance": 2.0}  # Not normalized

    composite = compute_composite(results, weights)
    assert composite["composite_score"] == 1.0


def test_composite_missing_metric():
    """Missing metric is handled gracefully."""
    results = [
        MetricResult(metric="relevance", score=0.9, evaluator_version="1.0.0"),
    ]
    weights = {"relevance": 0.5, "faithfulness": 0.5}

    composite = compute_composite(results, weights)
    assert "faithfulness" in composite["missing_metrics"]
    assert composite["composite_score"] > 0  # Still computes with available metrics


def test_composite_error_metric():
    """Metric with error is treated as missing."""
    results = [
        MetricResult(metric="relevance", score=0.9, evaluator_version="1.0.0"),
        MetricResult(metric="faithfulness", score=0.0, evaluator_version="1.0.0", error="model failed"),
    ]
    weights = {"relevance": 0.5, "faithfulness": 0.5}

    composite = compute_composite(results, weights)
    assert "faithfulness" in composite["missing_metrics"]


def test_composite_no_weights():
    """No weights → error."""
    composite = compute_composite([], {})
    assert composite["error"] == "no_weights"


def test_validate_weights_valid():
    """Valid weights produce no warnings."""
    warnings = validate_weights({"relevance": 0.5, "faithfulness": 0.5})
    assert warnings == []


def test_validate_weights_negative():
    """Negative weights produce warning."""
    warnings = validate_weights({"relevance": -0.5, "faithfulness": 1.5})
    assert len(warnings) > 0
    assert any("Negative" in w for w in warnings)


def test_validate_weights_not_summing():
    """Weights not summing to 1.0 produce warning."""
    warnings = validate_weights({"relevance": 0.3, "faithfulness": 0.3})
    assert len(warnings) > 0
    assert any("sum to" in w for w in warnings)
