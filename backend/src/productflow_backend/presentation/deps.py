from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from productflow_backend.application.audit_logs import AuditRequestContext
from productflow_backend.application.auth_sessions import (
    AUTH_SESSION_COOKIE_KEY,
    Principal,
    Viewer,
    build_viewer,
    load_principal,
    principal_workspace_owner_user_id,
)
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
    principal: Principal = Depends(require_admin_principal),
) -> Principal:
    return principal


def require_workspace_principal(principal: Principal | None = Depends(current_principal)) -> Principal:
    return require_principal(principal)


def require_workspace_viewer(principal: Principal = Depends(require_workspace_principal)) -> Viewer:
    return build_viewer(principal)


def require_admin(
    principal: Principal = Depends(require_admin_principal),
) -> None:
    return None


def current_workspace_owner_user_id(principal: Principal = Depends(require_workspace_principal)) -> str:
    return principal_workspace_owner_user_id(principal)


def request_audit_context(request: Request) -> AuditRequestContext:
    client_address = request.client.host if request.client else None
    return AuditRequestContext(
        client_address=client_address,
        user_agent=request.headers.get("user-agent"),
    )


def require_deletion_enabled() -> None:
    if not get_runtime_settings().deletion_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="删除功能已关闭，请联系管理员")
