from .cost import estimate_cost
from .hallucination import hallucination_report
from .latency import measure_latency
from .relevance import relevance_score


class EvaluationPipeline:
    def evaluate(self, conversation, context):
        response = conversation.get("model_response", "")
        return {
            "relevance": relevance_score(response, context),
            "hallucination": hallucination_report(response, context),
            "latency_ms": conversation.get("latency_ms") or measure_latency(lambda: None),
            "estimated_cost": estimate_cost(conversation),
        }
