"""add new api text model context

Revision ID: 20260526_0036
Revises: 20260525_0035
Create Date: 2026-05-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260526_0036"
down_revision = "20260525_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.add_column(sa.Column("new_api_text_model", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("new_api_text_models", sa.JSON(), nullable=True))
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(sa.Column("new_api_text_model", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("new_api_text_model")
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.drop_column("new_api_text_models")
        batch_op.drop_column("new_api_text_model")
