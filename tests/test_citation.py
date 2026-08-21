"""Tests for citation correctness evaluator."""

from unittest.mock import MagicMock

from evaluator.base import EvaluationSample


def _mock_citation_evaluator():
    from evaluator.citation_correctness import CitationCorrectnessEvaluator

    evaluator = CitationCorrectnessEvaluator()
    mock_nli = MagicMock()
    evaluator._nli = mock_nli
    return evaluator, mock_nli


def test_citation_correct():
    """Valid citation that matches context → score 1.0."""
    evaluator, mock_nli = _mock_citation_evaluator()
    mock_nli.return_value = [{"label": "ENTAILMENT", "score": 0.95}]

    sample = EvaluationSample(
        answer="Ibuprofen causes stomach upset.",
        context=[{"id": "doc-1", "text": "Ibuprofen causes stomach upset, nausea, and dizziness."}],
        citations=[{"source_id": "doc-1", "text": "Ibuprofen causes stomach upset."}],
    )
    result = evaluator.evaluate(sample)
    assert result.score == 1.0
    assert result.details["valid"] == 1
    assert result.details["total"] == 1


def test_citation_unsupported():
    """Citation that doesn't match context → lower score."""
    evaluator, mock_nli = _mock_citation_evaluator()
    mock_nli.return_value = [{"label": "CONTRADICTION", "score": 0.9}]

    sample = EvaluationSample(
        answer="Ibuprofen cures cancer.",
        context=[{"id": "doc-1", "text": "Ibuprofen is a pain reliever."}],
        citations=[{"source_id": "doc-1", "text": "Ibuprofen cures cancer."}],
    )
    result = evaluator.evaluate(sample)
    assert result.score == 0.0
    assert result.details["invalid"] == 1


def test_citation_missing_source():
    """Citation references non-existent source → penalised."""
    evaluator, mock_nli = _mock_citation_evaluator()

    sample = EvaluationSample(
        answer="Some claim.",
        context=[{"id": "doc-1", "text": "Some context."}],
        citations=[{"source_id": "doc-999", "text": "Non-existent source citation."}],
    )
    result = evaluator.evaluate(sample)
    assert result.details["missing_source"] == 1
    assert result.score == 0.0


def test_citation_no_citations():
    """No citations → score 1.0 (nothing to be wrong about)."""
    evaluator, _ = _mock_citation_evaluator()
    sample = EvaluationSample(answer="Some answer.", context=[], citations=[])
    result = evaluator.evaluate(sample)
    assert result.score == 1.0
    assert result.details["total"] == 0
