"""Add key_prefix and expires_at to api_keys for key hardening.

Revision ID: 005_api_key_hardening
Revises: 004_phase4_auth_projects
Create Date: 2026-08-25
"""

import sqlalchemy as sa

from alembic import op

revision = "005_api_key_hardening"
down_revision = "004_phase4_auth_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("key_prefix", sa.String(20), nullable=False, server_default=""))
    op.add_column("api_keys", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "expires_at")
    op.drop_column("api_keys", "key_prefix")
