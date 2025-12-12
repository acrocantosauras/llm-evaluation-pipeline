from .relevance import relevance_score
from .hallucination import hallucination_report
from .latency import measure_latency
from .cost import estimate_cost

class EvaluationPipeline:
    def evaluate(self, conversation, context):
        response = conversation.get("model_response","")
        return {
            "relevance": relevance_score(response, context),
            "hallucination": hallucination_report(response, context),
            "latency_ms": conversation.get("latency_ms") or measure_latency(lambda: None),
            "estimated_cost": estimate_cost(conversation)
        }
