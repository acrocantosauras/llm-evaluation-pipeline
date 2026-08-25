"""Add projects and API keys tables for Phase 4 authentication.

Revision ID: 004_phase4_auth_projects
Revises: 003_phase3_metric_results
Create Date: 2025-01-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "004_phase4_auth_projects"
down_revision = "003_phase3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), server_default=""),
    )

    # Create API keys table
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add project_id columns to existing tables
    op.add_column(
        "evaluation_runs", sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    )
    op.create_index("ix_evaluation_runs_project_id", "evaluation_runs", ["project_id"])

    op.add_column(
        "evaluation_jobs", sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    )
    op.create_index("ix_evaluation_jobs_project_id", "evaluation_jobs", ["project_id"])

    op.add_column(
        "quality_gates", sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    )
    op.create_index("ix_quality_gates_project_id", "quality_gates", ["project_id"])

    op.add_column(
        "evaluation_baselines", sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    )
    op.create_index("ix_evaluation_baselines_project_id", "evaluation_baselines", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_baselines_project_id", table_name="evaluation_baselines")
    op.drop_column("evaluation_baselines", "project_id")

    op.drop_index("ix_quality_gates_project_id", table_name="quality_gates")
    op.drop_column("quality_gates", "project_id")

    op.drop_index("ix_evaluation_jobs_project_id", table_name="evaluation_jobs")
    op.drop_column("evaluation_jobs", "project_id")

    op.drop_index("ix_evaluation_runs_project_id", table_name="evaluation_runs")
    op.drop_column("evaluation_runs", "project_id")

    op.drop_table("api_keys")
    op.drop_table("projects")
