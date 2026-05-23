from __future__ import annotations

from productflow_backend.infrastructure.provider_config import ProviderCredentialOverride, resolve_text_provider_config
from productflow_backend.infrastructure.text.base import TextProvider
from productflow_backend.infrastructure.text.mock_provider import MockTextProvider
from productflow_backend.infrastructure.text.openai_provider import OpenAITextProvider


def get_text_provider(
    credential_override: ProviderCredentialOverride | None = None,
) -> TextProvider:
    """根据统一供应商用途绑定选择文本生成供应商。"""
    provider_config = resolve_text_provider_config(credential_override)
    if provider_config.provider_kind == "openai":
        return OpenAITextProvider(provider_config)
    return MockTextProvider()
