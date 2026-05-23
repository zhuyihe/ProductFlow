from __future__ import annotations

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    admin_key: str = Field(default="")


class SessionResponse(BaseModel):
    ok: bool = True


class SessionStateResponse(BaseModel):
    authenticated: bool
    access_required: bool
    principal_kind: str | None = None
    username: str | None = None
    new_api_user_id: str | None = None
    new_api_token_id: str | None = None
    sso_start_url: str | None = None
