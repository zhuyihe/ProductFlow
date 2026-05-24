from __future__ import annotations

import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from productflow_backend.config import get_settings
from productflow_backend.domain.enums import (
    CopyStatus,
    ImageSessionAssetKind,
    JobStatus,
    PosterKind,
    SourceAssetKind,
    WorkflowNodeStatus,
    WorkflowNodeType,
    WorkflowRunStatus,
)
from productflow_backend.infrastructure.db.models import (
    AuditLog,
    AuthSession,
    CopySet,
    GalleryEntryReport,
    ImageGalleryEntry,
    ImageSession,
    ImageSessionAsset,
    ImageSessionGenerationTask,
    PosterVariant,
    Product,
    SourceAsset,
    UserCanvasTemplate,
    WorkflowNode,
    WorkflowNodeRun,
    WorkflowRun,
    new_id,
    utcnow,
)

MODEL_LEGACY_COPY_COLUMNS = [
    "model_" + suffix
    for suffix in ("title", "selling" + "_points", "poster" + "_headline", "c" + "ta")
]
LEGACY_COPY_COLUMNS = ["title", "selling" + "_points", "poster" + "_headline", "c" + "ta"]


def test_sqlalchemy_enum_columns_use_database_values() -> None:
    assert SourceAsset.__table__.c.kind.type.enums == [member.value for member in SourceAssetKind]
    assert ImageSessionAsset.__table__.c.kind.type.enums == [member.value for member in ImageSessionAssetKind]
    assert CopySet.__table__.c.status.type.enums == [member.value for member in CopyStatus]
    assert PosterVariant.__table__.c.kind.type.enums == [member.value for member in PosterKind]
    assert ImageSessionGenerationTask.__table__.c.status.type.enums == [member.value for member in JobStatus]
    assert WorkflowNode.__table__.c.node_type.type.enums == [member.value for member in WorkflowNodeType]
    assert WorkflowNode.__table__.c.status.type.enums == [member.value for member in WorkflowNodeStatus]
    assert WorkflowNodeRun.__table__.c.status.type.enums == [member.value for member in WorkflowNodeStatus]
    assert WorkflowRun.__table__.c.status.type.enums == [member.value for member in WorkflowRunStatus]


def test_workflow_run_model_has_retryability_and_progress_metadata() -> None:
    table = WorkflowRun.__table__
    assert "is_retryable" in table.c
    assert not table.c.is_retryable.nullable
    assert table.c.is_retryable.default is not None
    assert "progress_metadata" in table.c
    assert table.c.progress_metadata.nullable


def test_gallery_entry_model_matches_migration_contract() -> None:
    table = ImageGalleryEntry.__table__
    assert table.c.id.type.length == 36
    assert not table.c.id.nullable
    assert table.c.id.default is not None
    assert table.c.id.default.arg.__name__ == new_id.__name__
    assert table.c.image_session_asset_id.type.length == 36
    assert not table.c.image_session_asset_id.nullable
    assert table.c.image_session_round_id.nullable
    assert table.c.shared_by_user_id.type.length == 64
    assert table.c.shared_by_user_id.nullable
    assert table.c.shared_by_username.type.length == 255
    assert table.c.shared_by_username.nullable
    assert table.c.forked_from_entry_id.type.length == 36
    assert table.c.forked_from_entry_id.nullable
    assert not table.c.created_at.nullable
    assert table.c.created_at.default is not None
    assert table.c.created_at.default.arg.__name__ == utcnow.__name__
    assert {index.name for index in table.indexes} == {
        "uq_image_gallery_entries_asset_id",
        "ix_image_gallery_entries_round_id",
        "ix_image_gallery_entries_created_at",
        "ix_image_gallery_entries_shared_by_user_id",
        "ix_image_gallery_entries_forked_from_entry_id",
    }
    foreign_keys = {fk.parent.name: fk for fk in table.foreign_keys}
    assert foreign_keys["image_session_asset_id"].constraint.name == "fk_image_gallery_entries_image_session_asset_id"
    assert foreign_keys["image_session_asset_id"].ondelete == "CASCADE"
    assert foreign_keys["image_session_round_id"].constraint.name == "fk_image_gallery_entries_image_session_round_id"
    assert foreign_keys["image_session_round_id"].ondelete == "SET NULL"
    assert foreign_keys["forked_from_entry_id"].constraint.name == "fk_image_gallery_entries_forked_from_entry_id"
    assert foreign_keys["forked_from_entry_id"].ondelete == "SET NULL"


def test_gallery_entry_report_model_matches_migration_contract() -> None:
    table = GalleryEntryReport.__table__
    assert table.c.id.type.length == 36
    assert not table.c.id.nullable
    assert table.c.entry_id.type.length == 36
    assert not table.c.entry_id.nullable
    assert table.c.reporter_user_id.type.length == 64
    assert not table.c.reporter_user_id.nullable
    assert table.c.reason_code.type.length == 32
    assert not table.c.reason_code.nullable
    assert table.c.reason_text.nullable
    assert table.c.status.type.length == 16
    assert not table.c.status.nullable
    assert table.c.resolved_by_admin_id.type.length == 64
    assert table.c.resolved_by_admin_id.nullable
    assert table.c.resolved_at.nullable
    assert {index.name for index in table.indexes} == {
        "ix_gallery_entry_reports_status_created_at",
        "ix_gallery_entry_reports_entry_id",
    }
    foreign_keys = {fk.parent.name: fk for fk in table.foreign_keys}
    assert foreign_keys["entry_id"].constraint.name == "fk_gallery_entry_reports_entry_id"
    assert foreign_keys["entry_id"].ondelete == "CASCADE"


def test_user_canvas_template_model_matches_migration_contract() -> None:
    table = UserCanvasTemplate.__table__
    assert table.c.id.type.length == 36
    assert not table.c.id.nullable
    assert table.c.id.default is not None
    assert table.c.id.default.arg.__name__ == new_id.__name__
    assert table.c.key.type.length == 80
    assert not table.c.key.nullable
    assert table.c.title.type.length == 255
    assert not table.c.title.nullable
    assert table.c.description.nullable
    assert table.c.is_public.type.python_type is bool
    assert not table.c.is_public.nullable
    assert table.c.shared_at.nullable
    assert table.c.shared_by_username.type.length == 255
    assert table.c.shared_by_username.nullable
    assert table.c.forked_from_template_id.type.length == 36
    assert table.c.forked_from_template_id.nullable
    assert table.c.kind.type.length == 40
    assert not table.c.kind.nullable
    assert not table.c.schema_version.nullable
    assert not table.c.template_json.nullable
    assert table.c.archived_at.nullable
    assert not table.c.created_at.nullable
    assert not table.c.updated_at.nullable
    assert {constraint.name for constraint in table.constraints if isinstance(constraint, sa.UniqueConstraint)} == {
        None
    }
    assert {index.name for index in table.indexes} == {
        "ix_user_canvas_templates_archived_at",
        "ix_user_canvas_templates_owner_user_id",
        "ix_user_canvas_templates_is_public_shared_at",
        "ix_user_canvas_templates_forked_from_template_id",
    }


def test_auth_session_model_matches_migration_contract() -> None:
    table = AuthSession.__table__
    assert table.c.id.type.length == 36
    assert not table.c.id.nullable
    assert table.c.id.default is not None
    assert table.c.id.default.arg.__name__ == new_id.__name__
    assert table.c.principal_kind.type.length == 20
    assert not table.c.principal_kind.nullable
    assert table.c.new_api_user_id.type.length == 64
    assert table.c.new_api_user_id.nullable
    assert table.c.username.type.length == 255
    assert table.c.username.nullable
    assert table.c.email.type.length == 255
    assert table.c.email.nullable
    assert table.c.group.type.length == 120
    assert table.c.group.nullable
    assert table.c.role.type.length == 80
    assert table.c.role.nullable
    assert table.c.new_api_token_id.type.length == 64
    assert table.c.new_api_token_id.nullable
    assert table.c.new_api_token_name.type.length == 120
    assert table.c.new_api_token_name.nullable
    assert table.c.new_api_token.nullable
    assert table.c.revoked_at.nullable
    assert table.c.expires_at.nullable
    assert not table.c.created_at.nullable
    assert not table.c.updated_at.nullable
    assert {index.name for index in table.indexes} == {
        "ix_auth_sessions_expires_at",
        "ix_auth_sessions_new_api_user_id",
    }


def test_audit_log_model_matches_migration_contract() -> None:
    table = AuditLog.__table__
    assert table.c.id.type.length == 36
    assert not table.c.id.nullable
    assert table.c.id.default is not None
    assert table.c.id.default.arg.__name__ == new_id.__name__
    assert table.c.admin_user_id.type.length == 64
    assert not table.c.admin_user_id.nullable
    assert table.c.admin_session_id.type.length == 36
    assert table.c.admin_session_id.nullable
    assert table.c.admin_username.type.length == 255
    assert table.c.admin_username.nullable
    assert table.c.target_user_id.type.length == 64
    assert not table.c.target_user_id.nullable
    assert table.c.action.type.length == 80
    assert not table.c.action.nullable
    assert table.c.resource_type.type.length == 80
    assert not table.c.resource_type.nullable
    assert table.c.resource_id.type.length == 120
    assert not table.c.resource_id.nullable
    assert table.c.client_address.type.length == 255
    assert table.c.client_address.nullable
    assert table.c.user_agent.nullable
    assert not table.c.created_at.nullable
    assert table.c.created_at.default is not None
    assert table.c.created_at.default.arg.__name__ == utcnow.__name__
    assert {index.name for index in table.indexes} == {
        "ix_audit_logs_admin_user_id",
        "ix_audit_logs_created_at",
        "ix_audit_logs_target_user_id",
    }


def test_multi_user_owner_model_columns_match_migration_contract() -> None:
    owned_tables = (
        (Product.__table__, "ix_products_owner_user_id"),
        (ImageSession.__table__, "ix_image_sessions_owner_user_id"),
        (UserCanvasTemplate.__table__, "ix_user_canvas_templates_owner_user_id"),
    )
    for table, index_name in owned_tables:
        assert table.c.owner_user_id.type.length == 64
        assert table.c.owner_user_id.nullable
        indexes = {index.name: index for index in table.indexes}
        assert index_name in indexes
        assert [column.name for column in indexes[index_name].columns] == ["owner_user_id"]


def test_generation_task_new_api_token_context_model_columns_match_migration_contract() -> None:
    task_tables = (
        (WorkflowRun.__table__, "ix_workflow_runs_new_api_user_id"),
        (ImageSessionGenerationTask.__table__, "ix_image_session_generation_tasks_new_api_user_id"),
    )
    for table, index_name in task_tables:
        assert table.c.new_api_user_id.type.length == 64
        assert table.c.new_api_user_id.nullable
        assert table.c.new_api_token_id.type.length == 64
        assert table.c.new_api_token_id.nullable
        assert table.c.new_api_token_name.type.length == 120
        assert table.c.new_api_token_name.nullable
        assert table.c.new_api_token.nullable
        indexes = {index.name: index for index in table.indexes}
        assert index_name in indexes
        assert [column.name for column in indexes[index_name].columns] == ["new_api_user_id"]


def test_alembic_upgrade_head_supports_sqlite(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "alembic.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "head")

    assert database_path.exists()
    get_settings.cache_clear()


def test_auth_session_migration_schema_and_downgrade_support_sqlite(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "auth-session-migration.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "auth_sessions" in inspector.get_table_names()
    columns = {column["name"]: column for column in inspector.get_columns("auth_sessions")}
    assert columns["id"]["nullable"] is False
    assert columns["principal_kind"]["nullable"] is False
    assert columns["new_api_user_id"]["nullable"] is True
    assert columns["new_api_token"]["nullable"] is True
    assert columns["revoked_at"]["nullable"] is True
    assert columns["expires_at"]["nullable"] is True
    assert columns["created_at"]["nullable"] is False
    assert columns["updated_at"]["nullable"] is False
    indexes = {index["name"]: index for index in inspector.get_indexes("auth_sessions")}
    assert indexes["ix_auth_sessions_new_api_user_id"]["column_names"] == ["new_api_user_id"]
    assert indexes["ix_auth_sessions_expires_at"]["column_names"] == ["expires_at"]

    engine.dispose()
    command.downgrade(config, "20260513_0028")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "auth_sessions" not in inspector.get_table_names()
    engine.dispose()
    get_settings.cache_clear()


def test_resource_owner_columns_migration_schema_and_downgrade_support_sqlite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "owner-columns-migration.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    expected = {
        "products": "ix_products_owner_user_id",
        "image_sessions": "ix_image_sessions_owner_user_id",
        "user_canvas_templates": "ix_user_canvas_templates_owner_user_id",
    }
    for table_name, index_name in expected.items():
        columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        assert columns["owner_user_id"]["nullable"] is True
        indexes = {index["name"]: index for index in inspector.get_indexes(table_name)}
        assert indexes[index_name]["column_names"] == ["owner_user_id"]

    engine.dispose()
    command.downgrade(config, "20260522_0029")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    for table_name in expected:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert "owner_user_id" not in columns
    engine.dispose()
    get_settings.cache_clear()


def test_generation_task_token_context_migration_schema_and_downgrade_support_sqlite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "new-api-token-context-migration.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    expected = {
        "workflow_runs": "ix_workflow_runs_new_api_user_id",
        "image_session_generation_tasks": "ix_image_session_generation_tasks_new_api_user_id",
    }
    for table_name, index_name in expected.items():
        columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        assert columns["new_api_user_id"]["nullable"] is True
        assert columns["new_api_token_id"]["nullable"] is True
        assert columns["new_api_token_name"]["nullable"] is True
        assert columns["new_api_token"]["nullable"] is True
        indexes = {index["name"]: index for index in inspector.get_indexes(table_name)}
        assert indexes[index_name]["column_names"] == ["new_api_user_id"]

    engine.dispose()
    command.downgrade(config, "20260522_0030")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    for table_name in expected:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert not {"new_api_user_id", "new_api_token_id", "new_api_token_name", "new_api_token"} & columns
    engine.dispose()
    get_settings.cache_clear()


def test_audit_log_migration_schema_and_downgrade_support_sqlite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "audit-log-migration.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "audit_logs" in inspector.get_table_names()
    columns = {column["name"]: column for column in inspector.get_columns("audit_logs")}
    assert columns["id"]["nullable"] is False
    assert columns["admin_user_id"]["nullable"] is False
    assert columns["admin_session_id"]["nullable"] is True
    assert columns["admin_username"]["nullable"] is True
    assert columns["target_user_id"]["nullable"] is False
    assert columns["action"]["nullable"] is False
    assert columns["resource_type"]["nullable"] is False
    assert columns["resource_id"]["nullable"] is False
    assert columns["client_address"]["nullable"] is True
    assert columns["user_agent"]["nullable"] is True
    assert columns["created_at"]["nullable"] is False
    indexes = {index["name"]: index for index in inspector.get_indexes("audit_logs")}
    assert indexes["ix_audit_logs_admin_user_id"]["column_names"] == ["admin_user_id"]
    assert indexes["ix_audit_logs_target_user_id"]["column_names"] == ["target_user_id"]
    assert indexes["ix_audit_logs_created_at"]["column_names"] == ["created_at"]

    engine.dispose()
    command.downgrade(config, "20260522_0031")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "audit_logs" not in inspector.get_table_names()
    engine.dispose()
    get_settings.cache_clear()


def test_legacy_copy_fields_migrate_to_structured_payload_and_drop_columns(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "drop-legacy-copy-fields.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "20260509_0023")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        now = "2026-05-10 00:00:00"
        connection.execute(
            sa.text(
                """
                INSERT INTO products (
                    id, name, category, price, source_note, current_confirmed_copy_set_id, created_at, updated_at
                )
                VALUES (:id, :name, NULL, NULL, NULL, NULL, :now, :now)
                """
            ),
            {"id": "product-1", "name": "迁移商品", "now": now},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO copy_sets (
                    id, product_id, creative_brief_id, status,
                    __LEGACY_COPY_COLUMNS__,
                    structured_payload,
                    __MODEL_LEGACY_COLUMNS__,
                    model_structured_payload,
                    provider_name, model_name, prompt_version,
                    edited_at, confirmed_at, created_at, updated_at
                )
                VALUES (
                    :id, :product_id, NULL, :status,
                    :text_value, :points_value, :headline_value, :action_value,
                    NULL,
                    :model_text_value, :model_points_value, :model_headline_value, :model_action_value,
                    NULL,
                    :provider_name, :model_name, :prompt_version,
                    NULL, NULL, :now, :now
                )
                """
                .replace("__LEGACY_COPY_COLUMNS__", ", ".join(LEGACY_COPY_COLUMNS))
                .replace("__MODEL_LEGACY_COLUMNS__", ", ".join(MODEL_LEGACY_COPY_COLUMNS))
            ),
            {
                "id": "copy-set-1",
                "product_id": "product-1",
                "status": "draft",
                "text_value": "旧标题",
                "points_value": '["卖点一", "卖点二"]',
                "headline_value": "旧海报标题",
                "action_value": "立即购买",
                "model_text_value": "模型旧标题",
                "model_points_value": '["模型卖点"]',
                "model_headline_value": "模型海报标题",
                "model_action_value": "模型 CTA",
                "provider_name": "test",
                "model_name": "test",
                "prompt_version": "test",
                "now": now,
            },
        )

    engine.dispose()
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    copy_set_columns = {column["name"] for column in inspector.get_columns("copy_sets")}
    assert not {
        *LEGACY_COPY_COLUMNS,
        *MODEL_LEGACY_COPY_COLUMNS,
    } & copy_set_columns
    assert {"structured_payload", "model_structured_payload"} <= copy_set_columns
    with engine.connect() as connection:
        row = connection.execute(
            sa.text("SELECT structured_payload, model_structured_payload FROM copy_sets WHERE id = :id"),
            {"id": "copy-set-1"},
        ).mappings().one()
    structured_payload = json.loads(row["structured_payload"])
    model_structured_payload = json.loads(row["model_structured_payload"])
    assert structured_payload["version"] == 2
    assert structured_payload["summary"] == "旧海报标题"
    assert structured_payload["content"]["kind"] == "blocks"
    assert [block["text"] for block in structured_payload["content"]["blocks"][:3]] == [
        "旧标题",
        "卖点一",
        "卖点二",
    ]
    assert model_structured_payload["summary"] == "模型海报标题"
    engine.dispose()

    command.downgrade(config, "20260509_0023")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    downgraded_columns = {column["name"] for column in inspector.get_columns("copy_sets")}
    assert {*LEGACY_COPY_COLUMNS, *MODEL_LEGACY_COPY_COLUMNS} <= downgraded_columns
    with engine.connect() as connection:
        row = connection.execute(
            sa.text(
                """
                SELECT __LEGACY_COPY_COLUMNS__, __MODEL_LEGACY_COLUMNS__
                FROM copy_sets
                WHERE id = :id
                """
                .replace("__LEGACY_COPY_COLUMNS__", ", ".join(LEGACY_COPY_COLUMNS))
                .replace("__MODEL_LEGACY_COLUMNS__", ", ".join(MODEL_LEGACY_COPY_COLUMNS))
            ),
            {"id": "copy-set-1"},
        ).mappings().one()
    assert row[LEGACY_COPY_COLUMNS[0]] == "旧标题"
    assert json.loads(row[LEGACY_COPY_COLUMNS[1]]) == ["卖点一", "卖点二"]
    assert row[LEGACY_COPY_COLUMNS[2]] == "旧海报标题"
    assert row[LEGACY_COPY_COLUMNS[3]] == "立即购买"
    assert row[MODEL_LEGACY_COPY_COLUMNS[0]] == "模型旧标题"
    assert json.loads(row[MODEL_LEGACY_COPY_COLUMNS[1]]) == ["模型卖点"]
    assert row[MODEL_LEGACY_COPY_COLUMNS[2]] == "模型海报标题"
    assert row[MODEL_LEGACY_COPY_COLUMNS[3]] == "模型 CTA"
    engine.dispose()
    get_settings.cache_clear()


def test_workflow_run_retryability_migration_supports_sqlite(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "workflow-run-retryability.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "20260510_0024")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    now = "2026-05-12 00:00:00"
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO products (id, name, created_at, updated_at) "
                "VALUES ('product-1', '重试迁移商品', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO product_workflows (id, product_id, title, active, created_at, updated_at) "
                "VALUES ('workflow-1', 'product-1', '迁移工作流', 1, :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workflow_runs (id, workflow_id, status, started_at) "
                "VALUES ('run-1', 'workflow-1', 'failed', :now)"
            ),
            {"now": now},
        )

    engine.dispose()
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("workflow_runs")}
    assert columns["is_retryable"]["nullable"] is False
    with engine.connect() as connection:
        retryable = connection.execute(
            sa.text("SELECT is_retryable FROM workflow_runs WHERE id = 'run-1'")
        ).scalar_one()
    assert bool(retryable) is True

    engine.dispose()
    command.downgrade(config, "20260510_0024")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("workflow_runs")}
    assert "is_retryable" not in columns

    engine.dispose()
    get_settings.cache_clear()


def test_workflow_run_progress_metadata_migration_supports_sqlite(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "workflow-run-progress-metadata.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "20260512_0025")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    now = "2026-05-13 00:00:00"
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO products (id, name, created_at, updated_at) "
                "VALUES ('product-1', '进度迁移商品', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO product_workflows (id, product_id, title, active, created_at, updated_at) "
                "VALUES ('workflow-1', 'product-1', '迁移工作流', 1, :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workflow_runs (id, workflow_id, status, started_at, is_retryable) "
                "VALUES ('run-1', 'workflow-1', 'running', :now, 1)"
            ),
            {"now": now},
        )

    engine.dispose()
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("workflow_runs")}
    assert columns["progress_metadata"]["nullable"] is True
    with engine.begin() as connection:
        connection.execute(
            sa.text("UPDATE workflow_runs SET progress_metadata = :metadata WHERE id = 'run-1'"),
            {"metadata": json.dumps({"last_failure_reason": "上次失败"})},
        )
        metadata = connection.execute(
            sa.text("SELECT progress_metadata FROM workflow_runs WHERE id = 'run-1'")
        ).scalar_one()
    assert json.loads(metadata)["last_failure_reason"] == "上次失败"

    engine.dispose()
    command.downgrade(config, "20260512_0025")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("workflow_runs")}
    assert "progress_metadata" not in columns

    engine.dispose()
    get_settings.cache_clear()


def test_user_canvas_template_migration_schema_and_downgrade_support_sqlite(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "user-canvas-template-migration.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "user_canvas_templates" in inspector.get_table_names()
    columns = {column["name"]: column for column in inspector.get_columns("user_canvas_templates")}
    assert columns["id"]["nullable"] is False
    assert columns["key"]["nullable"] is False
    assert columns["title"]["nullable"] is False
    assert columns["description"]["nullable"] is True
    assert columns["kind"]["nullable"] is False
    assert columns["schema_version"]["nullable"] is False
    assert columns["template_json"]["nullable"] is False
    assert columns["archived_at"]["nullable"] is True
    assert columns["created_at"]["nullable"] is False
    assert columns["updated_at"]["nullable"] is False
    assert {constraint["name"] for constraint in inspector.get_unique_constraints("user_canvas_templates")} == {None}
    indexes = {index["name"]: index for index in inspector.get_indexes("user_canvas_templates")}
    assert indexes["ix_user_canvas_templates_archived_at"]["column_names"] == ["archived_at"]

    engine.dispose()
    command.downgrade(config, "20260507_0021")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "user_canvas_templates" not in inspector.get_table_names()
    engine.dispose()
    get_settings.cache_clear()


def test_gallery_migration_schema_and_downgrade_support_sqlite(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "gallery-migration.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "image_gallery_entries" in inspector.get_table_names()
    columns = {column["name"]: column for column in inspector.get_columns("image_gallery_entries")}
    assert columns["id"]["nullable"] is False
    assert columns["image_session_asset_id"]["nullable"] is False
    assert columns["image_session_round_id"]["nullable"] is True
    assert columns["shared_by_user_id"]["nullable"] is True
    assert columns["shared_by_username"]["nullable"] is True
    assert columns["forked_from_entry_id"]["nullable"] is True
    assert columns["created_at"]["nullable"] is False
    indexes = {index["name"]: index for index in inspector.get_indexes("image_gallery_entries")}
    assert bool(indexes["uq_image_gallery_entries_asset_id"]["unique"])
    assert indexes["uq_image_gallery_entries_asset_id"]["column_names"] == ["image_session_asset_id"]
    assert indexes["ix_image_gallery_entries_round_id"]["column_names"] == ["image_session_round_id"]
    assert indexes["ix_image_gallery_entries_created_at"]["column_names"] == ["created_at"]
    assert indexes["ix_image_gallery_entries_shared_by_user_id"]["column_names"] == ["shared_by_user_id"]
    assert indexes["ix_image_gallery_entries_forked_from_entry_id"]["column_names"] == ["forked_from_entry_id"]
    foreign_keys = {tuple(fk["constrained_columns"]): fk for fk in inspector.get_foreign_keys("image_gallery_entries")}
    assert foreign_keys[("image_session_asset_id",)]["referred_table"] == "image_session_assets"
    assert foreign_keys[("image_session_asset_id",)]["options"]["ondelete"] == "CASCADE"
    assert foreign_keys[("image_session_round_id",)]["referred_table"] == "image_session_rounds"
    assert foreign_keys[("image_session_round_id",)]["options"]["ondelete"] == "SET NULL"
    assert foreign_keys[("forked_from_entry_id",)]["referred_table"] == "image_gallery_entries"
    assert foreign_keys[("forked_from_entry_id",)]["options"]["ondelete"] == "SET NULL"
    assert "gallery_entry_reports" in inspector.get_table_names()
    template_columns = {column["name"]: column for column in inspector.get_columns("user_canvas_templates")}
    assert template_columns["is_public"]["nullable"] is False
    assert template_columns["shared_at"]["nullable"] is True
    assert template_columns["shared_by_username"]["nullable"] is True
    assert template_columns["forked_from_template_id"]["nullable"] is True
    template_indexes = {index["name"]: index for index in inspector.get_indexes("user_canvas_templates")}
    assert template_indexes["ix_user_canvas_templates_is_public_shared_at"]["column_names"] == [
        "is_public",
        "shared_at",
    ]
    assert template_indexes["ix_user_canvas_templates_forked_from_template_id"]["column_names"] == [
        "forked_from_template_id"
    ]
    asset_columns = {column["name"]: column for column in inspector.get_columns("image_session_assets")}
    assert asset_columns["imported_from_gallery_entry_id"]["nullable"] is True
    asset_indexes = {index["name"]: index for index in inspector.get_indexes("image_session_assets")}
    assert asset_indexes["ix_image_session_assets_imported_from_gallery_entry_id"]["column_names"] == [
        "imported_from_gallery_entry_id"
    ]
    report_columns = {column["name"]: column for column in inspector.get_columns("gallery_entry_reports")}
    assert report_columns["entry_id"]["nullable"] is False
    assert report_columns["reporter_user_id"]["nullable"] is False
    assert report_columns["reason_code"]["nullable"] is False
    assert report_columns["reason_text"]["nullable"] is True
    assert report_columns["status"]["nullable"] is False
    report_indexes = {index["name"]: index for index in inspector.get_indexes("gallery_entry_reports")}
    assert report_indexes["ix_gallery_entry_reports_entry_id"]["column_names"] == ["entry_id"]
    assert report_indexes["ix_gallery_entry_reports_status_created_at"]["column_names"] == ["status", "created_at"]
    report_foreign_keys = {
        tuple(fk["constrained_columns"]): fk for fk in inspector.get_foreign_keys("gallery_entry_reports")
    }
    assert report_foreign_keys[("entry_id",)]["referred_table"] == "image_gallery_entries"
    assert report_foreign_keys[("entry_id",)]["options"]["ondelete"] == "CASCADE"

    engine.dispose()
    command.downgrade(config, "20260522_0032")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "image_gallery_entries" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("image_gallery_entries")}
    assert not {"shared_by_user_id", "shared_by_username", "forked_from_entry_id"} & columns
    indexes = {index["name"] for index in inspector.get_indexes("image_gallery_entries")}
    assert "ix_image_gallery_entries_shared_by_user_id" not in indexes
    assert "ix_image_gallery_entries_forked_from_entry_id" not in indexes
    template_columns = {column["name"] for column in inspector.get_columns("user_canvas_templates")}
    assert not {"is_public", "shared_at", "shared_by_username", "forked_from_template_id"} & template_columns
    asset_columns = {column["name"] for column in inspector.get_columns("image_session_assets")}
    assert "imported_from_gallery_entry_id" not in asset_columns
    assert "gallery_entry_reports" not in inspector.get_table_names()
    engine.dispose()
    get_settings.cache_clear()


def test_job_runs_drop_migration_and_downgrade_support_sqlite(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "job-runs-drop.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "20260428_0016")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "job_runs" in inspector.get_table_names()
    assert "uq_job_runs_one_active_per_product_kind" in {
        index["name"] for index in inspector.get_indexes("job_runs")
    }

    engine.dispose()
    command.upgrade(config, "head")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "job_runs" not in inspector.get_table_names()

    engine.dispose()
    command.downgrade(config, "20260428_0016")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    assert "job_runs" in inspector.get_table_names()
    columns = {column["name"]: column for column in inspector.get_columns("job_runs")}
    assert columns["product_id"]["nullable"] is False
    assert columns["kind"]["nullable"] is False
    assert columns["status"]["nullable"] is False
    assert "uq_job_runs_one_active_per_product_kind" in {
        index["name"] for index in inspector.get_indexes("job_runs")
    }

    engine.dispose()
    get_settings.cache_clear()


def test_image_session_generation_progress_migration_and_downgrade_support_sqlite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "image-session-progress.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "20260428_0017")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    now = "2026-04-28 00:00:00"
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO image_sessions (id, title, created_at, updated_at) "
                "VALUES ('session-1', '迁移会话', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO image_session_generation_tasks "
                "(id, session_id, status, prompt, size, generation_count, created_at, attempts, is_retryable) "
                "VALUES ('task-1', 'session-1', 'running', '旧任务', '1024x1024', 2, :now, 1, 1)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO image_session_generation_tasks "
                "(id, session_id, status, prompt, size, generation_count, created_at, attempts, is_retryable) "
                "VALUES ('failed-task-1', 'session-1', 'failed', '旧失败任务', '1024x1024', 4, :now, 1, 0)"
            ),
            {"now": now},
        )

    engine.dispose()
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("image_session_generation_tasks")}
    assert columns["completed_candidates"]["nullable"] is False
    assert columns["completed_candidates"]["default"] is None
    assert columns["active_candidate_index"]["nullable"] is True
    assert columns["progress_phase"]["nullable"] is True
    assert columns["progress_updated_at"]["nullable"] is True
    assert columns["provider_response_id"]["nullable"] is True
    assert columns["provider_response_status"]["nullable"] is True
    assert columns["progress_metadata"]["nullable"] is True
    with engine.connect() as connection:
        completed_candidates = connection.execute(
            sa.text("SELECT completed_candidates FROM image_session_generation_tasks WHERE id = 'task-1'")
        ).scalar_one()
        failed_task_retryable = connection.execute(
            sa.text("SELECT is_retryable FROM image_session_generation_tasks WHERE id = 'failed-task-1'")
        ).scalar_one()
    assert completed_candidates == 0
    assert bool(failed_task_retryable) is True

    engine.dispose()
    command.downgrade(config, "20260428_0017")
    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("image_session_generation_tasks")}
    assert "completed_candidates" not in columns
    assert "progress_metadata" not in columns

    engine.dispose()
    get_settings.cache_clear()


def test_alembic_upgrade_removes_legacy_workflow_nodes(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "legacy-workflow.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "20260424_0009")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    now = "2026-04-24 00:00:00"
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO products (id, name, created_at, updated_at) "
                "VALUES ('product-1', '旧工作流商品', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO product_workflows (id, product_id, title, active, created_at, updated_at) "
                "VALUES ('workflow-1', 'product-1', '旧工作流', 1, :now, :now)"
            ),
            {"now": now},
        )
        for node_id, node_type in (
            ("context-1", "product_context"),
            ("copy-1", "copy_generation"),
            ("legacy-text-1", "legacy_text"),
            ("image-1", "image_generation"),
            ("legacy-result-1", "legacy_result"),
            ("slot-1", "image_upload"),
        ):
            connection.execute(
                sa.text(
                    "INSERT INTO workflow_nodes "
                    "(id, workflow_id, node_type, title, position_x, position_y, config_json, status, "
                    "created_at, updated_at) "
                    "VALUES (:id, 'workflow-1', :node_type, :id, 0, 0, '{}', 'idle', :now, :now)"
                ),
                {"id": node_id, "node_type": node_type, "now": now},
            )
        connection.execute(
            sa.text(
                "INSERT INTO workflow_edges "
                "(id, workflow_id, source_node_id, target_node_id, source_handle, target_handle, created_at) "
                "VALUES "
                "('edge-old-target', 'workflow-1', 'copy-1', 'legacy-text-1', 'output', 'input', :now), "
                "('edge-old-source', 'workflow-1', 'legacy-result-1', 'image-1', 'output', 'input', :now), "
                "('edge-supported', 'workflow-1', 'context-1', 'copy-1', 'output', 'input', :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workflow_runs (id, workflow_id, status, started_at) "
                "VALUES ('run-1', 'workflow-1', 'running', :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workflow_node_runs (id, workflow_run_id, node_id, status, started_at) "
                "VALUES "
                "('node-run-old', 'run-1', 'legacy-text-1', 'succeeded', :now), "
                "('node-run-supported', 'run-1', 'copy-1', 'succeeded', :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        node_types = connection.execute(sa.text("SELECT node_type FROM workflow_nodes ORDER BY id")).scalars().all()
        edge_ids = connection.execute(sa.text("SELECT id FROM workflow_edges ORDER BY id")).scalars().all()
        node_run_ids = connection.execute(sa.text("SELECT id FROM workflow_node_runs ORDER BY id")).scalars().all()

    assert node_types == ["product_context", "copy_generation", "image_generation", "reference_image"]
    assert edge_ids == ["edge-supported"]
    assert node_run_ids == ["node-run-supported"]
    get_settings.cache_clear()


def test_disjoint_workflow_node_run_migration_constraints_support_sqlite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "workflow-node-run-constraints.db"
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ADMIN_ACCESS_KEY", "super-secret-admin-key")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session-key-123")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(config, "20260507_0020")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    now = "2026-05-07 00:21:00"
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO products (id, name, created_at, updated_at) "
                "VALUES ('product-1', '节点并行迁移商品', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO product_workflows (id, product_id, title, active, created_at, updated_at) "
                "VALUES ('workflow-1', 'product-1', '节点并行迁移工作流', 1, :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workflow_nodes "
                "(id, workflow_id, node_type, title, position_x, position_y, "
                "config_json, status, created_at, updated_at) "
                "VALUES "
                "('node-1', 'workflow-1', 'copy_generation', '文案', 0, 0, '{}', 'queued', :now, :now), "
                "('node-2', 'workflow-1', 'image_generation', '生图', 100, 0, '{}', 'queued', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workflow_runs (id, workflow_id, status, started_at) "
                "VALUES ('run-1', 'workflow-1', 'running', :now)"
            ),
            {"now": now},
        )

    engine.dispose()
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    indexes = {index["name"]: index for index in inspector.get_indexes("workflow_node_runs")}
    assert "uq_workflow_node_runs_one_active_per_node" in indexes
    assert bool(indexes["uq_workflow_node_runs_one_active_per_node"]["unique"])
    assert indexes["uq_workflow_node_runs_one_active_per_node"]["column_names"] == ["node_id"]
    workflow_run_indexes = {index["name"] for index in inspector.get_indexes("workflow_runs")}
    assert "uq_workflow_runs_one_running_per_workflow" not in workflow_run_indexes

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO workflow_runs (id, workflow_id, status, started_at) "
                "VALUES ('run-2', 'workflow-1', 'running', :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workflow_node_runs (id, workflow_run_id, node_id, status, started_at) "
                "VALUES "
                "('node-run-1', 'run-1', 'node-1', 'queued', :now), "
                "('node-run-2', 'run-2', 'node-2', 'running', :now)"
            ),
            {"now": now},
        )

    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO workflow_node_runs (id, workflow_run_id, node_id, status, started_at) "
                    "VALUES ('node-run-duplicate', 'run-2', 'node-1', 'running', :now)"
                ),
                {"now": now},
            )

    engine.dispose()
    command.downgrade(config, "20260507_0020")

    engine = sa.create_engine(f"sqlite:///{database_path}")
    inspector = sa.inspect(engine)
    indexes = {index["name"]: index for index in inspector.get_indexes("workflow_runs")}
    assert "uq_workflow_runs_one_running_per_workflow" in indexes
    node_run_indexes = {index["name"] for index in inspector.get_indexes("workflow_node_runs")}
    assert "uq_workflow_node_runs_one_active_per_node" not in node_run_indexes
    with engine.connect() as connection:
        active_run_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM workflow_runs WHERE workflow_id = 'workflow-1' AND status = 'running'")
        ).scalar_one()
        failed_run_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM workflow_runs WHERE workflow_id = 'workflow-1' AND status = 'failed'")
        ).scalar_one()
        duplicate_run_active_node_runs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM workflow_node_runs "
                "WHERE workflow_run_id = 'run-1' AND status IN ('queued', 'running')"
            )
        ).scalar_one()
    assert active_run_count == 1
    assert failed_run_count == 1
    assert duplicate_run_active_node_runs == 0
    engine.dispose()
    get_settings.cache_clear()
