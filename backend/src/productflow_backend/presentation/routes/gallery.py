from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from productflow_backend.application.audit_logs import record_admin_user_content_access
from productflow_backend.application.auth_sessions import Viewer
from productflow_backend.application.gallery import (
    delete_gallery_entry,
    get_gallery_entry,
    import_gallery_entry_to_image_session,
    list_gallery_entries,
    report_gallery_entry,
    save_generated_asset_to_gallery,
)
from productflow_backend.application.product_workflow.user_templates import (
    import_public_user_canvas_template,
    list_public_user_canvas_templates,
    share_user_canvas_template,
    unshare_user_canvas_template,
)
from productflow_backend.infrastructure.db.models import UserCanvasTemplate
from productflow_backend.presentation.deps import (
    get_session,
    request_audit_context,
    require_workspace_viewer,
)
from productflow_backend.presentation.schemas.gallery import (
    GalleryEntryListResponse,
    GalleryEntryReportResponse,
    GalleryEntryResponse,
    ReportGalleryEntryRequest,
    SaveGalleryEntryRequest,
    serialize_gallery_entry,
)
from productflow_backend.presentation.schemas.image_sessions import (
    ImageSessionDetailResponse,
    serialize_image_session_detail,
)
from productflow_backend.presentation.schemas.product_workflows import (
    CanvasTemplateListResponse,
    CanvasTemplateSummaryResponse,
    serialize_user_canvas_template_summary,
)

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


def _require_user_viewer(viewer: Viewer) -> Viewer:
    if viewer.kind != "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该操作仅普通用户可用")
    return viewer


@router.get("", response_model=GalleryEntryListResponse)
def list_gallery_entries_endpoint(
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),
) -> GalleryEntryListResponse:
    items = list_gallery_entries(session)
    return GalleryEntryListResponse(items=[serialize_gallery_entry(item) for item in items])


@router.get("/templates", response_model=CanvasTemplateListResponse)
def list_gallery_templates_endpoint(
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),  # noqa: ARG001
) -> CanvasTemplateListResponse:
    items = [
        serialize_user_canvas_template_summary(template) for template in list_public_user_canvas_templates(session)
    ]
    return CanvasTemplateListResponse(items=items)


@router.get("/templates/{template_id}", response_model=CanvasTemplateSummaryResponse)
def get_gallery_template_endpoint(
    template_id: str,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),  # noqa: ARG001
) -> CanvasTemplateSummaryResponse:
    template = session.scalar(
        select(UserCanvasTemplate).where(
            UserCanvasTemplate.id == template_id,
            UserCanvasTemplate.archived_at.is_(None),
            UserCanvasTemplate.is_public.is_(True),
        )
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户模板不存在")
    return serialize_user_canvas_template_summary(template)


@router.post("/templates/{template_id}/share", response_model=CanvasTemplateSummaryResponse)
def share_gallery_template_endpoint(
    template_id: str,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),
) -> CanvasTemplateSummaryResponse:
    user_viewer = _require_user_viewer(viewer)
    template = share_user_canvas_template(
        session,
        template_id=template_id,
        owner_user_id=user_viewer.user_id,
        username=user_viewer.principal.username,
    )
    return serialize_user_canvas_template_summary(template)


@router.delete("/templates/{template_id}/share", response_model=CanvasTemplateSummaryResponse)
def unshare_gallery_template_endpoint(
    template_id: str,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),
) -> CanvasTemplateSummaryResponse:
    user_viewer = _require_user_viewer(viewer)
    template = unshare_user_canvas_template(
        session,
        template_id=template_id,
        owner_user_id=user_viewer.user_id,
    )
    return serialize_user_canvas_template_summary(template)


@router.post(
    "/templates/{template_id}/import",
    response_model=CanvasTemplateSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_gallery_template_endpoint(
    template_id: str,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),
) -> CanvasTemplateSummaryResponse:
    user_viewer = _require_user_viewer(viewer)
    template = import_public_user_canvas_template(
        session,
        template_id=template_id,
        owner_user_id=user_viewer.user_id,
    )
    return serialize_user_canvas_template_summary(template)


@router.get("/{entry_id}", response_model=GalleryEntryResponse)
def get_gallery_entry_endpoint(
    entry_id: str,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),  # noqa: ARG001
) -> GalleryEntryResponse:
    return serialize_gallery_entry(get_gallery_entry(session, entry_id))


@router.post("", response_model=GalleryEntryResponse, status_code=status.HTTP_201_CREATED)
def save_gallery_entry_endpoint(
    payload: SaveGalleryEntryRequest,
    response: Response,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),
) -> GalleryEntryResponse:
    result = save_generated_asset_to_gallery(
        session,
        viewer=viewer,
        image_session_asset_id=payload.image_session_asset_id,
    )
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return serialize_gallery_entry(result.entry)


@router.post("/{entry_id}/import", response_model=ImageSessionDetailResponse, status_code=status.HTTP_201_CREATED)
def import_gallery_entry_endpoint(
    entry_id: str,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),
) -> ImageSessionDetailResponse:
    user_viewer = _require_user_viewer(viewer)
    imported = import_gallery_entry_to_image_session(session, viewer=user_viewer, entry_id=entry_id)
    return serialize_image_session_detail(imported)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gallery_entry_endpoint(
    entry_id: str,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),
    audit_context=Depends(request_audit_context),
) -> Response:
    result = delete_gallery_entry(session, viewer=viewer, entry_id=entry_id)
    if result.requires_admin_audit and result.target_user_id is not None:
        record_admin_user_content_access(
            session,
            principal=viewer.principal,
            target_user_id=result.target_user_id,
            action="delete_gallery_entry",
            resource_type="gallery_entry",
            resource_id=entry_id,
            request_context=audit_context,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{entry_id}/report", response_model=GalleryEntryReportResponse, status_code=status.HTTP_201_CREATED)
def report_gallery_entry_endpoint(
    entry_id: str,
    payload: ReportGalleryEntryRequest,
    session: Session = Depends(get_session),
    viewer: Viewer = Depends(require_workspace_viewer),
) -> GalleryEntryReportResponse:
    report = report_gallery_entry(
        session,
        viewer=viewer,
        entry_id=entry_id,
        reason_code=payload.reason_code,
        reason_text=payload.reason_text,
    )
    return GalleryEntryReportResponse(
        id=report.id,
        entry_id=report.entry_id,
        reporter_user_id=report.reporter_user_id,
        reason_code=report.reason_code,
        reason_text=report.reason_text,
        status=report.status,
        created_at=report.created_at,
    )
