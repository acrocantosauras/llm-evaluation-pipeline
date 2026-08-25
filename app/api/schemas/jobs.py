import os
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas.evaluations import ContextChunk, ConversationInput

# Hard cap on async batch size. Prevents a single request from creating an
# enormous `items` JSON blob in the evaluation_jobs row (DoS / WAL bloat).
# Override via env for deployments with different capacity profiles.
MAX_BATCH_ITEMS = int(os.getenv("MAX_BATCH_ITEMS", "100"))


class BatchEvaluationItem(BaseModel):
    """A single evaluation case within a batch."""

    conversation: ConversationInput
    context: list[ContextChunk] = Field(..., min_length=1)


class AsyncEvaluationRequest(BaseModel):
    """Request to submit an async batch evaluation."""

    items: list[BatchEvaluationItem] = Field(
        ...,
        min_length=1,
        max_length=MAX_BATCH_ITEMS,
        description=f"Evaluation cases to process (max {MAX_BATCH_ITEMS})",
    )
    quality_gate_id: uuid.UUID | None = Field(default=None, description="Optional quality gate to apply")


class JobProgress(BaseModel):
    total: int
    completed: int
    failed: int


class JobResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    progress: JobProgress | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    evaluation_run_id: uuid.UUID | None = None
    batch_results: dict | None = None


class PaginatedJobsResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    offset: int
    limit: int
