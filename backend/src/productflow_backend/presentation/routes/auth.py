from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from productflow_backend.application.auth_sessions import (
    AUTH_SESSION_COOKIE_KEY,
    create_admin_session,
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
from productflow_backend.config import get_runtime_settings, get_settings
from productflow_backend.presentation.deps import get_session
from productflow_backend.presentation.schemas.auth import (
    SessionCreateRequest,
    SessionResponse,
    SessionStateResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
browser_router = APIRouter(tags=["auth"])


@router.post("/session", response_model=SessionResponse)
def create_session(
    payload: SessionCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> SessionResponse:
    if not get_runtime_settings().admin_access_required:
        return SessionResponse()
    settings = get_settings()
    if payload.admin_key != settings.admin_access_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员密钥不正确")
    request.session.clear()
    auth_session = create_admin_session(session)
    request.session[AUTH_SESSION_COOKIE_KEY] = auth_session.id
    return SessionResponse()


@router.get("/session", response_model=SessionStateResponse, response_model_exclude_none=True)
def get_session_state(
    request: Request,
    session: Session = Depends(get_session),
) -> SessionStateResponse:
    runtime_settings = get_runtime_settings()
    access_required = runtime_settings.admin_access_required
    auth_session_id = request.session.get(AUTH_SESSION_COOKIE_KEY)
    principal = load_principal(session, auth_session_id)
    return SessionStateResponse(
        authenticated=not access_required or bool(principal) or _has_legacy_admin_session(request, auth_session_id),
        access_required=access_required,
        principal_kind=principal.kind if principal is not None else None,
        username=principal.username if principal is not None else None,
        new_api_user_id=principal.new_api_user_id if principal is not None else None,
        new_api_token_id=principal.new_api_token_id if principal is not None else None,
        sso_start_url=_configured_sso_start_url(runtime_settings),
    )


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
    except NewApiSsoError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    auth_session = create_new_api_user_session(session, claims)
    request.session.clear()
    request.session[AUTH_SESSION_COOKIE_KEY] = auth_session.id
    return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)


def _configured_sso_start_url(settings) -> str | None:
    if not is_new_api_sso_configured(settings):
        return None
    return new_api_sso_start_url(settings)


def _has_legacy_admin_session(request: Request, auth_session_id: str | None) -> bool:
    return not auth_session_id and bool(request.session.get("is_authenticated"))
