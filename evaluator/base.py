"""Evaluator base classes and structured result types.

Every evaluator produces a MetricResult with a predictable output contract.
Evaluator versioning ensures reproducibility of historical results.
"""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MetricResult:
    """Structured output from every evaluator."""

    metric: str
    score: float
    evaluator_version: str
    passed: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvaluationSample:
    """Input to evaluators — standardised evaluation input."""

    question: str = ""
    answer: str = ""
    context: list[dict] = field(default_factory=list)  # [{"text": "...", "id": "..."}]
    conversation: dict = field(default_factory=dict)  # legacy format
    citations: list[dict] = field(default_factory=list)  # [{"source_id": "...", "text": "..."}]
    reference_answer: str = ""
    metadata: dict = field(default_factory=dict)


class BaseEvaluator:
    """Base class for all evaluators."""

    name: str = "base"
    version: str = "1.0.0"

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        raise NotImplementedError

    def _make_result(self, score: float, passed: bool | None = None, **details) -> MetricResult:
        return MetricResult(
            metric=self.name,
            score=score,
            evaluator_version=self.version,
            passed=passed,
            details=details,
        )

    def _error_result(self, error: str) -> MetricResult:
        return MetricResult(
            metric=self.name,
            score=0.0,
            evaluator_version=self.version,
            passed=False,
            error=error,
        )
