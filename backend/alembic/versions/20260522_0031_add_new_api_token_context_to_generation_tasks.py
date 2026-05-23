"""add new api token context to generation tasks

Revision ID: 20260522_0031
Revises: 20260522_0030
Create Date: 2026-05-22
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0031"
down_revision = "20260522_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column("new_api_user_id", sa.String(length=64), nullable=True))
    op.add_column("workflow_runs", sa.Column("new_api_token_id", sa.String(length=64), nullable=True))
    op.add_column("workflow_runs", sa.Column("new_api_token_name", sa.String(length=120), nullable=True))
    op.add_column("workflow_runs", sa.Column("new_api_token", sa.Text(), nullable=True))
    op.create_index("ix_workflow_runs_new_api_user_id", "workflow_runs", ["new_api_user_id"], unique=False)

    op.add_column("image_session_generation_tasks", sa.Column("new_api_user_id", sa.String(length=64), nullable=True))
    op.add_column("image_session_generation_tasks", sa.Column("new_api_token_id", sa.String(length=64), nullable=True))
    op.add_column(
        "image_session_generation_tasks",
        sa.Column("new_api_token_name", sa.String(length=120), nullable=True),
    )
    op.add_column("image_session_generation_tasks", sa.Column("new_api_token", sa.Text(), nullable=True))
    op.create_index(
        "ix_image_session_generation_tasks_new_api_user_id",
        "image_session_generation_tasks",
        ["new_api_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_image_session_generation_tasks_new_api_user_id",
        table_name="image_session_generation_tasks",
    )
    op.drop_column("image_session_generation_tasks", "new_api_token")
    op.drop_column("image_session_generation_tasks", "new_api_token_name")
    op.drop_column("image_session_generation_tasks", "new_api_token_id")
    op.drop_column("image_session_generation_tasks", "new_api_user_id")

    op.drop_index("ix_workflow_runs_new_api_user_id", table_name="workflow_runs")
    op.drop_column("workflow_runs", "new_api_token")
    op.drop_column("workflow_runs", "new_api_token_name")
    op.drop_column("workflow_runs", "new_api_token_id")
    op.drop_column("workflow_runs", "new_api_user_id")
