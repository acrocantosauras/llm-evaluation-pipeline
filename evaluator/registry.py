"""Evaluator registry — maps metric names to evaluator instances.

Central registry for all evaluators, enabling dynamic lookup and
profile-based evaluator selection.
"""

from .base import BaseEvaluator, EvaluationSample, MetricResult
from .profiles import get_profile

# Lazy-loaded evaluator instances
_evaluators: dict[str, BaseEvaluator] = {}


def _get_evaluator(name: str) -> BaseEvaluator | None:
    """Get or create an evaluator by name."""
    if name in _evaluators:
        return _evaluators[name]

    evaluator = _create_evaluator(name)
    if evaluator:
        _evaluators[name] = evaluator
    return evaluator


def _create_evaluator(name: str) -> BaseEvaluator | None:
    """Create an evaluator instance by name."""
    if name == "relevance":
        from .relevance import RelevanceEvaluator

        return RelevanceEvaluator()
    elif name == "hallucination":
        from .hallucination import HallucinationEvaluator

        return HallucinationEvaluator()
    elif name == "latency":
        from .latency import LatencyEvaluator

        return LatencyEvaluator()
    elif name == "cost":
        from .cost import CostEvaluator

        return CostEvaluator()
    elif name == "faithfulness":
        from .faithfulness import FaithfulnessEvaluator

        return FaithfulnessEvaluator()
    elif name == "context_precision":
        from .context_precision import ContextPrecisionEvaluator

        return ContextPrecisionEvaluator()
    elif name == "context_recall":
        from .context_recall import ContextRecallEvaluator

        return ContextRecallEvaluator()
    elif name == "answer_relevancy":
        from .answer_relevancy import AnswerRelevancyEvaluator

        return AnswerRelevancyEvaluator()
    elif name == "citation_correctness":
        from .citation_correctness import CitationCorrectnessEvaluator

        return CitationCorrectnessEvaluator()
    elif name == "llm_judge":
        from .judge import LLMJudgeEvaluator

        return LLMJudgeEvaluator()
    return None


def run_evaluators(
    evaluator_names: list[str],
    sample: EvaluationSample,
    use_judge: bool = False,
    judge_config: dict | None = None,
) -> list[MetricResult]:
    """Run a set of evaluators on a sample."""
    results = []

    for name in evaluator_names:
        evaluator = _get_evaluator(name)
        if evaluator is None:
            results.append(
                MetricResult(
                    metric=name,
                    score=0.0,
                    evaluator_version="0.0.0",
                    passed=False,
                    error=f"evaluator '{name}' not found",
                )
            )
            continue

        try:
            result = evaluator.evaluate(sample)
            results.append(result)
        except Exception as exc:
            results.append(
                MetricResult(
                    metric=name,
                    score=0.0,
                    evaluator_version=evaluator.version,
                    passed=False,
                    error=str(exc),
                )
            )

    # Run judge if requested and not already in the list
    if use_judge and "llm_judge" not in evaluator_names:
        judge = _get_evaluator("llm_judge")
        if judge:
            if judge_config:
                judge.provider = judge_config.get("provider", judge.provider)
                judge.model = judge_config.get("model", judge.model)
                judge.temperature = judge_config.get("temperature", judge.temperature)
            try:
                result = judge.evaluate(sample)
                results.append(result)
            except Exception as exc:
                results.append(
                    MetricResult(
                        metric="llm_judge",
                        score=0.0,
                        evaluator_version=judge.version,
                        passed=False,
                        error=str(exc),
                    )
                )

    return results


def evaluate_with_profile(
    profile_name: str,
    sample: EvaluationSample,
    judge_config: dict | None = None,
) -> list[MetricResult]:
    """Run evaluators defined by a profile."""
    profile = get_profile(profile_name)
    if profile is None:
        return [
            MetricResult(
                metric="error",
                score=0.0,
                evaluator_version="0.0.0",
                passed=False,
                error=f"profile '{profile_name}' not found",
            )
        ]

    return run_evaluators(
        profile.evaluators,
        sample,
        use_judge=profile.use_judge,
        judge_config=judge_config,
    )
