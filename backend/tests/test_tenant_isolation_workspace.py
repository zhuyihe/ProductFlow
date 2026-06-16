from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from fastapi.testclient import TestClient
from helpers import _login

from productflow_backend.infrastructure.db.models import ImageSession, Product


def _create_client():
    from productflow_backend.presentation.api import create_app

    return TestClient(create_app())


def test_admin_workspace_products_are_self_scoped(configured_env: Path, db_session) -> None:
    client = _create_client()
    db_session.add_all(
        [
            Product(id="admin-product", owner_user_id="admin-user", name="Admin Product"),
            Product(id="other-product", owner_user_id="other-user", name="Other Product"),
        ]
    )
    db_session.commit()

    engine = db_session.get_bind()
    with engine.begin() as connection:
        connection.execute(sa.text("PRAGMA ignore_check_constraints=ON"))
        connection.execute(
            sa.text(
                "INSERT INTO products (id, owner_user_id, name, created_at, updated_at) "
                "VALUES ('legacy-product', NULL, 'Legacy Product', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(sa.text("PRAGMA ignore_check_constraints=OFF"))

    _login(client, user_id="admin-user", username="admin", role="10")
    listed = client.get("/api/products")

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert [item["id"] for item in payload["items"]] == ["admin-product"]

    other_detail = client.get("/api/products/other-product")
    assert other_detail.status_code == 404

    legacy_detail = client.get("/api/products/legacy-product")
    assert legacy_detail.status_code == 404


def test_admin_workspace_image_sessions_are_self_scoped(configured_env: Path, db_session) -> None:
    client = _create_client()
    db_session.add_all(
        [
            ImageSession(id="admin-session", owner_user_id="admin-user", title="Admin Session"),
            ImageSession(id="other-session", owner_user_id="other-user", title="Other Session"),
        ]
    )
    db_session.commit()

    engine = db_session.get_bind()
    with engine.begin() as connection:
        connection.execute(sa.text("PRAGMA ignore_check_constraints=ON"))
        connection.execute(
            sa.text(
                "INSERT INTO image_sessions (id, owner_user_id, title, created_at, updated_at) "
                "VALUES ('legacy-session', NULL, 'Legacy Session', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(sa.text("PRAGMA ignore_check_constraints=OFF"))

    _login(client, user_id="admin-user", username="admin", role="10")
    listed = client.get("/api/image-sessions")

    assert listed.status_code == 200
    payload = listed.json()
    assert [item["id"] for item in payload["items"]] == ["admin-session"]

    other_detail = client.get("/api/image-sessions/other-session")
    assert other_detail.status_code == 404

    legacy_detail = client.get("/api/image-sessions/legacy-session")
    assert legacy_detail.status_code == 404


def test_user_workspace_cannot_read_other_users_records(configured_env: Path, db_session) -> None:
    client = _create_client()
    db_session.add_all(
        [
            Product(id="user-product", owner_user_id="user-a", name="User Product"),
            Product(id="other-product", owner_user_id="user-b", name="Other Product"),
            ImageSession(id="user-session", owner_user_id="user-a", title="User Session"),
            ImageSession(id="other-session", owner_user_id="user-b", title="Other Session"),
        ]
    )
    db_session.commit()

    _login(client, user_id="user-a", username="alice", role="1")

    products = client.get("/api/products")
    assert products.status_code == 200
    assert [item["id"] for item in products.json()["items"]] == ["user-product"]
    assert client.get("/api/products/other-product").status_code == 404

    image_sessions = client.get("/api/image-sessions")
    assert image_sessions.status_code == 200
    assert [item["id"] for item in image_sessions.json()["items"]] == ["user-session"]
    assert client.get("/api/image-sessions/other-session").status_code == 404


def test_workspace_session_without_new_api_user_id_fails_closed(configured_env: Path) -> None:
    client = _create_client()

    _login(client, user_id="", username="bootstrap-admin", role="10")
    response = client.get("/api/products")

    assert response.status_code == 500
    assert response.json() == {"detail": "Invalid authenticated principal"}
