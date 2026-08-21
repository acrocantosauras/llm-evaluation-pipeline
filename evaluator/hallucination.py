from transformers import pipeline

from .base import BaseEvaluator, EvaluationSample, MetricResult

# NOTE: Change to "facebook/bart-large-mnli" if you want faster downloads
nli = pipeline("text-classification", model="roberta-large-mnli", device=-1)


def split_sentences(text):
    return [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]


def hallucination_report(answer, context):
    """Legacy function — kept for backward compatibility."""
    premise = " ".join([c.get("text", "") for c in context.get("chunks", [])])
    sentences = split_sentences(answer)
    if not sentences:
        return {"fraction_supported": 0.0, "flags": [], "details": []}
    supported = 0
    flags = []
    details = []
    for s in sentences:
        out = nli(f"{premise} </s></s> {s}")
        label = out[0]["label"].upper()
        if label in ("ENTAILMENT", "LABEL_2"):
            supported += 1
        elif label in ("CONTRADICTION", "LABEL_0"):
            flags.append({"sentence": s, "label": "CONTRADICTION"})
        else:
            flags.append({"sentence": s, "label": "UNSUPPORTED"})
        details.append({"sentence": s, "label": label, "score": out[0]["score"]})
    return {"fraction_supported": round(supported / len(sentences), 4), "flags": flags, "details": details}


class HallucinationEvaluator(BaseEvaluator):
    name = "hallucination"
    version = "1.0.0"

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        if not sample.answer or not sample.context:
            return self._make_result(0.0, passed=False, fraction_supported=0.0)

        try:
            report = hallucination_report(sample.answer, {"chunks": sample.context})
            return self._make_result(
                report["fraction_supported"],
                passed=report["fraction_supported"] >= 0.5,
                fraction_supported=report["fraction_supported"],
                flags=report["flags"],
                details=report["details"],
            )
        except Exception as exc:
            return self._error_result(str(exc))
