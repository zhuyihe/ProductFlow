from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from productflow_backend.application.audit_logs import AuditRequestContext
from productflow_backend.application.auth_sessions import (
    AUTH_SESSION_COOKIE_KEY,
    Principal,
    load_principal,
    principal_owner_user_id,
)
from productflow_backend.application.new_api_sso import is_new_api_sso_configured
from productflow_backend.config import get_runtime_settings
from productflow_backend.infrastructure.db.session import get_db_session


def get_session(session: Session = Depends(get_db_session)) -> Session:
    return session


def current_principal(request: Request, session: Session = Depends(get_session)) -> Principal | None:
    return load_principal(session, request.session.get(AUTH_SESSION_COOKIE_KEY))


def require_principal(principal: Principal | None = Depends(current_principal)) -> Principal:
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return principal


def require_admin_principal(principal: Principal = Depends(require_principal)) -> Principal:
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return principal


def require_admin_audit_principal(
    request: Request,
    session: Session = Depends(get_session),
) -> Principal:
    if not get_runtime_settings().admin_access_required:
        return Principal(
            session_id="public-workspace",
            kind="admin",
            new_api_user_id=None,
            username="public",
            email=None,
            group=None,
            role="admin",
            new_api_token_id=None,
            new_api_token_name=None,
            new_api_token=None,
        )
    auth_session_id = request.session.get(AUTH_SESSION_COOKIE_KEY)
    principal = load_principal(session, auth_session_id)
    if principal is not None:
        if principal.is_admin:
            return principal
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    if auth_session_id or not request.session.get("is_authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return Principal(
        session_id="legacy-admin-session",
        kind="admin",
        new_api_user_id=None,
        username="admin",
        email=None,
        group=None,
        role="admin",
        new_api_token_id=None,
        new_api_token_name=None,
        new_api_token=None,
    )


def require_workspace_principal(principal: Principal | None = Depends(current_principal)) -> Principal:
    if principal is not None:
        return principal
    if is_new_api_sso_configured(get_runtime_settings()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    if not get_runtime_settings().admin_access_required:
        return Principal(
            session_id="public-workspace",
            kind="admin",
            new_api_user_id=None,
            username="public",
            email=None,
            group=None,
            role="admin",
            new_api_token_id=None,
            new_api_token_name=None,
            new_api_token=None,
        )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")


def require_admin(
    request: Request,
    session: Session = Depends(get_session),
) -> None:
    if not get_runtime_settings().admin_access_required:
        return
    auth_session_id = request.session.get(AUTH_SESSION_COOKIE_KEY)
    principal = load_principal(session, auth_session_id)
    if principal is not None:
        if principal.is_admin:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    if auth_session_id or not request.session.get("is_authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")


def current_owner_user_id(principal: Principal = Depends(require_workspace_principal)) -> str | None:
    return principal_owner_user_id(principal)


def request_audit_context(request: Request) -> AuditRequestContext:
    client_address = request.client.host if request.client else None
    return AuditRequestContext(
        client_address=client_address,
        user_agent=request.headers.get("user-agent"),
    )


def require_deletion_enabled() -> None:
    if not get_runtime_settings().deletion_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="删除功能已关闭，请联系管理员")
