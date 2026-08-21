"""Tests for evaluator registry."""

from evaluator.base import EvaluationSample
from evaluator.registry import _get_evaluator, run_evaluators


def test_get_evaluator_relevance():
    """Registry returns relevance evaluator."""
    evaluator = _get_evaluator("relevance")
    assert evaluator is not None
    assert evaluator.name == "relevance"


def test_get_evaluator_faithfulness():
    """Registry returns faithfulness evaluator."""
    evaluator = _get_evaluator("faithfulness")
    assert evaluator is not None
    assert evaluator.name == "faithfulness"


def test_get_evaluator_unknown():
    """Unknown evaluator returns None."""
    evaluator = _get_evaluator("nonexistent_metric")
    assert evaluator is None


def test_run_evaluators_unknown_metric():
    """Running unknown evaluator returns error result."""
    sample = EvaluationSample(answer="test", context=[{"text": "ctx"}])
    results = run_evaluators(["nonexistent"], sample)
    assert len(results) == 1
    assert results[0].error is not None
    assert "not found" in results[0].error
