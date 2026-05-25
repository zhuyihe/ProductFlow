from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from productflow_backend.infrastructure.db.models import AuthSession, new_id

AUTH_SESSION_COOKIE_KEY = "auth_session_id"
DEFAULT_AUTH_SESSION_TTL_DAYS = 14
GUEST_ACCOUNT_DISABLED_CODE = "guest_account_disabled"
logger = logging.getLogger(__name__)


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
    new_api_token: str | None = field(repr=False)
    new_api_token_group: str | None = None
    new_api_image_model: str | None = None
    new_api_image_models: tuple[str, ...] = field(default_factory=tuple)

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
class Viewer:
    kind: Literal["admin", "user"]
    user_id: str
    principal: Principal


class PrincipalIntegrityError(RuntimeError):
    pass


def build_viewer(principal: Principal) -> Viewer:
    if principal.kind == "admin":
        return Viewer(kind="admin", user_id=principal.session_id, principal=principal)
    if principal.kind == "user":
        user_id = (principal.new_api_user_id or "").strip()
        if user_id:
            return Viewer(kind="user", user_id=user_id, principal=principal)
    raise PrincipalIntegrityError("Invalid authenticated principal")


@dataclass(frozen=True, slots=True)
class NewApiSessionClaims:
    user_id: str
    username: str | None = None
    email: str | None = None
    group: str | None = None
    role: str | None = None
    token: str | None = field(default=None, repr=False)
    token_id: str | None = None
    token_name: str | None = None
    token_group: str | None = None
    image_model: str | None = None
    image_models: tuple[str, ...] = field(default_factory=tuple)
    expires_in_seconds: int | None = None


class InvalidNewApiRoleError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def principal_kind_from_new_api_role(role: str | None) -> str:
    normalized_role = (role or "").strip()
    if not normalized_role:
        logger.warning("Missing ProductFlow SSO role; treating session as ordinary user")
        return "user"
    try:
        role_value = int(normalized_role)
    except ValueError:
        logger.warning("Invalid ProductFlow SSO role %s; treating session as ordinary user", normalized_role)
        return "user"
    if role_value == 0:
        raise InvalidNewApiRoleError(GUEST_ACCOUNT_DISABLED_CODE)
    if role_value == 1:
        return "user"
    if role_value >= 10:
        return "admin"
    logger.warning("Unexpected ProductFlow SSO role %s; treating session as ordinary user", normalized_role)
    return "user"


def normalize_image_model_options(
    image_models: tuple[str, ...] | list[str] | None,
    selected_model: str | None = None,
) -> tuple[str, ...]:
    models: list[str] = []
    if isinstance(image_models, list | tuple):
        for model in image_models:
            normalized = str(model).strip()
            if normalized and normalized not in models:
                models.append(normalized)
    selected = (selected_model or "").strip()
    if selected and selected in models:
        models.remove(selected)
    if selected:
        models.insert(0, selected)
    return tuple(models)


def create_new_api_user_session(session: Session, claims: NewApiSessionClaims) -> AuthSession:
    ttl = (
        claims.expires_in_seconds
        if claims.expires_in_seconds is not None
        else DEFAULT_AUTH_SESSION_TTL_DAYS * 24 * 60 * 60
    )
    auth_session = AuthSession(
        id=new_id(),
        principal_kind=principal_kind_from_new_api_role(claims.role),
        new_api_user_id=claims.user_id,
        username=claims.username,
        email=claims.email,
        group=claims.group,
        role=claims.role,
        new_api_token=claims.token,
        new_api_token_id=claims.token_id,
        new_api_token_name=claims.token_name,
        new_api_token_group=claims.token_group,
        new_api_image_model=claims.image_model,
        new_api_image_models=list(normalize_image_model_options(claims.image_models, claims.image_model)) or None,
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
        new_api_token_group=auth_session.new_api_token_group,
        new_api_image_model=auth_session.new_api_image_model,
        new_api_image_models=normalize_image_model_options(
            auth_session.new_api_image_models,
            auth_session.new_api_image_model,
        ),
    )
