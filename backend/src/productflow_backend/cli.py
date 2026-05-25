from __future__ import annotations

import argparse
import sys
from datetime import timedelta

from productflow_backend.application.auth_sessions import AUTH_SESSION_COOKIE_KEY
from productflow_backend.config import get_settings
from productflow_backend.infrastructure.db.models import AuthSession, new_id, utcnow
from productflow_backend.infrastructure.db.session import get_session_factory
from productflow_backend.presentation.session import build_signed_session_cookie_value


def bootstrap_admin_session(*, new_api_user_id: str, new_api_username: str, ttl_hours: int) -> tuple[str, str]:
    if not new_api_user_id.strip():
        raise ValueError("new_api_user_id 不能为空")
    if not new_api_username.strip():
        raise ValueError("new_api_username 不能为空")
    if ttl_hours <= 0:
        raise ValueError("ttl_hours 必须大于 0")

    settings = get_settings()
    session_factory = get_session_factory()
    session = session_factory()
    try:
        auth_session = AuthSession(
            id=new_id(),
            principal_kind="admin",
            new_api_user_id=new_api_user_id.strip(),
            username=new_api_username.strip(),
            role="10",
            expires_at=utcnow() + timedelta(hours=ttl_hours),
        )
        session.add(auth_session)
        session.commit()
        cookie_value = build_signed_session_cookie_value(
            {AUTH_SESSION_COOKIE_KEY: auth_session.id},
            secret_key=settings.session_secret,
        )
        return auth_session.id, cookie_value
    finally:
        session.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atelier-backend")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bootstrap = subparsers.add_parser("bootstrap-admin", help="Create a temporary admin session")
    bootstrap.add_argument("--new-api-user-id", required=True)
    bootstrap.add_argument("--new-api-username", required=True)
    bootstrap.add_argument("--ttl-hours", type=int, default=24)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "bootstrap-admin":
        session_id, cookie_value = bootstrap_admin_session(
            new_api_user_id=args.new_api_user_id,
            new_api_username=args.new_api_username,
            ttl_hours=args.ttl_hours,
        )
        print(f"session_id={session_id}")
        print("cookie_name=session")
        print("warning=cookie_value is equivalent to an admin login secret; do not store it in logs", file=sys.stderr)
        print(f"cookie_value={cookie_value}", file=sys.stderr)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
