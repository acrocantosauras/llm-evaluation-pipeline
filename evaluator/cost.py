from .base import BaseEvaluator, EvaluationSample, MetricResult


def estimate_cost(conversation):
    """Legacy function — kept for backward compatibility."""
    input_tok = conversation.get("input_tokens", 0)
    output_tok = conversation.get("output_tokens", 0)
    price_in = 0.00015
    price_out = 0.0006
    cost = (input_tok / 1000) * price_in + (output_tok / 1000) * price_out
    return round(cost, 8)


class CostEvaluator(BaseEvaluator):
    name = "cost"
    version = "1.0.0"

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        conv = sample.conversation or {}
        cost = estimate_cost(conv)
        return self._make_result(
            min(cost / 0.01, 1.0),  # Normalize: $0.01 = 1.0
            passed=cost <= 0.01,
            estimated_cost=cost,
            input_tokens=conv.get("input_tokens", 0),
            output_tokens=conv.get("output_tokens", 0),
        )
