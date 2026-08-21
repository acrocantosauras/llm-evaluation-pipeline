"""Tests for evaluation profiles."""

from evaluator.profiles import get_profile, list_profiles


def test_list_profiles():
    """All built-in profiles are listed."""
    profiles = list_profiles()
    assert "basic" in profiles
    assert "rag" in profiles
    assert "rag_strict" in profiles
    assert "judge" in profiles


def test_get_profile_basic():
    """Basic profile has traditional metrics."""
    profile = get_profile("basic")
    assert profile is not None
    assert "relevance" in profile.evaluators
    assert "hallucination" in profile.evaluators
    assert profile.use_judge is False


def test_get_profile_rag():
    """RAG profile has advanced metrics."""
    profile = get_profile("rag")
    assert profile is not None
    assert "faithfulness" in profile.evaluators
    assert "context_precision" in profile.evaluators
    assert "context_recall" in profile.evaluators
    assert "answer_relevancy" in profile.evaluators
    assert len(profile.composite_weights) > 0


def test_get_profile_judge():
    """Judge profile enables LLM judge."""
    profile = get_profile("judge")
    assert profile is not None
    assert profile.use_judge is True


def test_get_profile_nonexistent():
    """Unknown profile returns None."""
    assert get_profile("nonexistent") is None


def test_profiles_have_composite_weights():
    """RAG profiles have composite weights that sum to ~1.0."""
    for name in ["rag", "rag_strict", "judge"]:
        profile = get_profile(name)
        total = sum(profile.composite_weights.values())
        assert abs(total - 1.0) < 0.01, f"Profile {name} weights sum to {total}"
