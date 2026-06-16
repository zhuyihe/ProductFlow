"""add audit events ledger

Revision ID: 20260615_0037
Revises: 20260526_0036
Create Date: 2026-06-15
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260615_0037"
down_revision = "20260526_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("actor_username", sa.String(length=255), nullable=True),
        sa.Column("actor_principal_kind", sa.String(length=20), nullable=True),
        sa.Column("subject_user_id", sa.String(length=64), nullable=True),
        sa.Column("subject_username", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("atelier_request_id", sa.String(length=64), nullable=True),
        sa.Column("new_api_request_id", sa.String(length=120), nullable=True),
        sa.Column("new_api_upstream_request_id", sa.String(length=120), nullable=True),
        sa.Column("new_api_log_id", sa.String(length=64), nullable=True),
        sa.Column("new_api_token_id", sa.String(length=64), nullable=True),
        sa.Column("new_api_token_name", sa.String(length=120), nullable=True),
        sa.Column("new_api_token_group", sa.String(length=120), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("provider_name", sa.String(length=120), nullable=True),
        sa.Column("quota", sa.Numeric(18, 6), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("use_time_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(length=80), nullable=True),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("parent_resource_type", sa.String(length=80), nullable=True),
        sa.Column("parent_resource_id", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_subject_created_at", "audit_events", ["subject_user_id", "created_at"])
    op.create_index("ix_audit_events_event_type_created_at", "audit_events", ["event_type", "created_at"])
    op.create_index("ix_audit_events_atelier_request_id", "audit_events", ["atelier_request_id"])
    op.create_index("ix_audit_events_new_api_request_id", "audit_events", ["new_api_request_id"])
    op.create_index("ix_audit_events_resource", "audit_events", ["resource_type", "resource_id"])
    op.create_index("ix_audit_events_status_created_at", "audit_events", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_status_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_resource", table_name="audit_events")
    op.drop_index("ix_audit_events_new_api_request_id", table_name="audit_events")
    op.drop_index("ix_audit_events_atelier_request_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_subject_created_at", table_name="audit_events")
    op.drop_table("audit_events")
