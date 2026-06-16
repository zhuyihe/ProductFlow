from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from productflow_backend.application.auth_sessions import Principal
from productflow_backend.infrastructure.db.models import AuditLog


@dataclass(frozen=True, slots=True)
class AuditRequestContext:
    client_address: str | None = None
    user_agent: str | None = None


def record_admin_user_content_access(
    session: Session,
    *,
    principal: Principal,
    target_user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    request_context: AuditRequestContext | None = None,
) -> None:
    if not principal.is_admin or not target_user_id:
        return
    admin_user_id = principal.new_api_user_id or "emergency-admin"
    if admin_user_id == target_user_id:
        return
    context = request_context or AuditRequestContext()

    session.add(
        AuditLog(
            admin_user_id=admin_user_id,
            admin_session_id=principal.session_id,
            admin_username=principal.username,
            target_user_id=target_user_id,
            action=action[:80],
            resource_type=resource_type[:80],
            resource_id=resource_id[:120],
            client_address=context.client_address[:255] if context.client_address else None,
            user_agent=context.user_agent,
        )
    )
    session.commit()
