import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ContextChunk(BaseModel):
    id: str = Field(default="", description="Optional chunk identifier")
    text: str = Field(
        ...,
        max_length=10_000,
        description="Text content of the context chunk",
    )


class Citation(BaseModel):
    source_id: str = Field(..., description="Reference to a context chunk")
    text: str = Field(..., description="Cited text")


class ConversationInput(BaseModel):
    model_response: str = Field(
        default="",
        max_length=20_000,
        description="The LLM response to evaluate",
    )
    question: str = Field(default="", max_length=10_000, description="The original question (for advanced metrics)")
    input_tokens: int = Field(default=0, ge=0, description="Number of input tokens")
    output_tokens: int = Field(default=0, ge=0, description="Number of output tokens")
    latency_ms: float | None = Field(default=None, description="Pre-measured latency in ms")
    reference_answer: str = Field(default="", max_length=10_000, description="Ground-truth answer (for context recall)")
    citations: list[Citation] = Field(default_factory=list, max_length=100, description="Citations in the answer")


class EvaluationRequest(BaseModel):
    conversation: ConversationInput = Field(..., description="Conversation/response data to evaluate")
    context: list[ContextChunk] = Field(..., min_length=1, max_length=50, description="Context chunks for evaluation")
    profile: str = Field(default="basic", description="Evaluation profile: basic, rag, rag_strict, judge")
    judge_config: dict | None = Field(default=None, description="Optional judge configuration override")


class HallucinationDetail(BaseModel):
    sentence: str
    label: str
    score: float


class HallucinationFlag(BaseModel):
    sentence: str
    label: str


class HallucinationResult(BaseModel):
    fraction_supported: float
    flags: list[HallucinationFlag]
    details: list[HallucinationDetail]


class MetricResultSchema(BaseModel):
    metric: str
    score: float
    evaluator_version: str
    passed: bool | None = None
    details: dict = Field(default_factory=dict)
    error: str | None = None


class EvaluationResult(BaseModel):
    relevance: float | None = None
    hallucination: HallucinationResult | None = None
    latency_ms: float | None = None
    estimated_cost: float | None = None


class EvaluationResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    results: EvaluationResult
    profile: str | None = None
    composite_score: float | None = None
    metric_results: list[MetricResultSchema] = Field(default_factory=list)
    created_at: datetime
