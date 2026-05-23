from __future__ import annotations

from productflow_backend.application.auth_sessions import NewApiSessionClaims, Principal
from productflow_backend.application.provider_runtime import ProviderExecutionContext


def test_token_bearing_dataclass_repr_hides_raw_token() -> None:
    principal = Principal(
        session_id="session-1",
        kind="user",
        new_api_user_id="42",
        username="alice",
        email=None,
        group="default",
        role="user",
        new_api_token_id="77",
        new_api_token_name="ProductFlow",
        new_api_token="sk-principal-token",
    )
    claims = NewApiSessionClaims(
        user_id="42",
        username="alice",
        email=None,
        group="default",
        role="user",
        token="sk-claims-token",
        token_id="77",
        token_name="ProductFlow",
    )
    context = ProviderExecutionContext(
        new_api_user_id="42",
        new_api_token_id="77",
        new_api_token_name="ProductFlow",
        new_api_token="sk-context-token",
    )

    principal_repr = repr(principal)
    claims_repr = repr(claims)
    context_repr = repr(context)

    assert "sk-principal-token" not in principal_repr
    assert "new_api_token=" not in principal_repr
    assert "sk-claims-token" not in claims_repr
    assert "token=" not in claims_repr
    assert "sk-context-token" not in context_repr
    assert "new_api_token=" not in context_repr
