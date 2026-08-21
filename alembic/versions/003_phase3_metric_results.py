"""Add metric results table and advanced evaluation fields

Revision ID: 003_phase3
Revises: 002_phase2
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_phase3"
down_revision: str | None = "002_phase2"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Add profile and composite_score to evaluation_runs
    op.add_column("evaluation_runs", sa.Column("profile", sa.String(50), nullable=True))
    op.add_column("evaluation_runs", sa.Column("composite_score", sa.Float(), nullable=True))

    # Create metric_results table
    op.create_table(
        "metric_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
            nullable=False,
        ),
        sa.Column("metric", sa.String(100), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("evaluator_version", sa.String(20), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(1000), nullable=True),
    )
    op.create_index("ix_metric_results_run_id", "metric_results", ["run_id"])
    op.create_index("ix_metric_results_metric", "metric_results", ["metric"])


def downgrade() -> None:
    op.drop_index("ix_metric_results_metric", table_name="metric_results")
    op.drop_index("ix_metric_results_run_id", table_name="metric_results")
    op.drop_table("metric_results")
    op.drop_column("evaluation_runs", "composite_score")
    op.drop_column("evaluation_runs", "profile")
