from __future__ import annotations

from dataclasses import dataclass, field

from productflow_backend.application.auth_sessions import Principal
from productflow_backend.config import get_runtime_settings, resolve_new_api_relay_base_url
from productflow_backend.domain.errors import BusinessValidationError
from productflow_backend.infrastructure.db.models import ImageSessionGenerationTask, WorkflowRun
from productflow_backend.infrastructure.provider_config import ProviderCredentialOverride

MISSING_NEW_API_TOKEN_DETAIL = "当前 ProductFlow 会话缺少 New API token，请从 New API 重新进入 ProductFlow"


@dataclass(frozen=True, slots=True)
class ProviderExecutionContext:
    new_api_user_id: str | None = None
    new_api_token_id: str | None = None
    new_api_token_name: str | None = None
    new_api_token: str | None = field(default=None, repr=False)

    @property
    def enabled(self) -> bool:
        return any(
            value is not None
            for value in (
                self.new_api_user_id,
                self.new_api_token_id,
                self.new_api_token_name,
                self.new_api_token,
            )
        )


def provider_execution_context_from_principal(principal: Principal | None) -> ProviderExecutionContext | None:
    if principal is None:
        return None
    return _provider_execution_context(
        new_api_user_id=principal.new_api_user_id,
        new_api_token_id=principal.new_api_token_id,
        new_api_token_name=principal.new_api_token_name,
        new_api_token=principal.new_api_token,
    )


def interactive_provider_execution_context_from_principal(
    principal: Principal | None,
) -> ProviderExecutionContext | None:
    if principal is None:
        return None
    context = provider_execution_context_from_principal(principal)
    if context is not None and not context.new_api_token:
        raise BusinessValidationError(MISSING_NEW_API_TOKEN_DETAIL)
    return context


def provider_execution_context_from_workflow_run(run: WorkflowRun) -> ProviderExecutionContext | None:
    return _provider_execution_context(
        new_api_user_id=run.new_api_user_id,
        new_api_token_id=run.new_api_token_id,
        new_api_token_name=run.new_api_token_name,
        new_api_token=run.new_api_token,
    )


def provider_execution_context_from_image_generation_task(
    task: ImageSessionGenerationTask,
) -> ProviderExecutionContext | None:
    return _provider_execution_context(
        new_api_user_id=task.new_api_user_id,
        new_api_token_id=task.new_api_token_id,
        new_api_token_name=task.new_api_token_name,
        new_api_token=task.new_api_token,
    )


def provider_execution_context_values(
    context: ProviderExecutionContext | None,
) -> dict[str, str | None]:
    if context is None:
        return {
            "new_api_user_id": None,
            "new_api_token_id": None,
            "new_api_token_name": None,
            "new_api_token": None,
        }
    return {
        "new_api_user_id": context.new_api_user_id,
        "new_api_token_id": context.new_api_token_id,
        "new_api_token_name": context.new_api_token_name,
        "new_api_token": context.new_api_token,
    }


def provider_credential_override_from_context(
    context: ProviderExecutionContext | None,
) -> ProviderCredentialOverride | None:
    if context is None:
        return None
    if not context.new_api_token:
        raise RuntimeError("当前 ProductFlow 会话缺少 New API token")
    relay_base_url = resolve_new_api_relay_base_url(get_runtime_settings())
    if relay_base_url is None:
        raise RuntimeError("New API relay base URL 未配置")
    return ProviderCredentialOverride(
        api_key=context.new_api_token,
        base_url=relay_base_url,
    )


def _provider_execution_context(
    *,
    new_api_user_id: str | None,
    new_api_token_id: str | None,
    new_api_token_name: str | None,
    new_api_token: str | None,
) -> ProviderExecutionContext | None:
    context = ProviderExecutionContext(
        new_api_user_id=new_api_user_id,
        new_api_token_id=new_api_token_id,
        new_api_token_name=new_api_token_name,
        new_api_token=new_api_token,
    )
    if not context.enabled:
        return None
    return context
