"""Pipeline unit tests.

These tests mock the heavy ML model imports so they can run without
downloading or loading SentenceTransformer / RoBERTa models.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest


def _import_pipeline_with_mocks():
    """Import EvaluationPipeline after mocking the heavy ML modules.

    This prevents loading SentenceTransformer and RoBERTa at import time,
    which is expensive and can crash on resource-constrained machines.
    """
    # Create mock modules for the heavy ML dependencies
    mock_relevance = types.ModuleType("evaluator.relevance")
    mock_relevance.relevance_score = MagicMock(return_value=0.85)
    mock_relevance.model = MagicMock()
    mock_relevance.util = MagicMock()

    mock_hallucination = types.ModuleType("evaluator.hallucination")
    mock_hallucination.hallucination_report = MagicMock(
        return_value={"fraction_supported": 1.0, "flags": [], "details": []}
    )
    mock_hallucination.nli = MagicMock()

    mock_latency = types.ModuleType("evaluator.latency")
    mock_latency.measure_latency = MagicMock(return_value=42.5)

    mock_cost = types.ModuleType("evaluator.cost")
    mock_cost.estimate_cost = MagicMock(return_value=0.001)

    # Temporarily inject mocks into sys.modules
    to_restore = {}
    for mod_name, mock_mod in [
        ("evaluator.relevance", mock_relevance),
        ("evaluator.hallucination", mock_hallucination),
        ("evaluator.latency", mock_latency),
        ("evaluator.cost", mock_cost),
    ]:
        to_restore[mod_name] = sys.modules.get(mod_name)
        sys.modules[mod_name] = mock_mod

    # Force reimport of pipeline so it picks up our mocks
    if "evaluator.pipeline" in sys.modules:
        del sys.modules["evaluator.pipeline"]

    from evaluator.pipeline import EvaluationPipeline

    # Restore original modules
    for mod_name, original in to_restore.items():
        if original is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = original

    return EvaluationPipeline, mock_relevance, mock_hallucination, mock_latency, mock_cost


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def pipeline_with_mocks():
    """Provide an EvaluationPipeline with all evaluator functions mocked."""
    EvalPipeline, mock_rel, mock_hall, mock_lat, mock_cost = _import_pipeline_with_mocks()
    pipeline = EvalPipeline()
    return pipeline, mock_rel, mock_hall, mock_lat, mock_cost


def test_pipeline_returns_all_keys(pipeline_with_mocks):
    """Pipeline should return all four evaluation keys."""
    pipeline, mock_rel, mock_hall, mock_lat, mock_cost = pipeline_with_mocks
    convo = {"model_response": "Test response.", "input_tokens": 10, "output_tokens": 5}
    ctx = {"chunks": [{"text": "Context."}]}
    result = pipeline.evaluate(convo, ctx)

    assert "relevance" in result
    assert "hallucination" in result
    assert "latency_ms" in result
    assert "estimated_cost" in result


def test_pipeline_uses_provided_latency(pipeline_with_mocks):
    """When conversation has latency_ms, it should use that value."""
    pipeline, mock_rel, mock_hall, mock_lat, mock_cost = pipeline_with_mocks
    convo = {"model_response": "Test.", "latency_ms": 99.9, "input_tokens": 10, "output_tokens": 5}
    ctx = {"chunks": [{"text": "Context."}]}
    result = pipeline.evaluate(convo, ctx)

    assert result["latency_ms"] == 99.9
    mock_lat.measure_latency.assert_not_called()


def test_pipeline_falls_back_to_measured_latency(pipeline_with_mocks):
    """When conversation has no latency_ms, it should measure it."""
    pipeline, mock_rel, mock_hall, mock_lat, mock_cost = pipeline_with_mocks
    convo = {"model_response": "Test.", "input_tokens": 10, "output_tokens": 5}
    ctx = {"chunks": [{"text": "Context."}]}
    result = pipeline.evaluate(convo, ctx)

    assert result["latency_ms"] == 42.5
    mock_lat.measure_latency.assert_called_once()


def test_pipeline_passes_correct_args(pipeline_with_mocks):
    """Pipeline should pass response text and context to evaluators."""
    pipeline, mock_rel, mock_hall, mock_lat, mock_cost = pipeline_with_mocks
    convo = {"model_response": "My response", "input_tokens": 10, "output_tokens": 5}
    ctx = {"chunks": [{"text": "My context"}]}
    pipeline.evaluate(convo, ctx)

    mock_rel.relevance_score.assert_called_once_with("My response", ctx)
    mock_hall.hallucination_report.assert_called_once_with("My response", ctx)


def test_pipeline_empty_response(pipeline_with_mocks):
    """Pipeline should handle empty model_response gracefully."""
    pipeline, mock_rel, mock_hall, mock_lat, mock_cost = pipeline_with_mocks
    convo = {"model_response": "", "input_tokens": 10, "output_tokens": 5}
    ctx = {"chunks": [{"text": "Context."}]}
    result = pipeline.evaluate(convo, ctx)

    assert "relevance" in result
    mock_rel.relevance_score.assert_called_once_with("", ctx)


def test_pipeline_estimated_cost(pipeline_with_mocks):
    """Pipeline should pass conversation to cost estimator."""
    pipeline, mock_rel, mock_hall, mock_lat, mock_cost = pipeline_with_mocks
    convo = {"model_response": "Hi", "input_tokens": 100, "output_tokens": 50}
    ctx = {"chunks": [{"text": "Ctx"}]}
    result = pipeline.evaluate(convo, ctx)

    assert result["estimated_cost"] == 0.001
    mock_cost.estimate_cost.assert_called_once_with(convo)
