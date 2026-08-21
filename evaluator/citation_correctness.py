"""Citation correctness evaluator — checks if citations support claims.

Evaluates whether citations in the answer:
1. Exist and are non-empty
2. Point to available sources in the context
3. Actually support the associated claims

Methodology:
- Match each citation to a context chunk by source_id or text similarity
- For matched citations, verify the cited text appears in context
- Score = fraction of citations that are valid and supported

Limitations:
- Requires citations in a structured format
- Text matching is approximate for long passages
- Cannot verify semantic support without NLI (use faithfulness for that)
"""

from .base import BaseEvaluator, EvaluationSample, MetricResult


class CitationCorrectnessEvaluator(BaseEvaluator):
    name = "citation_correctness"
    version = "1.0.0"

    def __init__(self):
        self._nli = None

    def _get_nli(self):
        if self._nli is None:
            from transformers import pipeline

            self._nli = pipeline("text-classification", model="roberta-large-mnli", device=-1)
        return self._nli

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        if not sample.citations:
            return self._make_result(
                1.0,  # No citations = no incorrect citations
                passed=True,
                total=0,
                valid=0,
                invalid=0,
                missing_source=0,
            )

        try:
            nli = self._get_nli()
            context_map = {c.get("id", ""): c.get("text", "") for c in sample.context}
            context_texts = [c.get("text", "") for c in sample.context]

            valid = 0
            invalid = 0
            missing_source = 0
            citation_details = []

            for citation in sample.citations:
                source_id = citation.get("source_id", "")
                cited_text = citation.get("text", "")

                # Check if source exists in context
                source_text = context_map.get(source_id, "")
                if not source_text and source_id:
                    # Try to find by text similarity
                    for ct in context_texts:
                        if cited_text and cited_text[:50] in ct:
                            source_text = ct
                            break

                if not source_text:
                    missing_source += 1
                    citation_details.append(
                        {
                            "source_id": source_id,
                            "cited_text": cited_text[:200],
                            "valid": False,
                            "reason": "source_not_found",
                        }
                    )
                    continue

                # Verify citation supports the cited text via NLI
                try:
                    out = nli(f"{source_text} </s></s> {cited_text}")
                    label = out[0]["label"].upper()
                    is_valid = label in ("ENTAILMENT", "LABEL_2")
                except Exception:
                    is_valid = False

                if is_valid:
                    valid += 1
                else:
                    invalid += 1

                citation_details.append(
                    {
                        "source_id": source_id,
                        "cited_text": cited_text[:200],
                        "valid": is_valid,
                        "nli_label": label if "label" in dir() else "unknown",
                    }
                )

            total = len(sample.citations)
            score = round(valid / total, 4) if total > 0 else 1.0

            return self._make_result(
                score,
                passed=score >= 0.5,
                total=total,
                valid=valid,
                invalid=invalid,
                missing_source=missing_source,
                citations=citation_details,
            )
        except Exception as exc:
            return self._error_result(str(exc))
