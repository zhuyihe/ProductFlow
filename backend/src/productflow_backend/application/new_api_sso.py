from __future__ import annotations

from urllib.parse import urljoin

import httpx

from productflow_backend.application.auth_sessions import NewApiSessionClaims
from productflow_backend.config import Settings


class NewApiSsoError(RuntimeError):
    pass


def is_new_api_sso_configured(settings: Settings) -> bool:
    return bool((settings.new_api_sso_verify_url or settings.new_api_base_url) and settings.new_api_sso_shared_secret)


def new_api_sso_start_url(settings: Settings) -> str | None:
    return settings.new_api_sso_start_url


def verify_new_api_sso_ticket(ticket: str, *, settings: Settings) -> NewApiSessionClaims:
    if not ticket.strip():
        raise NewApiSsoError("缺少登录票据")
    if not is_new_api_sso_configured(settings):
        raise NewApiSsoError("New API SSO 未配置")

    verify_url = _verify_url(settings)
    try:
        response = httpx.post(
            verify_url,
            json={"ticket": ticket},
            headers={"Authorization": f"Bearer {settings.new_api_sso_shared_secret}"},
            timeout=settings.new_api_sso_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise NewApiSsoError("New API SSO 校验失败") from exc

    if response.status_code != 200:
        raise NewApiSsoError("New API SSO 票据无效或已过期")

    payload = _unwrap_payload(response.json())
    token_payload = _first_mapping(payload, "token", "token_info", "productflow_token")
    productflow_payload = _first_mapping(payload, "productflow", "product_flow", "atelier")
    user_id = _first_text(payload, "user_id", "id", "uid")
    if user_id is None:
        raise NewApiSsoError("New API SSO 响应缺少用户信息")
    image_model = (
        _first_text(payload, "image_model", "selected_image_model")
        or _first_text(productflow_payload, "image_model", "selected_image_model")
        or _first_text(token_payload, "image_model", "selected_image_model", "model")
    )
    image_models = (
        _first_text_list(payload, "image_models", "available_image_models", "models")
        or _first_text_list(productflow_payload, "image_models", "available_image_models", "models")
        or _first_text_list(token_payload, "image_models", "available_image_models", "models")
        or ((image_model,) if image_model else ())
    )

    return NewApiSessionClaims(
        user_id=user_id,
        username=_first_text(payload, "username", "name"),
        email=_first_text(payload, "email"),
        group=_first_text(payload, "group", "user_group"),
        role=_first_text(payload, "role"),
        token=_first_text(payload, "token", "api_key", "key") or _first_text(token_payload, "token", "api_key", "key"),
        token_id=_first_text(payload, "token_id") or _first_text(token_payload, "id", "token_id"),
        token_name=_first_text(payload, "token_name") or _first_text(token_payload, "name", "token_name"),
        token_group=(
            _first_text(payload, "token_group", "selected_token_group")
            or _first_text(productflow_payload, "token_group", "selected_token_group")
            or _first_text(token_payload, "group", "token_group")
        ),
        image_model=image_model,
        image_models=tuple(image_models),
        expires_in_seconds=_first_int(payload, "expires_in", "session_expires_in"),
    )


def _verify_url(settings: Settings) -> str:
    if settings.new_api_sso_verify_url:
        return settings.new_api_sso_verify_url
    assert settings.new_api_base_url is not None
    return urljoin(f"{settings.new_api_base_url.rstrip('/')}/", settings.new_api_sso_verify_path.lstrip("/"))


def _unwrap_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise NewApiSsoError("New API SSO 响应格式无效")
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def _first_mapping(payload: dict | None, *keys: str) -> dict | None:
    if payload is None:
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return None


def _first_text(payload: dict | None, *keys: str) -> str | None:
    if payload is None:
        return None
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, dict | list | tuple | set):
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None


def _first_text_list(payload: dict | None, *keys: str) -> tuple[str, ...] | None:
    if payload is None:
        return None
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        items: list[object]
        if isinstance(value, str):
            items = [part.strip() for part in value.split(",")]
        elif isinstance(value, list | tuple | set):
            items = list(value)
        else:
            continue
        normalized: list[str] = []
        for item in items:
            if isinstance(item, dict | list | tuple | set):
                continue
            text = str(item).strip()
            if text and text not in normalized:
                normalized.append(text)
        if normalized:
            return tuple(normalized)
    return None


def _first_int(payload: dict | None, *keys: str) -> int | None:
    if payload is None:
        return None
    for key in keys:
        value = payload.get(key)
        if value is None or value == "":
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return None
