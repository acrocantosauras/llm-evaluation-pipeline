"""Tests for answer relevancy evaluator."""

from unittest.mock import MagicMock, patch

from evaluator.base import EvaluationSample


def _mock_relevancy_evaluator():
    from evaluator.answer_relevancy import AnswerRelevancyEvaluator

    evaluator = AnswerRelevancyEvaluator()
    mock_model = MagicMock()
    evaluator._model = mock_model
    return evaluator, mock_model


def test_answer_relevancy_relevant():
    """Relevant answer → high score."""
    evaluator, mock_model = _mock_relevancy_evaluator()
    mock_model.encode.return_value = MagicMock()

    mock_util = MagicMock()
    mock_util.cos_sim.return_value.item.return_value = 0.7  # High similarity

    with patch("evaluator.answer_relevancy.util", mock_util):
        sample = EvaluationSample(
            question="What are the side effects of ibuprofen?",
            answer="Ibuprofen can cause stomach pain, nausea, and dizziness.",
        )
        result = evaluator.evaluate(sample)
        assert result.score > 0.5
        assert result.passed is True


def test_answer_relevancy_irrelevant():
    """Irrelevant answer → low score."""
    evaluator, mock_model = _mock_relevancy_evaluator()
    mock_model.encode.return_value = MagicMock()

    mock_util = MagicMock()
    mock_util.cos_sim.return_value.item.return_value = -0.3  # Low similarity

    with patch("evaluator.answer_relevancy.util", mock_util):
        sample = EvaluationSample(
            question="What are the side effects of ibuprofen?",
            answer="The stock market crashed yesterday due to poor earnings reports.",
        )
        result = evaluator.evaluate(sample)
        assert result.score < 0.5
        assert result.passed is False


def test_answer_relevancy_empty():
    """Empty answer → score 0.0."""
    evaluator, _ = _mock_relevancy_evaluator()
    sample = EvaluationSample(question="What?", answer="")
    result = evaluator.evaluate(sample)
    assert result.score == 0.0
