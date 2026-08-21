import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas.evaluations import EvaluationResult, MetricResultSchema


class RunResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    results: EvaluationResult
    profile: str | None = None
    composite_score: float | None = None
    metric_results: list[MetricResultSchema] = Field(default_factory=list)
    created_at: datetime


class PaginatedRunsResponse(BaseModel):
    runs: list[RunResponse]
    total: int
    offset: int
    limit: int
