"""Tests for faithfulness evaluator."""

from unittest.mock import MagicMock

from evaluator.base import EvaluationSample


def _mock_faithfulness_evaluator():
    """Create a faithfulness evaluator with mocked NLI."""
    from evaluator.faithfulness import FaithfulnessEvaluator

    evaluator = FaithfulnessEvaluator()
    mock_nli = MagicMock()
    evaluator._nli = mock_nli
    return evaluator, mock_nli


def test_faithfulness_fully_supported():
    """All claims supported → score 1.0."""
    evaluator, mock_nli = _mock_faithfulness_evaluator()
    mock_nli.return_value = [{"label": "ENTAILMENT", "score": 0.95}]

    sample = EvaluationSample(
        answer="Ibuprofen causes stomach upset. It also causes drowsiness.",
        context=[{"text": "Ibuprofen causes stomach upset and drowsiness."}],
    )
    result = evaluator.evaluate(sample)
    assert result.score == 1.0
    assert result.passed is True
    assert len(result.details["claims"]) == 2
    assert all(c["supported"] for c in result.details["claims"])


def test_faithfulness_partially_supported():
    """Some claims supported → partial score."""
    evaluator, mock_nli = _mock_faithfulness_evaluator()
    mock_nli.side_effect = [
        [{"label": "ENTAILMENT", "score": 0.95}],
        [{"label": "CONTRADICTION", "score": 0.90}],
    ]

    sample = EvaluationSample(
        answer="Ibuprofen causes stomach upset. Aspirin cures cancer.",
        context=[{"text": "Ibuprofen causes stomach upset."}],
    )
    result = evaluator.evaluate(sample)
    assert result.score == 0.5
    assert result.details["supported"] == 1
    assert result.details["total"] == 2


def test_faithfulness_unsupported():
    """No claims supported → score 0.0."""
    evaluator, mock_nli = _mock_faithfulness_evaluator()
    mock_nli.return_value = [{"label": "CONTRADICTION", "score": 0.90}]

    sample = EvaluationSample(
        answer="The earth is flat.",
        context=[{"text": "The earth is approximately spherical."}],
    )
    result = evaluator.evaluate(sample)
    assert result.score == 0.0
    assert result.passed is False


def test_faithfulness_empty_answer():
    """Empty answer → score 0.0."""
    evaluator, _ = _mock_faithfulness_evaluator()
    sample = EvaluationSample(answer="", context=[{"text": "Some context."}])
    result = evaluator.evaluate(sample)
    assert result.score == 0.0


def test_faithfulness_empty_context():
    """Empty context → score 0.0."""
    evaluator, _ = _mock_faithfulness_evaluator()
    sample = EvaluationSample(answer="Some answer.", context=[])
    result = evaluator.evaluate(sample)
    assert result.score == 0.0


def test_faithfulness_multiple_claims():
    """Multiple claims are evaluated individually."""
    evaluator, mock_nli = _mock_faithfulness_evaluator()
    mock_nli.side_effect = [
        [{"label": "ENTAILMENT", "score": 0.9}],
        [{"label": "NEUTRAL", "score": 0.7}],
        [{"label": "ENTAILMENT", "score": 0.95}],
    ]

    sample = EvaluationSample(
        answer="Drug X reduces fever. Drug Y cures baldness. Drug Z treats nausea.",
        context=[{"text": "Drug X reduces fever. Drug Z treats nausea."}],
    )
    result = evaluator.evaluate(sample)
    assert result.score == round(2 / 3, 4)
    assert result.details["supported"] == 2
    assert result.details["total"] == 3


def test_faithfulness_version():
    """Evaluator version is set correctly."""
    evaluator, _ = _mock_faithfulness_evaluator()
    assert evaluator.version == "1.0.0"
    assert evaluator.name == "faithfulness"
