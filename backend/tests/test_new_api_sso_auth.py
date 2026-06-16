from __future__ import annotations

from fastapi.testclient import TestClient
from helpers import _login, _make_demo_image_bytes, _unlock_settings
from sqlalchemy import select

from productflow_backend.application import auth_sessions
from productflow_backend.application.auth_sessions import NewApiSessionClaims, create_new_api_user_session
from productflow_backend.infrastructure.db.models import AppSetting, AuditLog, AuthSession
from productflow_backend.infrastructure.db.session import get_session_factory


def _seed_app_settings(values: dict[str, str]) -> None:
    session = get_session_factory()()
    try:
        for key, value in values.items():
            session.merge(AppSetting(key=key, value=value))
        session.commit()
    finally:
        session.close()


def _seed_new_api_sso_settings(
    *,
    base_url: str,
    shared_secret: str,
    start_url: str | None = None,
    verify_url: str | None = None,
    verify_path: str | None = None,
    timeout_seconds: int | None = None,
) -> None:
    values = {
        "new_api_base_url": base_url,
        "new_api_sso_shared_secret": shared_secret,
    }
    if start_url is not None:
        values["new_api_sso_start_url"] = start_url
    if verify_url is not None:
        values["new_api_sso_verify_url"] = verify_url
    if verify_path is not None:
        values["new_api_sso_verify_path"] = verify_path
    if timeout_seconds is not None:
        values["new_api_sso_timeout_seconds"] = str(timeout_seconds)
    _seed_app_settings(values)


def test_new_api_sso_callback_creates_server_side_user_session(configured_env, monkeypatch) -> None:
    from productflow_backend.presentation.api import create_app

    _seed_new_api_sso_settings(base_url="https://api.example.test", shared_secret="server-secret")

    def fake_post(url: str, *, json: dict, headers: dict, timeout: int):
        assert url == "https://api.example.test/api/productflow/sso/verify"
        assert json == {"ticket": "ticket-123"}
        assert headers == {"Authorization": "Bearer server-secret"}
        assert timeout == 10

        class Response:
            status_code = 200

            @staticmethod
            def json() -> dict:
                return {
                    "data": {
                        "user_id": 42,
                        "username": "alice",
                        "group": "default",
                        "role": "1",
                        "token": "sk-productflow-secret",
                        "token_id": 77,
                        "token_name": "ProductFlow",
                        "token_group": "GPT-Image-2",
                        "image_model": "gpt-image-2",
                        "image_models": ["gpt-image-3", "gpt-image-2", "gpt-image-2"],
                        "text_model": "gpt-4.1-mini",
                        "text_models": ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-mini"],
                        "expires_in": 3600,
                    }
                }

        return Response()

    monkeypatch.setattr("productflow_backend.application.new_api_sso.httpx.post", fake_post)

    client = TestClient(create_app())
    callback = client.get("/auth/new-api/callback?ticket=ticket-123", follow_redirects=False)

    assert callback.status_code == 303
    assert callback.headers["location"] == "/products"
    assert "session" in client.cookies
    assert "sk-productflow-secret" not in client.cookies["session"]

    state = client.get("/api/auth/session")
    assert state.status_code == 200
    assert state.json() == {
        "authenticated": True,
        "principal_kind": "user",
        "username": "alice",
        "new_api_user_id": "42",
        "new_api_token_id": "77",
        "new_api_token_group": "GPT-Image-2",
        "new_api_image_model": "gpt-image-2",
        "new_api_image_models": ["gpt-image-2", "gpt-image-3"],
        "new_api_text_model": "gpt-4.1-mini",
        "new_api_text_models": ["gpt-4.1-mini", "gpt-4.1"],
    }
    assert "sk-productflow-secret" not in state.text

    session = get_session_factory()()
    try:
        auth_session = session.scalar(select(AuthSession).where(AuthSession.new_api_user_id == "42"))
        assert auth_session is not None
        assert auth_session.principal_kind == "user"
        assert auth_session.new_api_token == "sk-productflow-secret"
        assert auth_session.new_api_token_name == "ProductFlow"
        assert auth_session.new_api_token_group == "GPT-Image-2"
        assert auth_session.new_api_image_model == "gpt-image-2"
        assert auth_session.new_api_image_models == ["gpt-image-2", "gpt-image-3"]
        assert auth_session.new_api_text_model == "gpt-4.1-mini"
        assert auth_session.new_api_text_models == ["gpt-4.1-mini", "gpt-4.1"]
        assert 3595 <= (auth_session.expires_at - auth_session.created_at).total_seconds() <= 3605
    finally:
        session.close()


def test_health_sso_uses_runtime_settings(configured_env) -> None:
    from productflow_backend.presentation.api import create_app

    _seed_new_api_sso_settings(base_url="https://api.example.test", shared_secret="server-secret")

    client = TestClient(create_app())
    response = client.get("/api/health/sso")

    assert response.status_code == 200
    assert response.json()["supports_sso"] is True


def test_new_api_sso_callback_rejects_guest_role(configured_env, monkeypatch) -> None:
    from productflow_backend.presentation.api import create_app

    _seed_new_api_sso_settings(base_url="https://api.example.test", shared_secret="server-secret")

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "data": {
                    "user_id": 42,
                    "username": "guest",
                    "role": "0",
                    "token": "sk-productflow-secret",
                }
            }

    monkeypatch.setattr("productflow_backend.application.new_api_sso.httpx.post", lambda *args, **kwargs: Response())

    client = TestClient(create_app())
    callback = client.get("/auth/new-api/callback?ticket=ticket-guest")

    assert callback.status_code == 401
    assert callback.json()["detail"] == "guest_account_disabled"
    assert "session" not in client.cookies


def test_new_api_sso_missing_or_invalid_role_falls_back_to_user(configured_env) -> None:
    session = get_session_factory()()
    try:
        missing_role_session = create_new_api_user_session(
            session,
            NewApiSessionClaims(
                user_id="missing-role-user",
                username="alice",
                token="sk-missing-role",
            ),
        )
        invalid_role_session = create_new_api_user_session(
            session,
            NewApiSessionClaims(
                user_id="invalid-role-user",
                username="bob",
                role="abc",
                token="sk-invalid-role",
            ),
        )
        assert missing_role_session.principal_kind == "user"
        assert invalid_role_session.principal_kind == "user"
    finally:
        session.close()


def test_new_api_sso_admin_role_creates_admin_principal_and_short_ttl(configured_env) -> None:
    session = get_session_factory()()
    try:
        auth_session = create_new_api_user_session(
            session,
            NewApiSessionClaims(
                user_id="admin-user",
                username="alice",
                role="10",
                token="sk-admin-token",
                expires_in_seconds=300,
            ),
        )
        assert auth_session.principal_kind == "admin"
        assert 295 <= (auth_session.expires_at - auth_session.created_at).total_seconds() <= 305
    finally:
        session.close()


def test_unexpected_positive_new_api_role_falls_back_to_user_with_warning(configured_env, monkeypatch) -> None:
    warnings: list[str] = []

    class DummyLogger:
        @staticmethod
        def warning(message: str, *args) -> None:
            warnings.append(message % args)

    monkeypatch.setattr(auth_sessions, "logger", DummyLogger())
    session = get_session_factory()()
    try:
        auth_session = create_new_api_user_session(
            session,
            NewApiSessionClaims(
                user_id="weird-role-user",
                username="alice",
                role="2",
                token="sk-user-token",
                expires_in_seconds=120,
            ),
        )
        assert auth_session.principal_kind == "user"
        assert warnings == ["Unexpected ProductFlow SSO role 2; treating session as ordinary user"]
    finally:
        session.close()


def test_new_api_sso_callback_rejects_invalid_ticket(configured_env, monkeypatch) -> None:
    from productflow_backend.presentation.api import create_app

    _seed_new_api_sso_settings(base_url="https://api.example.test", shared_secret="server-secret")

    class Response:
        status_code = 401

        @staticmethod
        def json() -> dict:
            return {"success": False}

    monkeypatch.setattr("productflow_backend.application.new_api_sso.httpx.post", lambda *args, **kwargs: Response())

    client = TestClient(create_app())
    callback = client.get("/auth/new-api/callback?ticket=bad")

    assert callback.status_code == 401
    assert callback.json()["detail"] == "New API SSO 票据无效或已过期"
    assert "session" not in client.cookies


def test_password_admin_login_route_is_removed(configured_env) -> None:
    from productflow_backend.presentation.api import create_app

    client = TestClient(create_app())
    login = client.post("/api/auth/session", json={"admin_key": "super-secret-admin-key"})

    assert login.status_code == 404


def test_password_admin_login_route_stays_removed_for_plain_sessions(configured_env) -> None:
    from productflow_backend.presentation.api import create_app

    client = TestClient(create_app())
    login = client.post("/api/auth/session", json={"admin_key": "super-secret-admin-key"})

    assert login.status_code == 404
    assert client.get("/api/auth/session").json() == {"authenticated": False}


def test_revoked_server_side_admin_session_no_longer_authorizes(configured_env) -> None:
    from productflow_backend.presentation.api import create_app

    client = TestClient(create_app())
    _login(client)

    session = get_session_factory()()
    try:
        auth_session = session.scalar(select(AuthSession).where(AuthSession.principal_kind == "admin"))
        assert auth_session is not None
        auth_session.revoked_at = auth_session.created_at
        session.commit()
    finally:
        session.close()

    state = client.get("/api/auth/session")
    assert state.status_code == 200
    assert state.json() == {"authenticated": False}

    private_route = client.get("/api/products")
    assert private_route.status_code == 401
    assert private_route.json()["detail"] == "请先登录"


def test_session_state_hides_sso_fields_when_not_configured(configured_env) -> None:
    from productflow_backend.presentation.api import create_app

    client = TestClient(create_app())
    state = client.get("/api/auth/session")

    assert state.status_code == 200
    assert state.json() == {"authenticated": False}


def test_runtime_new_api_settings_drive_session_state_and_sso_callback(configured_env, monkeypatch) -> None:
    from productflow_backend.presentation.api import create_app

    app = create_app()
    admin = TestClient(app)
    _login(admin)
    _unlock_settings(admin)

    updated = admin.patch(
        "/api/settings",
        json={
            "values": {
                "new_api_base_url": "https://api.runtime.test",
                "new_api_sso_start_url": "https://api.runtime.test/sso/start",
                "new_api_sso_verify_path": "/custom/verify",
                "new_api_sso_shared_secret": "runtime-secret",
                "new_api_sso_timeout_seconds": 7,
            }
        },
    )
    assert updated.status_code == 200

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "data": {
                    "user_id": "runtime-user",
                    "username": "alice",
                    "role": "1",
                    "token": "sk-runtime-token",
                    "token_id": "runtime-token-id",
                    "token_name": "ProductFlow",
                }
            }

    def fake_post(url: str, *, json: dict, headers: dict, timeout: int):
        assert url == "https://api.runtime.test/custom/verify"
        assert json == {"ticket": "runtime-ticket"}
        assert headers == {"Authorization": "Bearer runtime-secret"}
        assert timeout == 7
        return Response()

    monkeypatch.setattr("productflow_backend.application.new_api_sso.httpx.post", fake_post)

    public = TestClient(app)
    state = public.get("/api/auth/session")
    assert state.status_code == 200
    assert state.json() == {
        "authenticated": False,
        "sso_start_url": "https://api.runtime.test/sso/start",
    }

    callback = public.get("/auth/new-api/callback?ticket=runtime-ticket", follow_redirects=False)
    assert callback.status_code == 303
    assert callback.headers["location"] == "/products"

    authenticated_state = public.get("/api/auth/session")
    assert authenticated_state.status_code == 200
    assert authenticated_state.json() == {
        "authenticated": True,
        "principal_kind": "user",
        "username": "alice",
        "new_api_user_id": "runtime-user",
        "new_api_token_id": "runtime-token-id",
        "sso_start_url": "https://api.runtime.test/sso/start",
    }


def test_new_api_sso_user_can_access_workspace_and_gallery_but_not_admin_only_routes(
    configured_env,
    monkeypatch,
) -> None:
    _seed_new_api_sso_settings(base_url="https://api.example.test", shared_secret="server-secret")

    from productflow_backend.presentation.api import create_app

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "data": {
                    "user_id": "user-42",
                    "username": "alice",
                    "role": "1",
                    "token": "sk-productflow-secret",
                    "token_id": "77",
                    "token_name": "ProductFlow",
                }
            }

    monkeypatch.setattr("productflow_backend.application.new_api_sso.httpx.post", lambda *args, **kwargs: Response())

    client = TestClient(create_app())
    callback = client.get("/auth/new-api/callback?ticket=ticket-123", follow_redirects=False)

    assert callback.status_code == 303

    products = client.get("/api/products")
    assert products.status_code == 200
    assert products.json()["items"] == []

    runtime_config = client.get("/api/settings/runtime")
    assert runtime_config.status_code == 200
    assert runtime_config.json() == {
        "image_generation_max_dimension": 3840,
        "image_tool_allowed_fields": [
            "model",
            "quality",
            "output_format",
            "output_compression",
            "moderation",
            "action",
            "input_fidelity",
            "partial_images",
        ],
        "deletion_enabled": False,
    }

    settings = client.get("/api/settings")
    assert settings.status_code == 403
    assert settings.json()["detail"] == "需要管理员权限"

    gallery = client.get("/api/gallery")
    assert gallery.status_code == 200
    assert gallery.json()["items"] == []


def test_new_api_sso_users_cannot_access_each_others_workspace_resources(configured_env, monkeypatch) -> None:
    from productflow_backend.domain.enums import WorkflowNodeType
    from productflow_backend.presentation.api import create_app

    _seed_new_api_sso_settings(base_url="https://api.example.test", shared_secret="server-secret")

    tickets = {
        "ticket-a": {
            "user_id": "user-a",
            "username": "alice",
            "role": "1",
            "token": "sk-user-a",
            "token_id": "token-a",
            "token_name": "ProductFlow",
            "token_group": "GPT-Image",
            "image_model": "gpt-image-2",
            "image_models": ["gpt-image-2"],
        },
        "ticket-b": {
            "user_id": "user-b",
            "username": "bob",
            "role": "1",
            "token": "sk-user-b",
            "token_id": "token-b",
            "token_name": "ProductFlow",
            "token_group": "GPT-Image",
            "image_model": "gpt-image-2",
            "image_models": ["gpt-image-2"],
        },
    }

    class Response:
        status_code = 200

        def __init__(self, ticket: str) -> None:
            self.ticket = ticket

        def json(self) -> dict:
            return {"data": tickets[self.ticket]}

    def fake_post(url: str, *, json: dict, headers: dict, timeout: int):
        return Response(json["ticket"])

    monkeypatch.setattr("productflow_backend.application.new_api_sso.httpx.post", fake_post)

    app = create_app()
    alice = TestClient(app)
    bob = TestClient(app)

    assert alice.get("/auth/new-api/callback?ticket=ticket-a", follow_redirects=False).status_code == 303
    assert bob.get("/auth/new-api/callback?ticket=ticket-b", follow_redirects=False).status_code == 303

    created_product = alice.post(
        "/api/products",
        data={"name": "Alice cream", "category": "护肤", "price": "59"},
        files={"image": ("alice.png", _make_demo_image_bytes(), "image/png")},
    )
    assert created_product.status_code == 201
    product = created_product.json()
    product_id = product["id"]
    source_asset_id = product["source_assets"][0]["id"]

    bob_products = bob.get("/api/products")
    assert bob_products.status_code == 200
    assert bob_products.json()["items"] == []
    assert bob.get(f"/api/products/{product_id}").status_code == 404
    assert bob.get(f"/api/source-assets/{source_asset_id}/download").status_code == 404

    alice_workflow = alice.get(f"/api/products/{product_id}/workflow")
    assert alice_workflow.status_code == 200
    workflow = alice_workflow.json()
    assert bob.get(f"/api/products/{product_id}/workflow").status_code == 404
    assert bob.get(f"/api/products/{product_id}/workflow/status").status_code == 404

    alice_template = alice.post(
        f"/api/products/{product_id}/workflow/user-template-groups",
        json={
            "title": "Alice template",
            "description": None,
            "node_ids": [
                node["id"] for node in workflow["nodes"] if node["node_type"] != WorkflowNodeType.PRODUCT_CONTEXT.value
            ][:1],
        },
    )
    assert alice_template.status_code == 201
    template = alice_template.json()
    bob_templates = bob.get("/api/workflow/canvas-templates")
    assert bob_templates.status_code == 200
    assert all(item["key"] != template["key"] for item in bob_templates.json()["items"])
    assert (
        bob.patch(
            f"/api/workflow/user-template-groups/{template['user_template_id']}",
            json={"title": "stolen", "description": None},
        ).status_code
        == 404
    )

    alice_session = alice.post("/api/image-sessions", json={"product_id": product_id, "title": "Alice session"})
    assert alice_session.status_code == 201
    image_session_id = alice_session.json()["id"]
    alice_upload = alice.post(
        f"/api/image-sessions/{image_session_id}/reference-images",
        files={"reference_images": ("ref.png", _make_demo_image_bytes(), "image/png")},
    )
    assert alice_upload.status_code == 200
    session_asset_id = alice_upload.json()["assets"][0]["id"]

    bob_sessions = bob.get("/api/image-sessions")
    assert bob_sessions.status_code == 200
    assert bob_sessions.json()["items"] == []
    assert bob.get(f"/api/image-sessions/{image_session_id}").status_code == 404
    assert bob.get(f"/api/image-sessions/{image_session_id}/status").status_code == 404
    assert bob.get(f"/api/image-session-assets/{session_asset_id}/download").status_code == 404
    assert (
        bob.post(
            f"/api/image-sessions/{image_session_id}/assets/{session_asset_id}/attach-to-product",
            json={"target": "reference"},
        ).status_code
        == 404
    )

    alice_generated = alice.post(
        f"/api/image-sessions/{image_session_id}/generate",
        json={"prompt": "Alice gallery asset", "size": "1024x1024"},
    )
    assert alice_generated.status_code == 202
    generated_asset_id = alice_generated.json()["rounds"][0]["generated_asset"]["id"]

    alice_share = alice.post("/api/gallery", json={"image_session_asset_id": generated_asset_id})
    assert alice_share.status_code == 201
    assert alice_share.json()["shared_by_user_id"] == "user-a"
    assert alice_share.json()["shared_by_username"] == "alice"

    bob_gallery = bob.get("/api/gallery")
    assert bob_gallery.status_code == 200
    assert [item["id"] for item in bob_gallery.json()["items"]] == [alice_share.json()["id"]]
    detail = bob.get(f"/api/gallery/{alice_share.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == alice_share.json()["id"]
    report = bob.post(
        f"/api/gallery/{alice_share.json()['id']}/report",
        json={"reason_code": "copyright", "reason_text": "looks copied"},
    )
    assert report.status_code == 201
    assert report.json()["entry_id"] == alice_share.json()["id"]
    assert report.json()["reporter_user_id"] == "user-b"

    bob_share = bob.post("/api/gallery", json={"image_session_asset_id": generated_asset_id})
    assert bob_share.status_code == 400
    assert bob_share.json()["detail"] == "只能保存自己的生成结果到画廊"

    alice_delete = alice.delete(f"/api/gallery/{alice_share.json()['id']}")
    assert alice_delete.status_code == 204
    assert bob.get(f"/api/gallery/{alice_share.json()['id']}").status_code == 404


def test_admin_normal_workspace_cannot_inspect_user_product(configured_env, monkeypatch) -> None:
    from productflow_backend.presentation.api import create_app

    _seed_new_api_sso_settings(base_url="https://api.example.test", shared_secret="server-secret")

    tickets = {
        "ticket-a": {
            "user_id": "user-a",
            "username": "alice",
            "role": "1",
            "token": "sk-user-a",
            "token_id": "token-a",
            "token_name": "ProductFlow",
        },
        "ticket-admin": {
            "user_id": "admin-1",
            "username": "root",
            "role": "10",
            "token": "sk-admin",
            "token_id": "token-admin",
            "token_name": "ProductFlow",
        },
    }

    class Response:
        status_code = 200

        def __init__(self, ticket: str) -> None:
            self.ticket = ticket

        def json(self) -> dict:
            return {"data": tickets[self.ticket]}

    def fake_post(url: str, *, json: dict, headers: dict, timeout: int):
        return Response(json["ticket"])

    monkeypatch.setattr("productflow_backend.application.new_api_sso.httpx.post", fake_post)

    app = create_app()
    alice = TestClient(app)
    admin = TestClient(app)

    assert alice.get("/auth/new-api/callback?ticket=ticket-a", follow_redirects=False).status_code == 303
    assert admin.get("/auth/new-api/callback?ticket=ticket-admin", follow_redirects=False).status_code == 303
    created_product = alice.post(
        "/api/products",
        data={"name": "Alice cream", "category": "护肤", "price": "59"},
        files={"image": ("alice.png", _make_demo_image_bytes(), "image/png")},
    )
    assert created_product.status_code == 201
    product_id = created_product.json()["id"]

    session = get_session_factory()()
    try:
        assert session.scalars(select(AuditLog)).all() == []
    finally:
        session.close()

    inspected = admin.get(
        f"/api/products/{product_id}",
        headers={"user-agent": "productflow-test-agent"},
    )
    assert inspected.status_code == 404

    session = get_session_factory()()
    try:
        logs = session.scalars(select(AuditLog)).all()
        assert logs == []
    finally:
        session.close()


def test_admin_revoke_session_endpoint_revokes_user_session_and_audits(configured_env, monkeypatch) -> None:
    from productflow_backend.presentation.api import create_app

    _seed_new_api_sso_settings(base_url="https://api.example.test", shared_secret="server-secret")

    tickets = {
        "ticket-user": {
            "user_id": "user-a",
            "username": "alice",
            "role": "1",
            "token": "sk-user-a",
            "token_id": "token-a",
            "token_name": "ProductFlow",
        },
        "ticket-admin": {
            "user_id": "admin-1",
            "username": "root",
            "role": "10",
            "token": "sk-admin",
            "token_id": "token-admin",
            "token_name": "ProductFlow",
        },
    }

    class Response:
        status_code = 200

        def __init__(self, ticket: str) -> None:
            self.ticket = ticket

        def json(self) -> dict:
            return {"data": tickets[self.ticket]}

    monkeypatch.setattr(
        "productflow_backend.application.new_api_sso.httpx.post",
        lambda url, *, json, headers, timeout: Response(json["ticket"]),
    )

    app = create_app()
    user = TestClient(app)
    admin = TestClient(app)

    assert user.get("/auth/new-api/callback?ticket=ticket-user", follow_redirects=False).status_code == 303
    assert admin.get("/auth/new-api/callback?ticket=ticket-admin", follow_redirects=False).status_code == 303

    session = get_session_factory()()
    try:
        user_session = session.scalar(select(AuthSession).where(AuthSession.new_api_user_id == "user-a"))
        assert user_session is not None
        user_session_id = user_session.id
    finally:
        session.close()

    revoked = admin.post(
        f"/api/admin/sessions/{user_session_id}/revoke",
        headers={"user-agent": "productflow-admin"},
    )
    assert revoked.status_code == 200
    assert revoked.json() == {"ok": True}

    state = user.get("/api/auth/session")
    assert state.status_code == 200
    assert state.json()["authenticated"] is False

    session = get_session_factory()()
    try:
        updated = session.get(AuthSession, user_session_id)
        assert updated is not None
        assert updated.revoked_at is not None
        logs = session.scalars(select(AuditLog)).all()
        assert len(logs) == 1
        assert logs[0].admin_user_id == "admin-1"
        assert logs[0].target_user_id == "user-a"
        assert logs[0].action == "revoke_auth_session"
        assert logs[0].resource_type == "auth_session"
        assert logs[0].resource_id == user_session_id
    finally:
        session.close()
