from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from helpers import _login

from productflow_backend.application.audit_events import create_audit_event, settle_model_call_audit_event
from productflow_backend.application.new_api_usage import NewApiLogFacts, NewApiUsageLookupResult
from productflow_backend.infrastructure.db.models import AuditEvent


def _create_client():
    from productflow_backend.presentation.api import create_app

    return TestClient(create_app())


def test_usage_events_are_scoped_to_current_user(configured_env: Path, db_session) -> None:
    client = _create_client()
    create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-a",
        subject_username="alice",
        status="succeeded",
        source="new_api",
        atelier_request_id="atelier-a",
        new_api_request_id="new-api-a",
        new_api_token_group="Atelier",
        model_name="gpt-image-2",
        quota=Decimal("1.25"),
        resource_type="image_session",
        resource_id="session-a",
    )
    create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-b",
        subject_username="bob",
        status="failed",
        source="new_api",
        atelier_request_id="atelier-b",
        model_name="gpt-5.2",
        quota=Decimal("9.99"),
        resource_type="product",
        resource_id="product-b",
    )
    db_session.commit()

    _login(client, user_id="user-a", username="alice", role="1")
    listed = client.get("/api/usage/events")

    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["subject_user_id"] == "user-a"
    assert payload["items"][0]["atelier_request_id"] == "atelier-a"
    assert payload["items"][0]["quota"] == "1.250000"

    summary = client.get("/api/usage/summary")
    assert summary.status_code == 200
    assert summary.json() == {
        "total_events": 1,
        "total_quota": "1.250000",
        "failed_events": 0,
    }


def test_admin_audit_events_can_filter_metadata_and_historical_unowned(configured_env: Path, db_session) -> None:
    client = _create_client()
    create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-a",
        subject_username="alice",
        status="failed",
        source="new_api",
        atelier_request_id="atelier-a",
        new_api_request_id="new-api-a",
        new_api_token_group="Atelier",
        model_name="gpt-image-2",
        error_code="model_not_found",
        error_message="模型不可用",
        resource_type="image_generation_task",
        resource_id="task-a",
    )
    create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id=None,
        status="succeeded",
        source="atelier",
        model_name="legacy-model",
        resource_type="image_session",
        resource_id="legacy-session",
    )
    db_session.commit()

    _login(client, user_id="admin-user", username="root", role="10")
    filtered = client.get("/api/admin/audit/events", params={"request_id": "atelier-a"})

    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert payload["items"][0]["subject_user_id"] == "user-a"
    assert payload["items"][0]["error_code"] == "model_not_found"

    historical = client.get("/api/admin/audit/events", params={"historical_unowned": True})
    assert historical.status_code == 200
    historical_payload = historical.json()
    assert historical_payload["total"] == 1
    assert historical_payload["items"][0]["resource_id"] == "legacy-session"


def test_admin_content_view_writes_audit_event(configured_env: Path, db_session) -> None:
    client = _create_client()
    source_event = create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-a",
        subject_username="alice",
        status="succeeded",
        source="new_api",
        resource_type="image_session",
        resource_id="session-a",
    )
    db_session.commit()

    _login(client, user_id="admin-user", username="root", role="10")
    response = client.post(
        "/api/admin/audit/content-view",
        json={"event_id": source_event.id, "resource_type": "image_session", "resource_id": "session-a"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["event_type"] == "admin_content_view"
    assert payload["actor_user_id"] == "admin-user"
    assert payload["subject_user_id"] == "user-a"
    assert payload["metadata_json"] == {"source_event_id": source_event.id}

    rows = db_session.query(AuditEvent).filter_by(event_type="admin_content_view").all()
    assert len(rows) == 1
    assert rows[0].resource_id == "session-a"


def test_audit_event_helpers_do_not_commit_caller_transaction(configured_env: Path) -> None:
    from productflow_backend.infrastructure.db.session import get_session_factory

    factory = get_session_factory()
    writer = factory()
    reader = factory()
    try:
        event = create_audit_event(
            writer,
            event_type="model_call",
            subject_user_id="user-a",
            status="running",
            source="atelier",
        )
        assert event.id is not None
        assert reader.get(AuditEvent, event.id) is None

        writer.rollback()
        assert reader.get(AuditEvent, event.id) is None
    finally:
        writer.close()
        reader.close()


def test_safe_audit_error_message_masks_sensitive_material() -> None:
    from productflow_backend.application.audit_events import safe_audit_error_message

    raw = (
        "Traceback request body prompt=draw this "
        "Authorization: Bearer sk-live-secret https://relay.example/v1 data:image/png;base64,AAAA"
    )

    assert safe_audit_error_message(raw) == "模型调用失败，请稍后重试"


def test_settle_model_call_copies_new_api_facts(configured_env: Path, db_session) -> None:
    event = create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-a",
        status="running",
        source="atelier",
        atelier_request_id="atr-found",
        model_name="local-model",
        quota=Decimal("0"),
        metadata_json={"operation": "image_generation"},
    )

    settle_model_call_audit_event(
        db_session,
        event_id=event.id,
        status="succeeded",
        atelier_request_id="atr-found",
        new_api_token="sk-test-token",
        model_name="fallback-model",
        provider_name="openai-images",
        lookup_result=NewApiUsageLookupResult(
            status="found",
            facts=NewApiLogFacts(
                log_id="9101",
                request_id="req-new-api",
                upstream_request_id="upstream-new-api",
                token_id="61",
                token_name="Atelier token",
                token_group="GPT-Image-2",
                model_name="gpt-image-2",
                quota=Decimal("12.345"),
                prompt_tokens=11,
                completion_tokens=22,
                use_time_seconds=Decimal("3"),
                log_type=2,
            ),
        ),
    )

    db_session.flush()
    assert event.status == "succeeded"
    assert event.new_api_log_id == "9101"
    assert event.new_api_request_id == "req-new-api"
    assert event.new_api_upstream_request_id == "upstream-new-api"
    assert event.new_api_token_id == "61"
    assert event.new_api_token_name == "Atelier token"
    assert event.new_api_token_group == "GPT-Image-2"
    assert event.model_name == "gpt-image-2"
    assert event.provider_name == "openai-images"
    assert event.quota == Decimal("12.345")
    assert event.prompt_tokens == 11
    assert event.completion_tokens == 22
    assert event.use_time_seconds == Decimal("3")
    assert event.metadata_json == {
        "operation": "image_generation",
        "billing_lookup_status": "found",
    }


def test_settle_model_call_keeps_success_quota_unknown_without_new_api_log(configured_env: Path, db_session) -> None:
    event = create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-a",
        status="running",
        source="atelier",
        atelier_request_id="atr-missing",
        quota=Decimal("0"),
    )

    settle_model_call_audit_event(
        db_session,
        event_id=event.id,
        status="succeeded",
        atelier_request_id="atr-missing",
        new_api_token="sk-test-token",
        model_name="gpt-image-2",
        lookup_result=NewApiUsageLookupResult(status="not_found"),
    )

    db_session.flush()
    assert event.status == "succeeded"
    assert event.quota is None
    assert event.model_name == "gpt-image-2"
    assert event.metadata_json == {"billing_lookup_status": "not_found"}


def test_settle_model_call_sets_failed_zero_only_when_no_log_found(configured_env: Path, db_session) -> None:
    no_log_event = create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-a",
        status="running",
        source="atelier",
        atelier_request_id="atr-failed-no-log",
    )
    lookup_failed_event = create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-a",
        status="running",
        source="atelier",
        atelier_request_id="atr-failed-lookup",
    )

    settle_model_call_audit_event(
        db_session,
        event_id=no_log_event.id,
        status="failed",
        atelier_request_id="atr-failed-no-log",
        new_api_token="sk-test-token",
        quota_if_not_found=Decimal("0"),
        lookup_result=NewApiUsageLookupResult(status="not_found"),
    )
    settle_model_call_audit_event(
        db_session,
        event_id=lookup_failed_event.id,
        status="failed",
        atelier_request_id="atr-failed-lookup",
        new_api_token="sk-test-token",
        lookup_result=NewApiUsageLookupResult(status="lookup_failed"),
    )

    db_session.flush()
    assert no_log_event.status == "failed"
    assert no_log_event.quota == Decimal("0")
    assert no_log_event.metadata_json == {"billing_lookup_status": "not_found"}
    assert lookup_failed_event.status == "failed"
    assert lookup_failed_event.quota is None
    assert lookup_failed_event.metadata_json == {"billing_lookup_status": "lookup_failed"}


def test_admin_content_view_rejects_resource_mismatch(configured_env: Path, db_session) -> None:
    client = _create_client()
    source_event = create_audit_event(
        db_session,
        event_type="model_call",
        subject_user_id="user-a",
        status="succeeded",
        source="new_api",
        resource_type="image_session",
        resource_id="session-a",
    )
    db_session.commit()

    _login(client, user_id="admin-user", username="root", role="10")
    response = client.post(
        "/api/admin/audit/content-view",
        json={"event_id": source_event.id, "resource_type": "image_session", "resource_id": "session-b"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "内容查看资源与来源审计事件不匹配"
    assert db_session.query(AuditEvent).filter_by(event_type="admin_content_view").count() == 0
