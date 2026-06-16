"""add owner not-null check constraints

Revision ID: 20260616_0038
Revises: 20260615_0037
Create Date: 2026-06-16
"""

from __future__ import annotations

from alembic import op

revision = "20260616_0038"
down_revision = "20260615_0037"
branch_labels = None
depends_on = None

OWNER_CHECK_CONSTRAINTS = (
    ("products", "ck_products_owner_user_id_not_null"),
    ("image_sessions", "ck_image_sessions_owner_user_id_not_null"),
    ("user_canvas_templates", "ck_user_canvas_templates_owner_user_id_not_null"),
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.execute("PRAGMA ignore_check_constraints=ON")
    for table_name, constraint_name in OWNER_CHECK_CONSTRAINTS:
        if _is_postgresql():
            op.execute(
                f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} CHECK (owner_user_id IS NOT NULL) NOT VALID"
            )
            continue
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_check_constraint(constraint_name, "owner_user_id IS NOT NULL")
    if op.get_bind().dialect.name == "sqlite":
        op.execute("PRAGMA ignore_check_constraints=OFF")


def downgrade() -> None:
    for table_name, constraint_name in reversed(OWNER_CHECK_CONSTRAINTS):
        if _is_postgresql():
            op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")
            continue
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(constraint_name, type_="check")
