from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock-based unit tests (fast, no model download)
# ---------------------------------------------------------------------------


def _make_mock_cosine_similarity(score_value):
    """Return a mock util.cos_sim that yields a fixed similarity score."""

    class MockTensor:
        def __init__(self, val):
            self._val = val

        def item(self):
            return self._val

    def fake_cos_sim(a, b):
        return MockTensor(score_value)

    return fake_cos_sim


@patch("evaluator.relevance.util")
@patch("evaluator.relevance.model")
def test_relevance_similar_text(mock_model, mock_util):
    """Similar texts should produce a high relevance score (> 0.5)."""
    mock_model.encode.return_value = MagicMock()
    mock_util.cos_sim.return_value = MagicMock()
    mock_util.cos_sim.return_value.item.return_value = 0.8

    from evaluator.relevance import relevance_score

    ctx = {"chunks": [{"text": "Ibuprofen may cause stomach upset."}]}
    score = relevance_score("Ibuprofen can cause stomach upset.", ctx)
    assert score > 0.5
    assert 0.0 <= score <= 1.0


@patch("evaluator.relevance.util")
@patch("evaluator.relevance.model")
def test_relevance_unrelated_text(mock_model, mock_util):
    """Unrelated texts should produce a lower relevance score."""
    mock_model.encode.return_value = MagicMock()
    mock_util.cos_sim.return_value = MagicMock()
    mock_util.cos_sim.return_value.item.return_value = -0.3

    from evaluator.relevance import relevance_score

    ctx = {"chunks": [{"text": "The stock market crashed yesterday."}]}
    score = relevance_score("Ibuprofen can cause stomach upset.", ctx)
    assert score < 0.5


@patch("evaluator.relevance.util")
@patch("evaluator.relevance.model")
def test_relevance_empty_answer(mock_model, mock_util):
    """Empty answer should return 0.0 without calling the model."""
    from evaluator.relevance import relevance_score

    ctx = {"chunks": [{"text": "Some context."}]}
    score = relevance_score("", ctx)
    assert score == 0.0
    mock_model.encode.assert_not_called()


@patch("evaluator.relevance.util")
@patch("evaluator.relevance.model")
def test_relevance_empty_context(mock_model, mock_util):
    """Empty context should return 0.0 without calling the model."""
    from evaluator.relevance import relevance_score

    score = relevance_score("Some answer.", {})
    assert score == 0.0
    mock_model.encode.assert_not_called()


@patch("evaluator.relevance.util")
@patch("evaluator.relevance.model")
def test_relevance_none_answer(mock_model, mock_util):
    """None/falsy answer should return 0.0."""
    from evaluator.relevance import relevance_score

    ctx = {"chunks": [{"text": "Some context."}]}
    score = relevance_score(None, ctx)
    assert score == 0.0


@patch("evaluator.relevance.util")
@patch("evaluator.relevance.model")
def test_relevance_score_range(mock_model, mock_util):
    """Score should always be in [0, 1] range after normalisation."""
    mock_model.encode.return_value = MagicMock()
    mock_util.cos_sim.return_value = MagicMock()
    mock_util.cos_sim.return_value.item.return_value = 0.0  # cosine sim = 0

    from evaluator.relevance import relevance_score

    ctx = {"chunks": [{"text": "context"}]}
    score = relevance_score("answer", ctx)
    # (0 + 1) / 2 = 0.5
    assert score == 0.5


@patch("evaluator.relevance.util")
@patch("evaluator.relevance.model")
def test_relevance_multiple_chunks(mock_model, mock_util):
    """Multiple context chunks should be concatenated."""
    mock_model.encode.return_value = MagicMock()
    mock_util.cos_sim.return_value = MagicMock()
    mock_util.cos_sim.return_value.item.return_value = 0.6

    from evaluator.relevance import relevance_score

    ctx = {"chunks": [{"text": "chunk one"}, {"text": "chunk two"}]}
    score = relevance_score("answer", ctx)
    assert 0.0 <= score <= 1.0
    # Verify encode was called (model used both chunks)
    assert mock_model.encode.call_count == 2


# ---------------------------------------------------------------------------
# Integration test (requires model download, slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_relevance_integration():
    """Full integration test with real model — slow, requires download."""
    from evaluator.relevance import relevance_score

    ans = "Ibuprofen can cause stomach upset."
    ctx = {"chunks": [{"text": "Ibuprofen may cause stomach upset."}]}
    score = relevance_score(ans, ctx)
    assert score > 0.5
    assert 0.0 <= score <= 1.0
