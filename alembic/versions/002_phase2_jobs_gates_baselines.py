"""Add evaluation jobs, quality gates, and baselines

Revision ID: 002_phase2
Revises: 001_initial
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_phase2"
down_revision: str | None = "001_initial"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Add is_baseline to evaluation_runs first
    op.add_column(
        "evaluation_runs",
        sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default="false"),
    )

    # quality_gates table (created before evaluation_jobs which references it)
    op.create_table(
        "quality_gates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("thresholds", postgresql.JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
    )

    # evaluation_jobs table
    op.create_table(
        "evaluation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column(
            "evaluation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
            nullable=True,
        ),
        sa.Column(
            "quality_gate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quality_gates.id"),
            nullable=True,
        ),
        sa.Column("batch_results", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_evaluation_jobs_status", "evaluation_jobs", ["status"])
    op.create_index("ix_evaluation_jobs_created_at", "evaluation_jobs", ["created_at"])

    # evaluation_baselines table
    op.create_table(
        "evaluation_baselines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
            nullable=False,
            unique=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("evaluation_baselines")
    op.drop_index("ix_evaluation_jobs_created_at", table_name="evaluation_jobs")
    op.drop_index("ix_evaluation_jobs_status", table_name="evaluation_jobs")
    op.drop_table("evaluation_jobs")
    op.drop_table("quality_gates")
    op.drop_column("evaluation_runs", "is_baseline")
