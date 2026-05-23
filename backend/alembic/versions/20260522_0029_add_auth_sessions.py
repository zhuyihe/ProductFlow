"""add server-side auth sessions

Revision ID: 20260522_0029
Revises: 20260513_0028
Create Date: 2026-05-22
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0029"
down_revision = "20260513_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("principal_kind", sa.String(length=20), nullable=False),
        sa.Column("new_api_user_id", sa.String(length=64), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("group", sa.String(length=120), nullable=True),
        sa.Column("role", sa.String(length=80), nullable=True),
        sa.Column("new_api_token_id", sa.String(length=64), nullable=True),
        sa.Column("new_api_token_name", sa.String(length=120), nullable=True),
        sa.Column("new_api_token", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"], unique=False)
    op.create_index("ix_auth_sessions_new_api_user_id", "auth_sessions", ["new_api_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_new_api_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_table("auth_sessions")
