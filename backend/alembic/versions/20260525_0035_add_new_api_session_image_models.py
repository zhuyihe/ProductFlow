"""add new api session image model options

Revision ID: 20260525_0035
Revises: 20260525_0034
Create Date: 2026-05-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0035"
down_revision = "20260525_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.add_column(sa.Column("new_api_image_models", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.drop_column("new_api_image_models")
