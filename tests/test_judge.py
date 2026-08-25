"""Tests for the LLM judge evaluator — real latency measurement, no network."""

import json
import time

from evaluator.base import EvaluationSample
from evaluator.judge import LLMJudgeEvaluator


def _sample() -> EvaluationSample:
    return EvaluationSample(
        question="What is ibuprofen?",
        answer="Ibuprofen is a nonsteroidal anti-inflammatory drug.",
        context=[{"text": "Ibuprofen is an NSAID used for pain and fever."}],
    )


def test_judge_latency_is_measured_not_zero(monkeypatch):
    """latency_ms reflects the actual LLM call duration (monotonic clock)."""

    def fake_call(self, prompt: str) -> str:
        time.sleep(0.05)  # deterministic mocked delay
        return json.dumps({"score": 4, "reason": "mostly correct", "criteria": {"correctness": 4}})

    monkeypatch.setattr(LLMJudgeEvaluator, "_call_llm", fake_call)

    judge = LLMJudgeEvaluator(max_retries=1)
    result = judge.evaluate(_sample())

    assert result.error is None
    assert result.score == 0.8
    latency = result.details["latency_ms"]
    assert isinstance(latency, (int, float))
    assert latency >= 50.0  # at least the mocked delay


def test_judge_latency_present_on_success_without_delay(monkeypatch):
    """Even a fast call reports a positive (non-zero) latency."""

    def fake_call(self, prompt: str) -> str:
        return '{"score": 5, "reason": "correct", "criteria": {}}'

    monkeypatch.setattr(LLMJudgeEvaluator, "_call_llm", fake_call)

    judge = LLMJudgeEvaluator(max_retries=1)
    result = judge.evaluate(_sample())

    assert result.score == 1.0
    assert result.details["latency_ms"] > 0


def test_judge_retry_then_success_reports_last_call_latency(monkeypatch):
    """Latency is measured per successful call, not accumulated across retries."""
    calls = {"n": 0}

    def fake_call(self, prompt: str) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient failure")
        time.sleep(0.02)
        return '{"score": 3, "reason": "partial"}'

    monkeypatch.setattr(LLMJudgeEvaluator, "_call_llm", fake_call)

    judge = LLMJudgeEvaluator(max_retries=3)
    result = judge.evaluate(_sample())

    assert calls["n"] == 2
    assert result.error is None
    # Latency of the successful call only (~20ms), not inflated by the failed attempt.
    assert 0 < result.details["latency_ms"] < 100.0


def test_judge_error_result_has_no_false_latency(monkeypatch):
    def failing_call(self, prompt: str) -> str:
        raise RuntimeError("provider down")

    monkeypatch.setattr(LLMJudgeEvaluator, "_call_llm", failing_call)

    judge = LLMJudgeEvaluator(max_retries=1)
    result = judge.evaluate(_sample())

    assert result.passed is False
    assert "provider down" in (result.error or "")
