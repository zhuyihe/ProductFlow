"""add owner columns for multi-user isolation

Revision ID: 20260522_0030
Revises: 20260522_0029
Create Date: 2026-05-22
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0030"
down_revision = "20260522_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("owner_user_id", sa.String(length=64), nullable=True))
    op.create_index("ix_products_owner_user_id", "products", ["owner_user_id"], unique=False)

    op.add_column("image_sessions", sa.Column("owner_user_id", sa.String(length=64), nullable=True))
    op.create_index("ix_image_sessions_owner_user_id", "image_sessions", ["owner_user_id"], unique=False)

    op.add_column("user_canvas_templates", sa.Column("owner_user_id", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_user_canvas_templates_owner_user_id",
        "user_canvas_templates",
        ["owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_canvas_templates_owner_user_id", table_name="user_canvas_templates")
    op.drop_column("user_canvas_templates", "owner_user_id")

    op.drop_index("ix_image_sessions_owner_user_id", table_name="image_sessions")
    op.drop_column("image_sessions", "owner_user_id")

    op.drop_index("ix_products_owner_user_id", table_name="products")
    op.drop_column("products", "owner_user_id")
