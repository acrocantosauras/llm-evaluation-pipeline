import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvaluationRun(Base):
    """Stores a single evaluation run with its input and results."""

    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    is_baseline: Mapped[bool] = mapped_column(default=False)

    # Input data
    conversation: Mapped[dict] = mapped_column(JSON, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Evaluation results
    relevance: Mapped[float] = mapped_column(Float, nullable=True)
    hallucination: Mapped[dict] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=True)

    # Relationships
    job: Mapped["EvaluationJob | None"] = relationship(back_populates="evaluation_run", uselist=False)


class EvaluationJob(Base):
    """Tracks async evaluation job lifecycle and progress."""

    __tablename__ = "evaluation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)

    # Progress tracking
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Input
    items: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Results
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=True
    )
    evaluation_run: Mapped["EvaluationRun | None"] = relationship(back_populates="job")

    # Quality gate
    quality_gate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quality_gates.id"), nullable=True
    )

    # Batch results
    batch_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class QualityGate(Base):
    """Configurable quality gate with per-metric thresholds."""

    __tablename__ = "quality_gates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True)


class EvaluationBaseline(Base):
    """Marks an evaluation run as a baseline for comparison."""

    __tablename__ = "evaluation_baselines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), unique=True, nullable=False
    )
