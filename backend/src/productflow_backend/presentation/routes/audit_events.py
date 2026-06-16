from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from productflow_backend.application.audit_events import (
    create_audit_event,
    get_admin_audit_event,
    list_admin_audit_events,
    list_user_audit_events,
    summarize_user_audit_events,
)
from productflow_backend.application.auth_sessions import Principal
from productflow_backend.presentation.deps import (
    current_workspace_owner_user_id,
    get_session,
    require_admin_audit_principal,
    require_workspace_principal,
)
from productflow_backend.presentation.schemas.audit_events import (
    AdminContentViewRequest,
    AuditEventListResponse,
    AuditEventResponse,
    AuditEventSummaryResponse,
    serialize_audit_event,
    serialize_audit_event_page,
    serialize_audit_event_summary,
)

usage_router = APIRouter(
    prefix="/api/usage",
    tags=["usage"],
    dependencies=[Depends(require_workspace_principal)],
)
admin_router = APIRouter(
    prefix="/api/admin/audit",
    tags=["admin-audit"],
    dependencies=[Depends(require_admin_audit_principal)],
)


@usage_router.get("/events", response_model=AuditEventListResponse)
def list_usage_events_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    event_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    model_name: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    session: Session = Depends(get_session),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
) -> AuditEventListResponse:
    page_result = list_user_audit_events(
        session,
        subject_user_id=owner_user_id,
        page=page,
        page_size=page_size,
        event_type=event_type,
        status=status_filter,
        model_name=model_name,
        resource_type=resource_type,
        resource_id=resource_id,
        created_from=created_from,
        created_to=created_to,
    )
    return serialize_audit_event_page(page_result)


@usage_router.get("/summary", response_model=AuditEventSummaryResponse)
def get_usage_summary_endpoint(
    session: Session = Depends(get_session),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
) -> AuditEventSummaryResponse:
    return serialize_audit_event_summary(summarize_user_audit_events(session, subject_user_id=owner_user_id))


@admin_router.get("/events", response_model=AuditEventListResponse)
def list_admin_audit_events_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    subject_user_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    model_name: str | None = Query(default=None),
    token_group: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    historical_unowned: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> AuditEventListResponse:
    page_result = list_admin_audit_events(
        session,
        page=page,
        page_size=page_size,
        subject_user_id=subject_user_id,
        event_type=event_type,
        status=status_filter,
        model_name=model_name,
        token_group=token_group,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        created_from=created_from,
        created_to=created_to,
        include_historical_unowned=historical_unowned,
    )
    return serialize_audit_event_page(page_result)


@admin_router.get("/events/{event_id}", response_model=AuditEventResponse)
def get_admin_audit_event_endpoint(
    event_id: str,
    session: Session = Depends(get_session),
) -> AuditEventResponse:
    return serialize_audit_event(get_admin_audit_event(session, event_id))


@admin_router.post(
    "/content-view",
    response_model=AuditEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_content_view_event_endpoint(
    payload: AdminContentViewRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_admin_audit_principal),
) -> AuditEventResponse:
    source_event = get_admin_audit_event(session, payload.event_id) if payload.event_id else None
    if source_event is not None and (
        source_event.resource_type != payload.resource_type or source_event.resource_id != payload.resource_id
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="内容查看资源与来源审计事件不匹配")
    event = create_audit_event(
        session,
        event_type="admin_content_view",
        principal=principal,
        subject_user_id=source_event.subject_user_id if source_event else None,
        subject_username=source_event.subject_username if source_event else None,
        status="succeeded",
        source="atelier",
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        parent_resource_type=source_event.resource_type if source_event else None,
        parent_resource_id=source_event.resource_id if source_event else None,
        metadata_json={"source_event_id": source_event.id} if source_event else None,
    )
    session.commit()
    session.refresh(event)
    return serialize_audit_event(event)
