from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from productflow_backend.application.auth_sessions import Principal
from productflow_backend.application.new_api_usage import (
    NewApiUsageLookupResult,
    lookup_new_api_usage_by_atelier_request_id,
)
from productflow_backend.domain.errors import NotFoundError
from productflow_backend.infrastructure.db.models import AuditEvent

MAX_PAGE_SIZE = 100
MAX_SAFE_ERROR_MESSAGE_LENGTH = 500
GENERIC_AUDIT_ERROR_MESSAGE = "模型调用失败，请稍后重试"
_SENSITIVE_AUDIT_ERROR_PATTERNS = (
    re.compile(r"sk-[a-zA-Z0-9_-]+"),
    re.compile(r"\b(api[_ -]?key|token|bearer|authorization|credential|secret)\b", re.IGNORECASE),
    re.compile(r"\b(base_url|prompt|request[_ -]?body|body)\s*=", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"data:image/[a-zA-Z0-9.+-]+;base64,", re.IGNORECASE),
    re.compile(r"(traceback|stack trace|/tmp/|[A-Za-z]:\\)", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class AuditEventPage:
    items: list[AuditEvent]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True, slots=True)
class AuditEventSummary:
    total_events: int
    total_quota: Decimal
    failed_events: int


def create_audit_event(
    session: Session,
    *,
    event_type: str,
    principal: Principal | None = None,
    subject_user_id: str | None = None,
    subject_username: str | None = None,
    status: str = "succeeded",
    source: str = "atelier",
    atelier_request_id: str | None = None,
    new_api_request_id: str | None = None,
    new_api_upstream_request_id: str | None = None,
    new_api_log_id: str | None = None,
    new_api_token_id: str | None = None,
    new_api_token_name: str | None = None,
    new_api_token_group: str | None = None,
    model_name: str | None = None,
    provider_name: str | None = None,
    quota: Decimal | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    use_time_seconds: Decimal | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    parent_resource_type: str | None = None,
    parent_resource_id: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        actor_user_id=principal.new_api_user_id if principal else None,
        actor_username=principal.username if principal else None,
        actor_principal_kind=principal.kind if principal else None,
        subject_user_id=subject_user_id,
        subject_username=subject_username,
        status=status,
        source=source,
        atelier_request_id=atelier_request_id,
        new_api_request_id=new_api_request_id,
        new_api_upstream_request_id=new_api_upstream_request_id,
        new_api_log_id=new_api_log_id,
        new_api_token_id=new_api_token_id,
        new_api_token_name=new_api_token_name,
        new_api_token_group=new_api_token_group,
        model_name=model_name,
        provider_name=provider_name,
        quota=quota,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        use_time_seconds=use_time_seconds,
        error_code=error_code,
        error_message=error_message,
        resource_type=resource_type,
        resource_id=resource_id,
        parent_resource_type=parent_resource_type,
        parent_resource_id=parent_resource_id,
        metadata_json=metadata_json,
    )
    session.add(event)
    session.flush()
    return event


def generate_atelier_request_id() -> str:
    return f"atr_{uuid4().hex}"


def update_audit_event(
    session: Session,
    *,
    event_id: str,
    status: str,
    new_api_request_id: str | None = None,
    new_api_upstream_request_id: str | None = None,
    new_api_log_id: str | None = None,
    model_name: str | None = None,
    provider_name: str | None = None,
    quota: Decimal | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    use_time_seconds: Decimal | None = None,
    clear_quota: bool = False,
    error_code: str | None = None,
    error_message: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> AuditEvent | None:
    event = session.get(AuditEvent, event_id)
    if event is None:
        return None

    event.status = status
    if new_api_request_id is not None:
        event.new_api_request_id = new_api_request_id
    if new_api_upstream_request_id is not None:
        event.new_api_upstream_request_id = new_api_upstream_request_id
    if new_api_log_id is not None:
        event.new_api_log_id = new_api_log_id
    if model_name is not None:
        event.model_name = model_name
    if provider_name is not None:
        event.provider_name = provider_name
    if clear_quota:
        event.quota = None
    if quota is not None:
        event.quota = quota
    if prompt_tokens is not None:
        event.prompt_tokens = prompt_tokens
    if completion_tokens is not None:
        event.completion_tokens = completion_tokens
    if use_time_seconds is not None:
        event.use_time_seconds = use_time_seconds
    if error_code is not None:
        event.error_code = error_code
    if error_message is not None:
        event.error_message = safe_audit_error_message(error_message)
    if metadata_json is not None:
        event.metadata_json = metadata_json
    session.flush()
    return event


def settle_model_call_audit_event(
    session: Session,
    *,
    event_id: str | None,
    status: str,
    atelier_request_id: str | None,
    new_api_token: str | None,
    model_name: str | None = None,
    provider_name: str | None = None,
    quota_if_not_found: Decimal | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    lookup_result: NewApiUsageLookupResult | None = None,
) -> None:
    if event_id is None:
        return
    event = session.get(AuditEvent, event_id)
    if event is None:
        return
    lookup = lookup_result or lookup_new_api_usage_by_atelier_request_id(
        new_api_token=new_api_token,
        atelier_request_id=atelier_request_id,
    )
    metadata = {
        **(event.metadata_json if isinstance(event.metadata_json, dict) else {}),
        **(metadata_json or {}),
        "billing_lookup_status": lookup.status,
    }
    facts = lookup.facts
    clear_quota = facts is None and quota_if_not_found is None
    update_audit_event(
        session,
        event_id=event_id,
        status=status,
        new_api_request_id=facts.request_id if facts is not None else None,
        new_api_upstream_request_id=facts.upstream_request_id if facts is not None else None,
        new_api_log_id=facts.log_id if facts is not None else None,
        model_name=(facts.model_name if facts is not None and facts.model_name is not None else model_name),
        provider_name=provider_name,
        quota=facts.quota if facts is not None else quota_if_not_found,
        clear_quota=clear_quota,
        prompt_tokens=facts.prompt_tokens if facts is not None else None,
        completion_tokens=facts.completion_tokens if facts is not None else None,
        use_time_seconds=facts.use_time_seconds if facts is not None else None,
        error_code=error_code,
        error_message=error_message,
        metadata_json=metadata,
    )
    if facts is not None:
        if facts.token_id is not None:
            event.new_api_token_id = facts.token_id
        if facts.token_name is not None:
            event.new_api_token_name = facts.token_name
        if facts.token_group is not None:
            event.new_api_token_group = facts.token_group
        session.flush()


def safe_audit_error_message(value: str | None) -> str | None:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        return None
    if any(pattern.search(normalized) for pattern in _SENSITIVE_AUDIT_ERROR_PATTERNS):
        return GENERIC_AUDIT_ERROR_MESSAGE
    return normalized[:MAX_SAFE_ERROR_MESSAGE_LENGTH]


def list_user_audit_events(
    session: Session,
    *,
    subject_user_id: str,
    page: int,
    page_size: int,
    event_type: str | None = None,
    status: str | None = None,
    model_name: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> AuditEventPage:
    return _list_audit_events(
        session,
        page=page,
        page_size=page_size,
        subject_user_id=subject_user_id,
        event_type=event_type,
        status=status,
        model_name=model_name,
        resource_type=resource_type,
        resource_id=resource_id,
        created_from=created_from,
        created_to=created_to,
        include_historical_unowned=False,
    )


def summarize_user_audit_events(session: Session, *, subject_user_id: str) -> AuditEventSummary:
    total_events = (
        session.scalar(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.subject_user_id == subject_user_id)
        )
        or 0
    )
    failed_events = (
        session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.subject_user_id == subject_user_id, AuditEvent.status == "failed")
        )
        or 0
    )
    total_quota = (
        session.scalar(
            select(func.coalesce(func.sum(AuditEvent.quota), 0)).where(AuditEvent.subject_user_id == subject_user_id)
        )
        or Decimal("0")
    )
    return AuditEventSummary(
        total_events=int(total_events),
        total_quota=Decimal(str(total_quota)),
        failed_events=int(failed_events),
    )


def list_admin_audit_events(
    session: Session,
    *,
    page: int,
    page_size: int,
    subject_user_id: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    model_name: str | None = None,
    token_group: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    include_historical_unowned: bool = False,
) -> AuditEventPage:
    return _list_audit_events(
        session,
        page=page,
        page_size=page_size,
        subject_user_id=subject_user_id,
        event_type=event_type,
        status=status,
        model_name=model_name,
        token_group=token_group,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        created_from=created_from,
        created_to=created_to,
        include_historical_unowned=include_historical_unowned,
    )


def get_admin_audit_event(session: Session, event_id: str) -> AuditEvent:
    event = session.get(AuditEvent, event_id)
    if event is None:
        raise NotFoundError("审计事件不存在")
    return event


def _list_audit_events(
    session: Session,
    *,
    page: int,
    page_size: int,
    subject_user_id: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    model_name: str | None = None,
    token_group: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    include_historical_unowned: bool,
) -> AuditEventPage:
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    start = (page - 1) * page_size
    conditions = []
    if include_historical_unowned:
        conditions.append(AuditEvent.subject_user_id.is_(None))
    elif subject_user_id is not None:
        conditions.append(AuditEvent.subject_user_id == subject_user_id)
    if event_type:
        conditions.append(AuditEvent.event_type == event_type)
    if status:
        conditions.append(AuditEvent.status == status)
    if model_name:
        conditions.append(AuditEvent.model_name == model_name)
    if token_group:
        conditions.append(AuditEvent.new_api_token_group == token_group)
    if resource_type:
        conditions.append(AuditEvent.resource_type == resource_type)
    if resource_id:
        conditions.append(AuditEvent.resource_id == resource_id)
    if request_id:
        conditions.append(
            or_(
                AuditEvent.atelier_request_id == request_id,
                AuditEvent.new_api_request_id == request_id,
                AuditEvent.new_api_upstream_request_id == request_id,
            )
        )
    if created_from is not None:
        conditions.append(AuditEvent.created_at >= created_from)
    if created_to is not None:
        conditions.append(AuditEvent.created_at <= created_to)

    count_stmt = select(func.count()).select_from(AuditEvent)
    stmt = select(AuditEvent).order_by(desc(AuditEvent.created_at), desc(AuditEvent.id))
    for condition in conditions:
        count_stmt = count_stmt.where(condition)
        stmt = stmt.where(condition)

    total = session.scalar(count_stmt) or 0
    items = session.scalars(stmt.offset(start).limit(page_size)).all()
    return AuditEventPage(items=list(items), total=int(total), page=page, page_size=page_size)
