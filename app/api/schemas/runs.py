import uuid
from datetime import datetime

from pydantic import BaseModel

from app.api.schemas.evaluations import EvaluationResult


class RunResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    results: EvaluationResult
    created_at: datetime


class PaginatedRunsResponse(BaseModel):
    runs: list[RunResponse]
    total: int
    offset: int
    limit: int
