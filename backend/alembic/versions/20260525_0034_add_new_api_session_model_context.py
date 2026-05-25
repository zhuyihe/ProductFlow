"""add new api session model context

Revision ID: 20260525_0034
Revises: 20260524_0033
Create Date: 2026-05-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0034"
down_revision = "20260524_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("auth_sessions", "workflow_runs", "image_session_generation_tasks"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("new_api_token_group", sa.String(length=120), nullable=True))
            batch_op.add_column(sa.Column("new_api_image_model", sa.String(length=255), nullable=True))


def downgrade() -> None:
    for table_name in ("image_session_generation_tasks", "workflow_runs", "auth_sessions"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("new_api_image_model")
            batch_op.drop_column("new_api_token_group")
