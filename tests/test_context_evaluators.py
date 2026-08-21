"""Tests for context precision and context recall evaluators."""

from unittest.mock import MagicMock, patch

from evaluator.base import EvaluationSample

# ── Context Precision ─────────────────────────────────────────────────────────


def _mock_precision_evaluator():
    from evaluator.context_precision import ContextPrecisionEvaluator

    evaluator = ContextPrecisionEvaluator()
    mock_model = MagicMock()
    evaluator._model = mock_model
    return evaluator, mock_model


def test_context_precision_all_relevant():
    """All chunks relevant → score 1.0."""
    evaluator, mock_model = _mock_precision_evaluator()
    mock_model.encode.return_value = MagicMock()

    mock_util = MagicMock()
    # All chunks score 0.8 (above threshold of 0.3)
    mock_util.cos_sim.return_value.item.return_value = 0.8

    with patch("evaluator.context_precision.util", mock_util):
        sample = EvaluationSample(
            question="What is ibuprofen?",
            context=[
                {"text": "Ibuprofen is a pain reliever."},
                {"text": "Ibuprofen reduces inflammation."},
                {"text": "Ibuprofen treats fever."},
            ],
        )
        result = evaluator.evaluate(sample)
        assert result.score == 1.0
        assert result.details["chunks_relevant"] == 3


def test_context_precision_mixed():
    """Some chunks relevant, some not → partial score."""
    evaluator, mock_model = _mock_precision_evaluator()
    mock_model.encode.return_value = MagicMock()

    # Create proper mock tensors
    def make_tensor(val):
        m = MagicMock()
        m.item.return_value = val
        return m

    mock_util = MagicMock()
    # Raw cosine sim values: normalized = (score + 1) / 2
    # Threshold is 0.3, so raw sim < -0.4 → normalized < 0.3 → not relevant
    mock_util.cos_sim.side_effect = [
        make_tensor(0.8),  # raw=0.8 → norm=0.9 → relevant
        make_tensor(0.7),  # raw=0.7 → norm=0.85 → relevant
        make_tensor(-0.8),  # raw=-0.8 → norm=0.1 → irrelevant
    ]

    with patch("evaluator.context_precision.util", mock_util):
        sample = EvaluationSample(
            question="What is ibuprofen?",
            context=[
                {"text": "Ibuprofen is a pain reliever."},
                {"text": "Ibuprofen reduces inflammation."},
                {"text": "The sky is blue."},
            ],
        )
        result = evaluator.evaluate(sample)
        assert result.details["chunks_relevant"] == 2
        assert result.score == round(2 / 3, 4)


def test_context_precision_empty():
    """Empty context → score 0.0."""
    evaluator, _ = _mock_precision_evaluator()
    sample = EvaluationSample(question="What?", context=[])
    result = evaluator.evaluate(sample)
    assert result.score == 0.0


# ── Context Recall ────────────────────────────────────────────────────────────


def _mock_recall_evaluator():
    from evaluator.context_recall import ContextRecallEvaluator

    evaluator = ContextRecallEvaluator()
    mock_nli = MagicMock()
    evaluator._nli = mock_nli
    return evaluator, mock_nli


def test_context_recall_complete():
    """All answer claims found in context → score 1.0."""
    evaluator, mock_nli = _mock_recall_evaluator()
    mock_nli.return_value = [{"label": "ENTAILMENT", "score": 0.95}]

    sample = EvaluationSample(
        answer="Ibuprofen treats pain and reduces inflammation.",
        context=[{"text": "Ibuprofen treats pain. Ibuprofen reduces inflammation."}],
    )
    result = evaluator.evaluate(sample)
    assert result.score == 1.0
    assert result.passed is True


def test_context_recall_partial():
    """Only some claims found → partial score."""
    evaluator, mock_nli = _mock_recall_evaluator()
    mock_nli.side_effect = [
        [{"label": "ENTAILMENT", "score": 0.9}],
        [{"label": "NEUTRAL", "score": 0.7}],
    ]

    sample = EvaluationSample(
        answer="Ibuprofen treats pain. Aspirin cures cancer.",
        context=[{"text": "Ibuprofen treats pain."}],
    )
    result = evaluator.evaluate(sample)
    assert result.score == 0.5


def test_context_recall_with_reference():
    """Uses reference_answer when available."""
    evaluator, mock_nli = _mock_recall_evaluator()
    mock_nli.return_value = [{"label": "ENTAILMENT", "score": 0.9}]

    sample = EvaluationSample(
        answer="Some answer",
        reference_answer="Ground truth answer about ibuprofen.",
        context=[{"text": "Ibuprofen information."}],
    )
    result = evaluator.evaluate(sample)
    assert result.details["has_reference"] is True


def test_context_recall_empty():
    """Empty context → score 0.0."""
    evaluator, _ = _mock_recall_evaluator()
    sample = EvaluationSample(answer="Answer.", context=[])
    result = evaluator.evaluate(sample)
    assert result.score == 0.0
