from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from productflow_backend.application.audit_events import AuditEventPage, AuditEventSummary
from productflow_backend.infrastructure.db.models import AuditEvent


class AuditEventResponse(BaseModel):
    id: str
    event_type: str
    actor_user_id: str | None = None
    actor_username: str | None = None
    actor_principal_kind: str | None = None
    subject_user_id: str | None = None
    subject_username: str | None = None
    status: str
    source: str
    atelier_request_id: str | None = None
    new_api_request_id: str | None = None
    new_api_upstream_request_id: str | None = None
    new_api_log_id: str | None = None
    new_api_token_id: str | None = None
    new_api_token_name: str | None = None
    new_api_token_group: str | None = None
    model_name: str | None = None
    provider_name: str | None = None
    quota: Decimal | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    use_time_seconds: Decimal | None = None
    error_code: str | None = None
    error_message: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    parent_resource_type: str | None = None
    parent_resource_id: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int


class AuditEventSummaryResponse(BaseModel):
    total_events: int
    total_quota: Decimal
    failed_events: int


class AdminContentViewRequest(BaseModel):
    event_id: str | None = None
    resource_type: str = Field(min_length=1, max_length=80)
    resource_id: str = Field(min_length=1, max_length=120)


def serialize_audit_event(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        event_type=event.event_type,
        actor_user_id=event.actor_user_id,
        actor_username=event.actor_username,
        actor_principal_kind=event.actor_principal_kind,
        subject_user_id=event.subject_user_id,
        subject_username=event.subject_username,
        status=event.status,
        source=event.source,
        atelier_request_id=event.atelier_request_id,
        new_api_request_id=event.new_api_request_id,
        new_api_upstream_request_id=event.new_api_upstream_request_id,
        new_api_log_id=event.new_api_log_id,
        new_api_token_id=event.new_api_token_id,
        new_api_token_name=event.new_api_token_name,
        new_api_token_group=event.new_api_token_group,
        model_name=event.model_name,
        provider_name=event.provider_name,
        quota=event.quota,
        prompt_tokens=event.prompt_tokens,
        completion_tokens=event.completion_tokens,
        use_time_seconds=event.use_time_seconds,
        error_code=event.error_code,
        error_message=event.error_message,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        parent_resource_type=event.parent_resource_type,
        parent_resource_id=event.parent_resource_id,
        metadata_json=event.metadata_json,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def serialize_audit_event_page(page: AuditEventPage) -> AuditEventListResponse:
    return AuditEventListResponse(
        items=[serialize_audit_event(item) for item in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
    )


def serialize_audit_event_summary(summary: AuditEventSummary) -> AuditEventSummaryResponse:
    return AuditEventSummaryResponse(
        total_events=summary.total_events,
        total_quota=summary.total_quota,
        failed_events=summary.failed_events,
    )
