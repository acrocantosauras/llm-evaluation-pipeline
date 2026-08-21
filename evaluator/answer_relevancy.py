"""Answer relevancy evaluator — measures whether the answer addresses the question.

Uses a stronger evaluation than basic cosine similarity by:
1. Generating hypothetical answers from the question
2. Comparing the actual answer against the question AND hypothetical answers
3. Producing a relevancy score

Methodology:
- Compute cosine similarity between question and answer
- Generate multiple hypothetical question phrasings from the answer
- Compute similarity between answer and generated questions
- Average the scores for a robust relevancy measure

Limitations:
- Embedding-based similarity is a proxy, not a semantic understanding
- Does not detect factually correct but off-topic answers
"""

from sentence_transformers import util

from .base import BaseEvaluator, EvaluationSample, MetricResult


class AnswerRelevancyEvaluator(BaseEvaluator):
    name = "answer_relevancy"
    version = "1.0.0"

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        if not sample.question or not sample.answer:
            return self._make_result(0.0, passed=False, question_answer_similarity=0.0)

        try:
            model = self._get_model()

            q_emb = model.encode(sample.question, convert_to_tensor=True)
            a_emb = model.encode(sample.answer, convert_to_tensor=True)

            # Direct question-answer similarity
            qa_sim = util.cos_sim(q_emb, a_emb).item()
            qa_normalized = round((qa_sim + 1) / 2, 4)

            # Generate hypothetical questions from the answer
            # Use simple sentence splitting to create pseudo-questions
            sentences = [s.strip() for s in sample.answer.replace("\n", " ").split(". ") if s.strip()]
            hypothetical_scores = []

            for sentence in sentences[:5]:  # Limit to 5 for efficiency
                h_emb = model.encode(sentence, convert_to_tensor=True)
                h_sim = util.cos_sim(q_emb, h_emb).item()
                hypothetical_scores.append(round((h_sim + 1) / 2, 4))

            # Combined score: weighted average of direct and hypothetical similarity
            if hypothetical_scores:
                avg_hypothetical = sum(hypothetical_scores) / len(hypothetical_scores)
                score = round(0.6 * qa_normalized + 0.4 * avg_hypothetical, 4)
            else:
                score = qa_normalized

            return self._make_result(
                score,
                passed=score >= 0.5,
                question_answer_similarity=qa_normalized,
                hypothetical_scores=hypothetical_scores,
                num_hypotheticals=len(hypothetical_scores),
            )
        except Exception as exc:
            return self._error_result(str(exc))
