"""add shared author fields to image gallery entries

Revision ID: 20260524_0033
Revises: 20260522_0032
Create Date: 2026-05-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260524_0033"
down_revision = "20260522_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("image_gallery_entries") as batch_op:
        batch_op.add_column(sa.Column("shared_by_user_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("shared_by_username", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column(
                "forked_from_entry_id",
                sa.String(length=36),
                sa.ForeignKey(
                    "image_gallery_entries.id",
                    name="fk_image_gallery_entries_forked_from_entry_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            )
        )
    op.create_index(
        "ix_image_gallery_entries_shared_by_user_id",
        "image_gallery_entries",
        ["shared_by_user_id"],
    )
    op.create_index(
        "ix_image_gallery_entries_forked_from_entry_id",
        "image_gallery_entries",
        ["forked_from_entry_id"],
    )
    with op.batch_alter_table("user_canvas_templates") as batch_op:
        batch_op.add_column(sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("shared_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("shared_by_username", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column(
                "forked_from_template_id",
                sa.String(length=36),
                sa.ForeignKey(
                    "user_canvas_templates.id",
                    name="fk_user_canvas_templates_forked_from_template_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            )
        )
    op.create_index(
        "ix_user_canvas_templates_is_public_shared_at",
        "user_canvas_templates",
        ["is_public", "shared_at"],
    )
    op.create_index(
        "ix_user_canvas_templates_forked_from_template_id",
        "user_canvas_templates",
        ["forked_from_template_id"],
    )
    with op.batch_alter_table("image_session_assets") as batch_op:
        batch_op.add_column(
            sa.Column(
                "imported_from_gallery_entry_id",
                sa.String(length=36),
                sa.ForeignKey(
                    "image_gallery_entries.id",
                    name="fk_image_session_assets_imported_from_gallery_entry_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            )
        )
    op.create_index(
        "ix_image_session_assets_imported_from_gallery_entry_id",
        "image_session_assets",
        ["imported_from_gallery_entry_id"],
    )
    op.create_table(
        "gallery_entry_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("reporter_user_id", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("resolved_by_admin_id", sa.String(length=64), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["image_gallery_entries.id"],
            name="fk_gallery_entry_reports_entry_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_gallery_entry_reports_status_created_at",
        "gallery_entry_reports",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_gallery_entry_reports_entry_id",
        "gallery_entry_reports",
        ["entry_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_image_session_assets_imported_from_gallery_entry_id", table_name="image_session_assets")
    with op.batch_alter_table("image_session_assets") as batch_op:
        batch_op.drop_column("imported_from_gallery_entry_id")
    op.drop_index("ix_user_canvas_templates_forked_from_template_id", table_name="user_canvas_templates")
    op.drop_index("ix_user_canvas_templates_is_public_shared_at", table_name="user_canvas_templates")
    with op.batch_alter_table("user_canvas_templates") as batch_op:
        batch_op.drop_column("forked_from_template_id")
        batch_op.drop_column("shared_by_username")
        batch_op.drop_column("shared_at")
        batch_op.drop_column("is_public")
    op.drop_index("ix_gallery_entry_reports_entry_id", table_name="gallery_entry_reports")
    op.drop_index("ix_gallery_entry_reports_status_created_at", table_name="gallery_entry_reports")
    op.drop_table("gallery_entry_reports")
    op.drop_index("ix_image_gallery_entries_forked_from_entry_id", table_name="image_gallery_entries")
    op.drop_index("ix_image_gallery_entries_shared_by_user_id", table_name="image_gallery_entries")
    with op.batch_alter_table("image_gallery_entries") as batch_op:
        batch_op.drop_column("forked_from_entry_id")
        batch_op.drop_column("shared_by_username")
        batch_op.drop_column("shared_by_user_id")
