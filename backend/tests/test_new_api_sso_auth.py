from __future__ import annotations

from fastapi.testclient import TestClient
from helpers import _make_demo_image_bytes
from sqlalchemy import select

from productflow_backend.infrastructure.db.models import AuditLog, AuthSession
from productflow_backend.infrastructure.db.session import get_session_factory


def test_new_api_sso_callback_creates_server_side_user_session(configured_env, monkeypatch) -> None:
    monkeypatch.setenv("NEW_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("NEW_API_SSO_SHARED_SECRET", "server-secret")

    from productflow_backend.config import get_settings
    from productflow_backend.presentation.api import create_app

    get_settings.cache_clear()

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
                        "role": "user",
                        "token": "sk-productflow-secret",
                        "token_id": 77,
                        "token_name": "ProductFlow",
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
        "access_required": True,
        "principal_kind": "user",
        "username": "alice",
        "new_api_user_id": "42",
        "new_api_token_id": "77",
    }
    assert "sk-productflow-secret" not in state.text

    session = get_session_factory()()
    try:
        auth_session = session.scalar(select(AuthSession).where(AuthSession.new_api_user_id == "42"))
        assert auth_session is not None
        assert auth_session.principal_kind == "user"
        assert auth_session.new_api_token == "sk-productflow-secret"
        assert auth_session.new_api_token_name == "ProductFlow"
    finally:
        session.close()


def test_new_api_sso_callback_rejects_invalid_ticket(configured_env, monkeypatch) -> None:
    monkeypatch.setenv("NEW_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("NEW_API_SSO_SHARED_SECRET", "server-secret")

    from productflow_backend.config import get_settings
    from productflow_backend.presentation.api import create_app

    get_settings.cache_clear()

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


def test_admin_login_uses_server_side_admin_session(configured_env) -> None:
    from productflow_backend.presentation.api import create_app

    client = TestClient(create_app())
    login = client.post("/api/auth/session", json={"admin_key": "super-secret-admin-key"})

    assert login.status_code == 200
    assert "session" in client.cookies

    state = client.get("/api/auth/session")
    assert state.status_code == 200
    assert state.json() == {
        "authenticated": True,
        "access_required": True,
        "principal_kind": "admin",
        "username": "admin",
    }

    session = get_session_factory()()
    try:
        auth_session = session.scalar(select(AuthSession).where(AuthSession.principal_kind == "admin"))
        assert auth_session is not None
        assert auth_session.new_api_token is None
    finally:
        session.close()


def test_revoked_server_side_admin_session_no_longer_authorizes(configured_env) -> None:
    from productflow_backend.presentation.api import create_app

    client = TestClient(create_app())
    login = client.post("/api/auth/session", json={"admin_key": "super-secret-admin-key"})
    assert login.status_code == 200

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
    assert state.json() == {"authenticated": False, "access_required": True}

    private_route = client.get("/api/products")
    assert private_route.status_code == 401
    assert private_route.json()["detail"] == "请先登录"


def test_session_state_hides_sso_fields_when_not_configured(configured_env) -> None:
    from productflow_backend.presentation.api import create_app

    client = TestClient(create_app())
    state = client.get("/api/auth/session")

    assert state.status_code == 200
    assert state.json() == {"authenticated": False, "access_required": True}


def test_new_api_sso_user_can_access_workspace_but_not_admin_only_routes(configured_env, monkeypatch) -> None:
    monkeypatch.setenv("NEW_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("NEW_API_SSO_SHARED_SECRET", "server-secret")

    from productflow_backend.config import get_settings
    from productflow_backend.presentation.api import create_app

    get_settings.cache_clear()

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "data": {
                    "user_id": "user-42",
                    "username": "alice",
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
    assert runtime_config.json()["admin_access_required"] is True

    settings = client.get("/api/settings")
    assert settings.status_code == 403
    assert settings.json()["detail"] == "需要管理员权限"

    gallery = client.get("/api/gallery")
    assert gallery.status_code == 403
    assert gallery.json()["detail"] == "需要管理员权限"


def test_new_api_sso_users_cannot_access_each_others_workspace_resources(configured_env, monkeypatch) -> None:
    monkeypatch.setenv("NEW_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("NEW_API_SSO_SHARED_SECRET", "server-secret")

    from productflow_backend.config import get_settings
    from productflow_backend.domain.enums import WorkflowNodeType
    from productflow_backend.presentation.api import create_app

    get_settings.cache_clear()

    tickets = {
        "ticket-a": {
            "user_id": "user-a",
            "username": "alice",
            "token": "sk-user-a",
            "token_id": "token-a",
            "token_name": "ProductFlow",
        },
        "ticket-b": {
            "user_id": "user-b",
            "username": "bob",
            "token": "sk-user-b",
            "token_id": "token-b",
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
                node["id"]
                for node in workflow["nodes"]
                if node["node_type"] != WorkflowNodeType.PRODUCT_CONTEXT.value
            ][:1],
        },
    )
    assert alice_template.status_code == 201
    template = alice_template.json()
    bob_templates = bob.get("/api/workflow/canvas-templates")
    assert bob_templates.status_code == 200
    assert all(item["key"] != template["key"] for item in bob_templates.json()["items"])
    assert bob.patch(
        f"/api/workflow/user-template-groups/{template['user_template_id']}",
        json={"title": "stolen", "description": None},
    ).status_code == 404

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
    assert bob.post(
        f"/api/image-sessions/{image_session_id}/assets/{session_asset_id}/attach-to-product",
        json={"target": "reference"},
    ).status_code == 404


def test_admin_user_content_inspection_writes_audit_log(configured_env, monkeypatch) -> None:
    monkeypatch.setenv("NEW_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("NEW_API_SSO_SHARED_SECRET", "server-secret")

    from productflow_backend.config import get_settings
    from productflow_backend.presentation.api import create_app

    get_settings.cache_clear()

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "data": {
                    "user_id": "user-a",
                    "username": "alice",
                    "token": "sk-user-a",
                    "token_id": "token-a",
                    "token_name": "ProductFlow",
                }
            }

    monkeypatch.setattr("productflow_backend.application.new_api_sso.httpx.post", lambda *args, **kwargs: Response())

    app = create_app()
    alice = TestClient(app)
    admin = TestClient(app)

    assert alice.get("/auth/new-api/callback?ticket=ticket-a", follow_redirects=False).status_code == 303
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

    assert admin.post("/api/auth/session", json={"admin_key": "super-secret-admin-key"}).status_code == 200
    inspected = admin.get(
        f"/api/products/{product_id}",
        headers={"user-agent": "productflow-test-agent"},
    )
    assert inspected.status_code == 200

    session = get_session_factory()()
    try:
        logs = session.scalars(select(AuditLog)).all()
        assert len(logs) == 1
        audit_log = logs[0]
        assert audit_log.admin_user_id == "emergency-admin"
        assert audit_log.admin_username == "admin"
        assert audit_log.target_user_id == "user-a"
        assert audit_log.action == "read"
        assert audit_log.resource_type == "product"
        assert audit_log.resource_id == product_id
        assert audit_log.client_address == "testclient"
        assert audit_log.user_agent == "productflow-test-agent"
    finally:
        session.close()
