import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BaselineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class BaselineResponse(BaseModel):
    baseline_id: uuid.UUID
    name: str
    description: str
    run_id: uuid.UUID
    created_at: datetime


class RegressionEntry(BaseModel):
    metric: str
    baseline: float
    current: float
    change: float
    threshold: float
    direction: str


class ComparisonResponse(BaseModel):
    overall: str
    baseline_id: str | None = None
    regressions: list[RegressionEntry]
    improvements: list[RegressionEntry]


class QualityGateCheck(BaseModel):
    value: float
    threshold: float
    passed: bool
    direction: str


class QualityGateResult(BaseModel):
    status: str
    checks: dict[str, QualityGateCheck]


class QualityGateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    thresholds: dict = Field(
        default_factory=dict,
        description="Threshold config, e.g. {'relevance': {'min': 0.80}}",
    )


class QualityGateResponse(BaseModel):
    gate_id: uuid.UUID
    name: str
    thresholds: dict
    enabled: bool
    created_at: datetime
