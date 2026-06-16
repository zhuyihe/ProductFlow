from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import urljoin

import httpx

from productflow_backend.config import get_runtime_settings

BillingLookupStatus = Literal["found", "not_found", "lookup_failed", "skipped"]


@dataclass(frozen=True, slots=True)
class NewApiLogFacts:
    log_id: str | None
    request_id: str | None
    upstream_request_id: str | None
    token_id: str | None
    token_name: str | None
    token_group: str | None
    model_name: str | None
    quota: Decimal | None
    prompt_tokens: int | None
    completion_tokens: int | None
    use_time_seconds: Decimal | None
    log_type: int | None


@dataclass(frozen=True, slots=True)
class NewApiUsageLookupResult:
    status: BillingLookupStatus
    facts: NewApiLogFacts | None = None


def lookup_new_api_usage_by_atelier_request_id(
    *,
    new_api_token: str | None,
    atelier_request_id: str | None,
) -> NewApiUsageLookupResult:
    token = (new_api_token or "").strip()
    request_id = (atelier_request_id or "").strip()
    settings = get_runtime_settings()
    base_url = (settings.new_api_base_url or "").strip()
    if not token or not request_id or not base_url:
        return NewApiUsageLookupResult(status="skipped")

    endpoint = urljoin(f"{base_url.rstrip('/')}/", "api/log/token")
    try:
        response = httpx.get(
            endpoint,
            params={"atelier_request_id": request_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings.new_api_sso_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return NewApiUsageLookupResult(status="lookup_failed")

    if not isinstance(payload, dict) or payload.get("success") is not True:
        return NewApiUsageLookupResult(status="lookup_failed")
    items = payload.get("data")
    if not isinstance(items, list) or not items:
        return NewApiUsageLookupResult(status="not_found")
    facts = _facts_from_log_item(items[0])
    if facts is None:
        return NewApiUsageLookupResult(status="lookup_failed")
    return NewApiUsageLookupResult(status="found", facts=facts)


def _facts_from_log_item(item: Any) -> NewApiLogFacts | None:
    if not isinstance(item, dict):
        return None
    return NewApiLogFacts(
        log_id=_optional_text(item.get("id")),
        request_id=_optional_text(item.get("request_id")),
        upstream_request_id=_optional_text(item.get("upstream_request_id")),
        token_id=_optional_text(item.get("token_id")),
        token_name=_optional_text(item.get("token_name")),
        token_group=_optional_text(item.get("group")),
        model_name=_optional_text(item.get("model_name")),
        quota=_optional_decimal(item.get("quota")),
        prompt_tokens=_optional_int(item.get("prompt_tokens")),
        completion_tokens=_optional_int(item.get("completion_tokens")),
        use_time_seconds=_optional_decimal(item.get("use_time")),
        log_type=_optional_int(item.get("type")),
    )


def _optional_text(value: Any) -> str | None:
    normalized = "" if value is None else str(value).strip()
    return normalized or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return None
