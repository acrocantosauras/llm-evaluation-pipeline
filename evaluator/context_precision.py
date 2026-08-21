"""Context precision evaluator — measures whether retrieved context is relevant.

Compares each context chunk against the question to determine relevance.
High precision means most retrieved chunks are relevant to the question.
Low precision means many irrelevant chunks were retrieved.

Methodology:
- For each context chunk, compute cosine similarity with the question
- Count chunks above a relevance threshold
- Score = fraction of chunks that are relevant

Limitations:
- Relies on embedding similarity as a proxy for relevance
- Does not understand semantic nuance beyond embedding space
"""

from sentence_transformers import util

from .base import BaseEvaluator, EvaluationSample, MetricResult


class ContextPrecisionEvaluator(BaseEvaluator):
    name = "context_precision"
    version = "1.0.0"

    RELEVANCE_THRESHOLD = 0.3  # cosine similarity threshold

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        if not sample.question or not sample.context:
            return self._make_result(0.0, passed=False, chunks_total=0, chunks_relevant=0)

        try:
            model = self._get_model()

            q_emb = model.encode(sample.question, convert_to_tensor=True)
            relevant_count = 0
            chunk_scores = []

            for chunk in sample.context:
                text = chunk.get("text", "")
                if not text:
                    continue
                c_emb = model.encode(text, convert_to_tensor=True)
                score = util.cos_sim(q_emb, c_emb).item()
                normalized = round((score + 1) / 2, 4)
                chunk_scores.append(
                    {
                        "text": text[:200],
                        "score": normalized,
                        "relevant": normalized >= self.RELEVANCE_THRESHOLD,
                    }
                )
                if normalized >= self.RELEVANCE_THRESHOLD:
                    relevant_count += 1

            total = len(sample.context)
            precision = round(relevant_count / total, 4) if total > 0 else 0.0

            return self._make_result(
                precision,
                passed=precision >= 0.5,
                chunks_total=total,
                chunks_relevant=relevant_count,
                chunks=chunk_scores,
            )
        except Exception as exc:
            return self._error_result(str(exc))
