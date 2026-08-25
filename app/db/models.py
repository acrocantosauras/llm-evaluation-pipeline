import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Auth & Projects ────────────────────────────────────────────────────────────


class Project(Base):
    """Project/workspace that owns all resources."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="")

    # Relationships
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="project")


class ApiKey(Base):
    """API key for project authentication."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # Display prefix of the plaintext key (never enough to reconstruct it)
    key_prefix: Mapped[str] = mapped_column(String(20), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Optional expiry — expired keys are rejected during authentication
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="api_keys")


# ── Evaluation Resources ───────────────────────────────────────────────────────


class EvaluationRun(Base):
    """Stores a single evaluation run with its input and results."""

    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="completed")
    is_baseline: Mapped[bool] = mapped_column(default=False)
    profile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Input data
    conversation: Mapped[dict] = mapped_column(JSON, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Legacy evaluation results (kept for backward compatibility)
    relevance: Mapped[float] = mapped_column(Float, nullable=True)
    hallucination: Mapped[dict] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=True)

    # Relationships
    job: Mapped["EvaluationJob | None"] = relationship(back_populates="evaluation_run", uselist=False)
    metric_results: Mapped[list["MetricResultRecord"]] = relationship(back_populates="evaluation_run")


class MetricResultRecord(Base):
    """Stores individual metric results for an evaluation run."""

    __tablename__ = "metric_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool | None] = mapped_column(nullable=True)
    evaluator_version: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    evaluation_run: Mapped["EvaluationRun"] = relationship(back_populates="metric_results")


class EvaluationJob(Base):
    """Tracks async evaluation job lifecycle and progress."""

    __tablename__ = "evaluation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)

    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    items: Mapped[dict] = mapped_column(JSON, nullable=False)

    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=True
    )
    evaluation_run: Mapped["EvaluationRun | None"] = relationship(back_populates="job")

    quality_gate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quality_gates.id"), nullable=True
    )

    batch_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class QualityGate(Base):
    """Configurable quality gate with per-metric thresholds."""

    __tablename__ = "quality_gates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True)


class EvaluationBaseline(Base):
    """Marks an evaluation run as a baseline for comparison."""

    __tablename__ = "evaluation_baselines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), unique=True, nullable=False
    )
