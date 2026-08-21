import time

from .base import BaseEvaluator, EvaluationSample, MetricResult


def measure_latency(fn, runs=3):
    """Legacy function — kept for backward compatibility."""
    durations = []
    for _ in range(runs):
        start = time.time()
        fn()
        durations.append((time.time() - start) * 1000)
    return round(sum(durations) / len(durations), 3)


class LatencyEvaluator(BaseEvaluator):
    name = "latency"
    version = "1.0.0"

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        latency_ms = sample.conversation.get("latency_ms") or sample.metadata.get("latency_ms")
        if latency_ms is not None:
            return self._make_result(
                min(latency_ms / 10000, 1.0),  # Normalize: 0-10s maps to 0-1
                passed=latency_ms <= 2000,
                latency_ms=latency_ms,
            )
        return self._make_result(0.0, passed=True, latency_ms=0, note="no_latency_data")
