"""Evaluation profiles — define which evaluators run for each profile.

Profiles avoid running expensive evaluators (like LLM judges) unnecessarily.
"""

from dataclasses import dataclass, field


@dataclass
class EvalProfile:
    """Defines which evaluators to run and their configuration."""

    name: str
    description: str
    evaluators: list[str] = field(default_factory=list)
    use_judge: bool = False
    judge_config: dict = field(default_factory=dict)
    composite_weights: dict[str, float] = field(default_factory=dict)


# ── Built-in profiles ─────────────────────────────────────────────────────────

PROFILES: dict[str, EvalProfile] = {
    "basic": EvalProfile(
        name="basic",
        description="Traditional metrics: relevance, hallucination, latency, cost",
        evaluators=["relevance", "hallucination", "latency", "cost"],
    ),
    "rag": EvalProfile(
        name="rag",
        description="RAG evaluation: faithfulness, context precision/recall, answer relevancy",
        evaluators=[
            "relevance",
            "hallucination",
            "latency",
            "cost",
            "faithfulness",
            "context_precision",
            "context_recall",
            "answer_relevancy",
        ],
        composite_weights={
            "relevance": 0.15,
            "faithfulness": 0.25,
            "context_precision": 0.15,
            "context_recall": 0.15,
            "answer_relevancy": 0.15,
            "hallucination_fraction_unsupported": 0.15,
        },
    ),
    "rag_strict": EvalProfile(
        name="rag_strict",
        description="Strict RAG evaluation with citation correctness",
        evaluators=[
            "relevance",
            "hallucination",
            "latency",
            "cost",
            "faithfulness",
            "context_precision",
            "context_recall",
            "answer_relevancy",
            "citation_correctness",
        ],
        composite_weights={
            "relevance": 0.10,
            "faithfulness": 0.20,
            "context_precision": 0.15,
            "context_recall": 0.15,
            "answer_relevancy": 0.15,
            "citation_correctness": 0.15,
            "hallucination_fraction_unsupported": 0.10,
        },
    ),
    "judge": EvalProfile(
        name="judge",
        description="LLM judge evaluation with all RAG metrics",
        evaluators=[
            "relevance",
            "hallucination",
            "latency",
            "cost",
            "faithfulness",
            "context_precision",
            "context_recall",
            "answer_relevancy",
            "citation_correctness",
        ],
        use_judge=True,
        composite_weights={
            "relevance": 0.10,
            "faithfulness": 0.15,
            "context_precision": 0.10,
            "context_recall": 0.10,
            "answer_relevancy": 0.10,
            "citation_correctness": 0.10,
            "hallucination_fraction_unsupported": 0.10,
            "llm_judge": 0.25,
        },
    ),
}


def get_profile(name: str) -> EvalProfile | None:
    """Get a profile by name."""
    return PROFILES.get(name)


def list_profiles() -> dict[str, dict]:
    """List all available profiles."""
    return {
        name: {"name": p.name, "description": p.description, "evaluators": p.evaluators} for name, p in PROFILES.items()
    }
