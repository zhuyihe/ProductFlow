from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from productflow_backend.application.audit_logs import record_admin_user_content_access
from productflow_backend.application.auth_sessions import (
    AUTH_SESSION_COOKIE_KEY,
    InvalidNewApiRoleError,
    Principal,
    create_new_api_user_session,
    load_principal,
    revoke_auth_session,
)
from productflow_backend.application.new_api_sso import (
    NewApiSsoError,
    is_new_api_sso_configured,
    new_api_sso_start_url,
    verify_new_api_sso_ticket,
)
from productflow_backend.config import get_runtime_settings
from productflow_backend.infrastructure.db.models import AuthSession
from productflow_backend.presentation.deps import (
    get_session,
    request_audit_context,
    require_admin_audit_principal,
)
from productflow_backend.presentation.schemas.auth import SessionResponse, SessionStateResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
browser_router = APIRouter(tags=["auth"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/session", response_model=SessionStateResponse, response_model_exclude_none=True)
def get_session_state(
    request: Request,
    session: Session = Depends(get_session),
) -> SessionStateResponse:
    runtime_settings = get_runtime_settings()
    auth_session_id = request.session.get(AUTH_SESSION_COOKIE_KEY)
    principal = load_principal(session, auth_session_id)
    return SessionStateResponse(
        authenticated=bool(principal),
        principal_kind=principal.kind if principal is not None else None,
        username=principal.username if principal is not None else None,
        new_api_user_id=principal.new_api_user_id if principal is not None else None,
        new_api_token_id=principal.new_api_token_id if principal is not None else None,
        new_api_token_group=principal.new_api_token_group if principal is not None else None,
        new_api_image_model=principal.new_api_image_model if principal is not None else None,
        new_api_image_models=(
            list(principal.new_api_image_models) if principal is not None and principal.new_api_image_models else None
        ),
        new_api_text_model=principal.new_api_text_model if principal is not None else None,
        new_api_text_models=(
            list(principal.new_api_text_models) if principal is not None and principal.new_api_text_models else None
        ),
        sso_start_url=_configured_sso_start_url(runtime_settings),
    )


@router.post("/session", include_in_schema=False)
def create_session_removed() -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


@router.delete("/session", response_model=SessionResponse)
def destroy_session(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> SessionResponse:
    revoke_auth_session(session, request.session.get(AUTH_SESSION_COOKIE_KEY))
    request.session.clear()
    response.delete_cookie("session")
    return SessionResponse()


@admin_router.post("/sessions/{auth_session_id}/revoke", response_model=SessionResponse)
def revoke_auth_session_endpoint(
    auth_session_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_admin_audit_principal),
    audit_context=Depends(request_audit_context),
) -> SessionResponse:
    auth_session = session.get(AuthSession, auth_session_id)
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="登录会话不存在")
    target_user_id = auth_session.new_api_user_id
    revoke_auth_session(session, auth_session_id)
    if target_user_id:
        record_admin_user_content_access(
            session,
            principal=principal,
            target_user_id=target_user_id,
            action="revoke_auth_session",
            resource_type="auth_session",
            resource_id=auth_session_id,
            request_context=audit_context,
        )
    return SessionResponse()


@router.get("/sso/new-api/start", response_model=SessionResponse)
def get_new_api_sso_start() -> SessionResponse:
    settings = get_runtime_settings()
    if not is_new_api_sso_configured(settings):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New API SSO 未配置")
    if not settings.new_api_sso_start_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New API SSO 入口未配置")
    return SessionResponse()


@browser_router.get("/auth/new-api/callback")
def new_api_sso_callback(
    request: Request,
    ticket: str = Query(default=""),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    try:
        claims = verify_new_api_sso_ticket(ticket, settings=get_runtime_settings())
        auth_session = create_new_api_user_session(session, claims)
    except NewApiSsoError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except InvalidNewApiRoleError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    request.session.clear()
    request.session[AUTH_SESSION_COOKIE_KEY] = auth_session.id
    return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)


def _configured_sso_start_url(settings) -> str | None:
    if not is_new_api_sso_configured(settings):
        return None
    return new_api_sso_start_url(settings)
