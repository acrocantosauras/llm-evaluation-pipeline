"""Faithfulness evaluator — determines whether the answer is supported by context.

Uses NLI (Natural Language Inference) to check each claim in the answer
against the provided context. Returns claim-level support information.

Methodology:
- Split answer into individual claims/sentences
- For each claim, run NLI against concatenated context
- Supported = ENTAILMENT, Unsupported = NEUTRAL/CONTRADICTION
- Score = fraction of supported claims

Limitations:
- Depends on NLI model accuracy
- Sentence splitting is approximate (period-based)
- Does not handle complex multi-hop reasoning
"""

from .base import BaseEvaluator, EvaluationSample, MetricResult


class FaithfulnessEvaluator(BaseEvaluator):
    name = "faithfulness"
    version = "1.0.0"

    def __init__(self):
        self._nli = None

    def _get_nli(self):
        if self._nli is None:
            from transformers import pipeline

            self._nli = pipeline("text-classification", model="roberta-large-mnli", device=-1)
        return self._nli

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        if not sample.answer or not sample.context:
            return self._make_result(0.0, passed=False, claims=[], total=0, supported=0)

        try:
            nli = self._get_nli()
            premise = " ".join(c.get("text", "") for c in sample.context)
            sentences = self._split_sentences(sample.answer)

            if not sentences:
                return self._make_result(0.0, passed=False, claims=[], total=0, supported=0)

            claims = []
            supported_count = 0

            for sentence in sentences:
                out = nli(f"{premise} </s></s> {sentence}")
                label = out[0]["label"].upper()
                is_supported = label in ("ENTAILMENT", "LABEL_2")
                if is_supported:
                    supported_count += 1
                claims.append(
                    {
                        "claim": sentence,
                        "supported": is_supported,
                        "label": label,
                        "confidence": round(out[0]["score"], 4),
                    }
                )

            score = round(supported_count / len(sentences), 4) if sentences else 0.0
            return self._make_result(
                score,
                passed=score >= 0.5,
                claims=claims,
                total=len(sentences),
                supported=supported_count,
            )
        except Exception as exc:
            return self._error_result(str(exc))

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        return [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
