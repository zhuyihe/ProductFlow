from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from productflow_backend.infrastructure.db.models import AuthSession, new_id

AUTH_SESSION_COOKIE_KEY = "auth_session_id"
DEFAULT_AUTH_SESSION_TTL_DAYS = 14


@dataclass(frozen=True, slots=True)
class Principal:
    session_id: str
    kind: str
    new_api_user_id: str | None
    username: str | None
    email: str | None
    group: str | None
    role: str | None
    new_api_token_id: str | None
    new_api_token_name: str | None
    new_api_token: str | None

    @property
    def is_admin(self) -> bool:
        return self.kind == "admin"

    @property
    def is_user(self) -> bool:
        return self.kind == "user"


def principal_owner_user_id(principal: Principal | None) -> str | None:
    if principal is None or not principal.is_user:
        return None
    normalized = (principal.new_api_user_id or "").strip()
    return normalized or None


@dataclass(frozen=True, slots=True)
class NewApiSessionClaims:
    user_id: str
    username: str | None = None
    email: str | None = None
    group: str | None = None
    role: str | None = None
    token: str | None = None
    token_id: str | None = None
    token_name: str | None = None
    expires_in_seconds: int | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_admin_session(session: Session) -> AuthSession:
    auth_session = AuthSession(
        id=new_id(),
        principal_kind="admin",
        username="admin",
        role="admin",
        expires_at=utc_now() + timedelta(days=DEFAULT_AUTH_SESSION_TTL_DAYS),
    )
    session.add(auth_session)
    session.commit()
    session.refresh(auth_session)
    return auth_session


def create_new_api_user_session(session: Session, claims: NewApiSessionClaims) -> AuthSession:
    ttl = claims.expires_in_seconds or DEFAULT_AUTH_SESSION_TTL_DAYS * 24 * 60 * 60
    auth_session = AuthSession(
        id=new_id(),
        principal_kind="user",
        new_api_user_id=claims.user_id,
        username=claims.username,
        email=claims.email,
        group=claims.group,
        role=claims.role,
        new_api_token=claims.token,
        new_api_token_id=claims.token_id,
        new_api_token_name=claims.token_name,
        expires_at=utc_now() + timedelta(seconds=ttl),
    )
    session.add(auth_session)
    session.commit()
    session.refresh(auth_session)
    return auth_session


def revoke_auth_session(session: Session, auth_session_id: str | None) -> None:
    if not auth_session_id:
        return
    auth_session = session.get(AuthSession, auth_session_id)
    if auth_session is None or auth_session.revoked_at is not None:
        return
    auth_session.revoked_at = utc_now()
    session.commit()


def load_principal(session: Session, auth_session_id: str | None) -> Principal | None:
    if not auth_session_id:
        return None
    auth_session = session.get(AuthSession, auth_session_id)
    if auth_session is None or auth_session.revoked_at is not None:
        return None
    if auth_session.expires_at is not None and _as_utc(auth_session.expires_at) <= utc_now():
        return None
    return Principal(
        session_id=auth_session.id,
        kind=auth_session.principal_kind,
        new_api_user_id=auth_session.new_api_user_id,
        username=auth_session.username,
        email=auth_session.email,
        group=auth_session.group,
        role=auth_session.role,
        new_api_token_id=auth_session.new_api_token_id,
        new_api_token_name=auth_session.new_api_token_name,
        new_api_token=auth_session.new_api_token,
    )
