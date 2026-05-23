from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from productflow_backend.application.audit_logs import AuditRequestContext, record_admin_user_content_access
from productflow_backend.application.auth_sessions import Principal
from productflow_backend.application.gallery import list_gallery_entries, save_generated_asset_to_gallery
from productflow_backend.presentation.deps import (
    get_session,
    request_audit_context,
    require_admin,
    require_admin_audit_principal,
)
from productflow_backend.presentation.schemas.gallery import (
    GalleryEntryListResponse,
    GalleryEntryResponse,
    SaveGalleryEntryRequest,
    serialize_gallery_entry,
)

router = APIRouter(prefix="/api/gallery", tags=["gallery"], dependencies=[Depends(require_admin)])


@router.get("", response_model=GalleryEntryListResponse)
def list_gallery_entries_endpoint(
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_admin_audit_principal),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> GalleryEntryListResponse:
    items = list_gallery_entries(session)
    for item in items:
        record_admin_user_content_access(
            session,
            principal=principal,
            target_user_id=item.asset.session.owner_user_id,
            action="read",
            resource_type="image_gallery_entry",
            resource_id=item.id,
            request_context=audit_context,
        )
    return GalleryEntryListResponse(items=[serialize_gallery_entry(item) for item in items])


@router.post("", response_model=GalleryEntryResponse, status_code=status.HTTP_201_CREATED)
def save_gallery_entry_endpoint(
    payload: SaveGalleryEntryRequest,
    response: Response,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_admin_audit_principal),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> GalleryEntryResponse:
    result = save_generated_asset_to_gallery(
        session,
        image_session_asset_id=payload.image_session_asset_id,
    )
    if not result.created:
        response.status_code = status.HTTP_200_OK
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=result.entry.asset.session.owner_user_id,
        action="create" if result.created else "read",
        resource_type="image_gallery_entry",
        resource_id=result.entry.id,
        request_context=audit_context,
    )
    return serialize_gallery_entry(result.entry)
