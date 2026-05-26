from __future__ import annotations

import base64
import time
from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from PIL import Image

if TYPE_CHECKING:
    from productflow_backend.application.product_workflow_dependencies import WorkflowExecutionDependencies

from productflow_backend.application.auth_sessions import (
    AUTH_SESSION_COOKIE_KEY,
    NewApiSessionClaims,
    create_new_api_user_session,
)
from productflow_backend.infrastructure.db.session import get_session_factory
from productflow_backend.presentation.session import build_signed_session_cookie_value


def _make_demo_image_bytes() -> bytes:
    return _make_demo_image_bytes_with_size(800, 800)


def _make_demo_image_bytes_with_size(width: int, height: int) -> bytes:
    image = Image.new("RGB", (width, height), (240, 240, 240))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _make_demo_image_data_url() -> str:
    encoded = base64.b64encode(_make_demo_image_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _read_image_size(image_bytes: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(image_bytes)) as image:
        return image.size


def _login(
    client: TestClient,
    *,
    user_id: str | None = None,
    username: str = "admin",
    role: str = "10",
    token: str | None = None,
    token_id: str | None = None,
    token_name: str | None = None,
    token_group: str | None = None,
    image_model: str | None = None,
    image_models: tuple[str, ...] | list[str] | None = None,
    text_model: str | None = None,
    text_models: tuple[str, ...] | list[str] | None = None,
) -> None:
    session = get_session_factory()()
    try:
        auth_session = create_new_api_user_session(
            session,
            NewApiSessionClaims(
                user_id=user_id,
                username=username,
                role=role,
                token=token,
                token_id=token_id,
                token_name=token_name,
                token_group=token_group,
                image_model=image_model,
                image_models=tuple(image_models or ((image_model,) if image_model else ())),
                text_model=text_model,
                text_models=tuple(text_models or ((text_model,) if text_model else ())),
                expires_in_seconds=24 * 60 * 60,
            ),
        )
    finally:
        session.close()
    cookie_value = build_signed_session_cookie_value(
        {AUTH_SESSION_COOKIE_KEY: auth_session.id},
        secret_key="super-secret-session-key-123",
    )
    client.cookies.clear()
    client.cookies.set("session", cookie_value)
    assert "session" in client.cookies, "login did not persist session cookie"
    state = client.get("/api/auth/session")
    assert state.status_code == 200, f"session state failed after login: {state.status_code}: {state.text}"
    assert state.json()["authenticated"] is True, (
        f"login response did not create authenticated session: "
        f"has_session_cookie={'session' in client.cookies} state={state.text}"
    )


def _unlock_settings(client: TestClient) -> None:
    unlock = client.post("/api/settings/unlock", json={"token": "super-secret-settings-token"})
    assert unlock.status_code == 200


def _enable_deletion(client: TestClient) -> None:
    _unlock_settings(client)
    response = client.patch("/api/settings", json={"values": {"deletion_enabled": True}})
    assert response.status_code == 200


def _wait_for_workflow_run(
    client: TestClient,
    product_id: str,
    *,
    run_id: str | None = None,
    status: str | None = None,
    timeout: float = 5.0,
) -> dict:
    deadline = time.monotonic() + timeout
    last_payload: dict | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/products/{product_id}/workflow")
        assert response.status_code == 200, (
            f"{response.status_code}: {response.text} has_session_cookie={'session' in client.cookies}"
        )
        last_payload = response.json()
        observed_run = (
            next((run for run in last_payload["runs"] if run["id"] == run_id), None)
            if run_id is not None
            else (last_payload["runs"][0] if last_payload["runs"] else None)
        )
        if observed_run and (status is None or observed_run["status"] == status):
            if run_id is not None and last_payload["runs"][0]["id"] != run_id:
                last_payload = {
                    **last_payload,
                    "runs": [observed_run, *[run for run in last_payload["runs"] if run["id"] != run_id]],
                }
            return last_payload
        time.sleep(0.05)
    assert last_payload is not None
    target = f"run {run_id} " if run_id is not None else ""
    raise AssertionError(f"workflow {target}did not reach {status or 'any status'}: {last_payload['runs'][:1]}")


def _execute_workflow_queue_inline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    dependencies: WorkflowExecutionDependencies | None = None,
) -> None:
    from productflow_backend.application.product_workflows import (
        execute_product_workflow_node_run,
        execute_product_workflow_run,
    )

    def execute_inline(run_id: str) -> None:
        execute_product_workflow_run(run_id, dependencies=dependencies)

    def execute_node_inline(node_run_id: str) -> None:
        execute_product_workflow_node_run(node_run_id, dependencies=dependencies)

    monkeypatch.setattr(
        "productflow_backend.application.product_workflow.execution.enqueue_workflow_run",
        execute_inline,
    )
    monkeypatch.setattr(
        "productflow_backend.application.product_workflow.execution.enqueue_workflow_node_run",
        execute_node_inline,
    )
