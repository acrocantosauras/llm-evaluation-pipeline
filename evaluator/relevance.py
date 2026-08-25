from sentence_transformers import util

from .base import BaseEvaluator, EvaluationSample, MetricResult

# Lazy model loading — avoids import-time side effects
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# Legacy alias for backward compatibility with tests that patch this
model = None


def relevance_score(answer: str, context: dict) -> float:
    """Legacy function — kept for backward compatibility."""
    if not answer or not context:
        return 0.0
    m = _get_model()
    ctx_text = " ".join([c.get("text", "") for c in context.get("chunks", [])])
    emb_a = m.encode(answer, convert_to_tensor=True)
    emb_c = m.encode(ctx_text, convert_to_tensor=True)
    score = util.cos_sim(emb_a, emb_c).item()
    return round((score + 1) / 2, 4)


class RelevanceEvaluator(BaseEvaluator):
    name = "relevance"
    version = "1.0.0"

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        if not sample.answer or not sample.context:
            return self._make_result(0.0, passed=False)

        try:
            m = self._get_model()
            ctx_text = " ".join(c.get("text", "") for c in sample.context)
            emb_a = m.encode(sample.answer, convert_to_tensor=True)
            emb_c = m.encode(ctx_text, convert_to_tensor=True)
            score = round((util.cos_sim(emb_a, emb_c).item() + 1) / 2, 4)
            return self._make_result(score, passed=score >= 0.5)
        except Exception as exc:
            return self._error_result(str(exc))
