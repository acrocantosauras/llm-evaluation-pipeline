"""Hallucination module unit tests.

These tests mock the heavy NLI model import so they can run without
downloading or loading RoBERTa.
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _import_hallucination_with_mock():
    """Import hallucination module with a mocked NLI pipeline."""
    mock_pipeline_fn = MagicMock(return_value=[{"label": "ENTAILMENT", "score": 0.95}])

    # Patch transformers.pipeline before importing the module
    with patch.dict(sys.modules, {}):
        # Ensure evaluator package is importable
        import evaluator  # noqa: F401

        mock_transformers = types.ModuleType("transformers")
        mock_transformers.pipeline = MagicMock(return_value=mock_pipeline_fn)
        original = sys.modules.get("transformers")
        sys.modules["transformers"] = mock_transformers

        # Force reimport
        if "evaluator.hallucination" in sys.modules:
            del sys.modules["evaluator.hallucination"]

        from evaluator.hallucination import hallucination_report, split_sentences

        # Restore
        if original is not None:
            sys.modules["transformers"] = original
        else:
            sys.modules.pop("transformers", None)

        return split_sentences, hallucination_report, mock_pipeline_fn


# ---------------------------------------------------------------------------
# split_sentences unit tests (pure function — no ML needed)
# ---------------------------------------------------------------------------


@pytest.fixture()
def split_sentences():
    """Provide split_sentences with mocked NLI pipeline."""
    ss, _, _ = _import_hallucination_with_mock()
    return ss


def test_split_sentences_normal(split_sentences):
    result = split_sentences("Hello world. This is a test. Another sentence.")
    assert len(result) == 3
    assert result[0] == "Hello world"
    assert result[1] == "This is a test"
    # Last sentence may or may not retain trailing period
    assert "Another sentence" in result[2]


def test_split_sentences_single_sentence(split_sentences):
    result = split_sentences("Just one sentence.")
    assert result == ["Just one sentence."]


def test_split_sentences_empty(split_sentences):
    result = split_sentences("")
    assert result == []


def test_split_sentences_newlines(split_sentences):
    result = split_sentences("Line one.\nLine two.")
    assert len(result) >= 1


def test_split_sentences_no_periods(split_sentences):
    result = split_sentences("No periods here")
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# hallucination_report tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def hallucination_report_and_mock():
    """Provide hallucination_report with a configurable mock NLI pipeline."""
    _, report_fn, mock_nli = _import_hallucination_with_mock()
    return report_fn, mock_nli


def test_hallucination_report_all_supported(hallucination_report_and_mock):
    """All sentences supported -> fraction_supported = 1.0, no flags."""
    report_fn, mock_nli = hallucination_report_and_mock
    mock_nli.return_value = [{"label": "ENTAILMENT", "score": 0.99}]

    ctx = {"chunks": [{"text": "Ibuprofen causes stomach upset."}]}
    report = report_fn("Ibuprofen causes stomach upset.", ctx)
    assert report["fraction_supported"] == 1.0
    assert report["flags"] == []
    assert len(report["details"]) == 1


def test_hallucination_report_contradiction(hallucination_report_and_mock):
    """Contradicted sentence -> appears in flags."""
    report_fn, mock_nli = hallucination_report_and_mock
    mock_nli.return_value = [{"label": "CONTRADICTION", "score": 0.90}]

    ctx = {"chunks": [{"text": "Ibuprofen causes stomach upset."}]}
    report = report_fn("Ibuprofen cures cancer.", ctx)
    assert report["fraction_supported"] == 0.0
    assert len(report["flags"]) == 1
    assert report["flags"][0]["label"] == "CONTRADICTION"


def test_hallucination_report_unsupported(hallucination_report_and_mock):
    """Neutral/unsupported sentence -> appears in flags as UNSUPPORTED."""
    report_fn, mock_nli = hallucination_report_and_mock
    mock_nli.return_value = [{"label": "NEUTRAL", "score": 0.70}]

    ctx = {"chunks": [{"text": "Ibuprofen causes stomach upset."}]}
    report = report_fn("The sky is blue today.", ctx)
    assert report["fraction_supported"] == 0.0
    assert len(report["flags"]) == 1
    assert report["flags"][0]["label"] == "UNSUPPORTED"


def test_hallucination_report_mixed(hallucination_report_and_mock):
    """Mix of supported and contradicted sentences."""
    report_fn, mock_nli = hallucination_report_and_mock
    mock_nli.side_effect = [
        [{"label": "ENTAILMENT", "score": 0.99}],
        [{"label": "CONTRADICTION", "score": 0.90}],
    ]

    ctx = {"chunks": [{"text": "Ibuprofen causes stomach upset and nausea."}]}
    report = report_fn("Ibuprofen causes stomach upset. Ibuprofen cures cancer.", ctx)
    assert report["fraction_supported"] == 0.5
    assert len(report["flags"]) == 1
    assert len(report["details"]) == 2


def test_hallucination_report_details_contain_scores(hallucination_report_and_mock):
    """Each detail entry should include the NLI confidence score."""
    report_fn, mock_nli = hallucination_report_and_mock
    mock_nli.return_value = [{"label": "ENTAILMENT", "score": 0.88}]

    ctx = {"chunks": [{"text": "Context."}]}
    report = report_fn("A sentence.", ctx)
    assert report["details"][0]["score"] == 0.88


def test_hallucination_report_empty_answer(hallucination_report_and_mock):
    """Empty answer -> no sentences, should return safe defaults."""
    report_fn, mock_nli = hallucination_report_and_mock
    ctx = {"chunks": [{"text": "Context."}]}
    report = report_fn("", ctx)
    assert report["fraction_supported"] == 0.0
    assert report["flags"] == []
    assert report["details"] == []
    mock_nli.assert_not_called()
