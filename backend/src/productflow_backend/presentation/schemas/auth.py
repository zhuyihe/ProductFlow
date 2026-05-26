from __future__ import annotations

from pydantic import BaseModel


class SessionResponse(BaseModel):
    ok: bool = True


class SessionStateResponse(BaseModel):
    authenticated: bool
    principal_kind: str | None = None
    username: str | None = None
    new_api_user_id: str | None = None
    new_api_token_id: str | None = None
    new_api_token_group: str | None = None
    new_api_image_model: str | None = None
    new_api_image_models: list[str] | None = None
    new_api_text_model: str | None = None
    new_api_text_models: list[str] | None = None
    sso_start_url: str | None = None
