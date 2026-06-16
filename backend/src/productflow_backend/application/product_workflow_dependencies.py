from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from productflow_backend.infrastructure.image.base import ImageProvider
from productflow_backend.infrastructure.image.factory import get_image_provider
from productflow_backend.infrastructure.poster.renderer import PosterRenderer
from productflow_backend.infrastructure.provider_config import ProviderCredentialOverride
from productflow_backend.infrastructure.text.base import TextProvider
from productflow_backend.infrastructure.text.factory import get_text_provider

TextProviderResolver = Callable[[str | None], TextProvider]
ImageProviderResolver = Callable[[str | None], ImageProvider]
PosterRendererFactory = Callable[[Path], PosterRenderer]


def _default_text_provider(atelier_request_id: str | None = None) -> TextProvider:
    del atelier_request_id
    return get_text_provider()


def _default_image_provider(atelier_request_id: str | None = None) -> ImageProvider:
    del atelier_request_id
    return get_image_provider()


@dataclass(frozen=True, slots=True)
class WorkflowExecutionDependencies:
    """Explicit dependency seam for workflow execution provider/renderer adapters."""

    text_provider_resolver: TextProviderResolver = _default_text_provider
    image_provider_resolver: ImageProviderResolver = _default_image_provider
    poster_renderer_factory: PosterRendererFactory = PosterRenderer

    def text_provider(self, atelier_request_id: str | None = None) -> TextProvider:
        try:
            return self.text_provider_resolver(atelier_request_id)
        except TypeError:
            return self.text_provider_resolver()  # type: ignore[call-arg]

    def image_provider(self, atelier_request_id: str | None = None) -> ImageProvider:
        try:
            return self.image_provider_resolver(atelier_request_id)
        except TypeError:
            return self.image_provider_resolver()  # type: ignore[call-arg]

    def poster_renderer(self, font_path: Path) -> PosterRenderer:
        return self.poster_renderer_factory(font_path)


def default_workflow_execution_dependencies(
    credential_override: ProviderCredentialOverride | None = None,
) -> WorkflowExecutionDependencies:
    if credential_override is None:
        return WorkflowExecutionDependencies()

    def text_provider_resolver(atelier_request_id: str | None = None) -> TextProvider:
        effective_override = (
            credential_override
            if atelier_request_id is None
            else ProviderCredentialOverride(
                api_key=credential_override.api_key,
                base_url=credential_override.base_url,
                image_model=credential_override.image_model,
                text_model=credential_override.text_model,
                token_group=credential_override.token_group,
                atelier_request_id=atelier_request_id,
            )
        )
        return get_text_provider(effective_override)

    def image_provider_resolver(atelier_request_id: str | None = None) -> ImageProvider:
        effective_override = (
            credential_override
            if atelier_request_id is None
            else ProviderCredentialOverride(
                api_key=credential_override.api_key,
                base_url=credential_override.base_url,
                image_model=credential_override.image_model,
                text_model=credential_override.text_model,
                token_group=credential_override.token_group,
                atelier_request_id=atelier_request_id,
            )
        )
        return get_image_provider(effective_override)

    return WorkflowExecutionDependencies(
        text_provider_resolver=text_provider_resolver,
        image_provider_resolver=image_provider_resolver,
    )
