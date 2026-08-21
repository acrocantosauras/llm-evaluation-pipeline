import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ContextChunk(BaseModel):
    id: str = Field(default="", description="Optional chunk identifier")
    text: str = Field(..., description="Text content of the context chunk")


class ConversationInput(BaseModel):
    model_response: str = Field(..., description="The LLM response to evaluate")
    input_tokens: int = Field(default=0, ge=0, description="Number of input tokens")
    output_tokens: int = Field(default=0, ge=0, description="Number of output tokens")
    latency_ms: float | None = Field(default=None, description="Pre-measured latency in ms")


class EvaluationRequest(BaseModel):
    conversation: ConversationInput = Field(..., description="Conversation/response data to evaluate")
    context: list[ContextChunk] = Field(
        ..., min_length=1, description="Context chunks for relevance and hallucination checking"
    )


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


class EvaluationResult(BaseModel):
    relevance: float
    hallucination: HallucinationResult
    latency_ms: float
    estimated_cost: float


class EvaluationResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    results: EvaluationResult
    created_at: datetime
