"""Context recall evaluator — measures whether context contains info to answer.

Compares the answer against each context chunk to determine how much of
the answer is covered by the retrieved context.

Requires a reference_answer for best accuracy. Without a reference,
the evaluator uses the answer itself as a proxy.

Methodology:
- Split answer into claims
- For each claim, check if any context chunk supports it via NLI
- Score = fraction of answer claims supported by context

Limitations:
- Without reference_answer, measures self-consistency not true recall
- NLI model accuracy affects results
"""

from .base import BaseEvaluator, EvaluationSample, MetricResult


class ContextRecallEvaluator(BaseEvaluator):
    name = "context_recall"
    version = "1.0.0"

    def __init__(self):
        self._nli = None

    def _get_nli(self):
        if self._nli is None:
            from transformers import pipeline

            self._nli = pipeline("text-classification", model="roberta-large-mnli", device=-1)
        return self._nli

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        if not sample.context:
            return self._make_result(0.0, passed=False, claims_total=0, claims_recalled=0)

        # Use reference_answer if available, otherwise answer
        text_to_check = sample.reference_answer or sample.answer
        if not text_to_check:
            return self._make_result(0.0, passed=False, claims_total=0, claims_recalled=0)

        try:
            nli = self._get_nli()
            context_text = " ".join(c.get("text", "") for c in sample.context)
            sentences = self._split_sentences(text_to_check)

            if not sentences:
                return self._make_result(0.0, passed=False, claims_total=0, claims_recalled=0)

            recalled_count = 0
            claim_details = []

            for sentence in sentences:
                out = nli(f"{context_text} </s></s> {sentence}")
                label = out[0]["label"].upper()
                is_recalled = label in ("ENTAILMENT", "LABEL_2")
                if is_recalled:
                    recalled_count += 1
                claim_details.append(
                    {
                        "claim": sentence,
                        "recalled": is_recalled,
                        "label": label,
                        "confidence": round(out[0]["score"], 4),
                    }
                )

            score = round(recalled_count / len(sentences), 4) if sentences else 0.0
            return self._make_result(
                score,
                passed=score >= 0.5,
                claims_total=len(sentences),
                claims_recalled=recalled_count,
                claims=claim_details,
                has_reference=bool(sample.reference_answer),
            )
        except Exception as exc:
            return self._error_result(str(exc))

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        return [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
