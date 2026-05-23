from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from productflow_backend.application.audit_logs import AuditRequestContext, record_admin_user_content_access
from productflow_backend.application.auth_sessions import Principal
from productflow_backend.application.use_cases import (
    add_reference_images,
    confirm_copy_set,
    create_product,
    delete_product,
    delete_reference_image,
    get_poster_variant_or_raise,
    get_product_detail,
    get_product_history,
    get_source_asset_or_raise,
    list_products,
    update_copy_set,
)
from productflow_backend.domain.enums import ProductWorkflowState
from productflow_backend.infrastructure.storage import ImageVariantName, LocalStorage
from productflow_backend.presentation.deps import (
    current_owner_user_id,
    get_session,
    request_audit_context,
    require_deletion_enabled,
    require_workspace_principal,
)
from productflow_backend.presentation.image_variants import build_variant_filename
from productflow_backend.presentation.schemas.products import (
    CopySetResponse,
    CopySetUpdateRequest,
    ProductDetailResponse,
    ProductHistoryResponse,
    ProductListResponse,
    serialize_copy_set,
    serialize_poster_variant,
    serialize_product_detail,
    serialize_product_summary,
)
from productflow_backend.presentation.upload_validation import (
    read_validated_image_upload,
    validate_reference_image_count,
)

router = APIRouter(prefix="/api", tags=["products"], dependencies=[Depends(require_workspace_principal)])


@router.post("/products", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_product_endpoint(
    name: str = Form(...),
    image: UploadFile = File(...),
    reference_images: list[UploadFile] | None = File(default=None),
    category: str | None = Form(default=None),
    price: str | None = Form(default=None),
    source_note: str | None = Form(default=None),
    canvas_template_key: str | None = Form(default=None),
    session: Session = Depends(get_session),
    owner_user_id: str | None = Depends(current_owner_user_id),
) -> ProductDetailResponse:
    main_image = await read_validated_image_upload(image, fallback_filename="upload.bin")
    reference_payloads: list[tuple[bytes, str, str]] = []
    validate_reference_image_count(len(reference_images or []))
    for reference_image in reference_images or []:
        validated_reference = await read_validated_image_upload(reference_image, fallback_filename="reference.bin")
        reference_payloads.append(
            (
                validated_reference.content,
                validated_reference.filename,
                validated_reference.mime_type,
            )
        )
    product = create_product(
        session,
        owner_user_id=owner_user_id,
        name=name,
        category=category,
        price=price,
        source_note=source_note,
        image_bytes=main_image.content,
        filename=main_image.filename,
        content_type=main_image.mime_type,
        reference_image_uploads=reference_payloads,
        canvas_template_key=canvas_template_key,
    )
    return serialize_product_detail(product)


@router.get("/products", response_model=ProductListResponse)
def list_products_endpoint(
    status: ProductWorkflowState | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    owner_user_id: str | None = Depends(current_owner_user_id),
) -> ProductListResponse:
    items, total = list_products(session, status=status, page=page, page_size=page_size, owner_user_id=owner_user_id)
    return ProductListResponse(
        items=[serialize_product_summary(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product_detail_endpoint(
    product_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductDetailResponse:
    product = get_product_detail(session, product_id, owner_user_id)
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=product.owner_user_id,
        action="read",
        resource_type="product",
        resource_id=product.id,
        request_context=audit_context,
    )
    return serialize_product_detail(product)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_deletion_enabled)],
)
def delete_product_endpoint(
    product_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> None:
    product = get_product_detail(session, product_id, owner_user_id)
    target_user_id = product.owner_user_id
    delete_product(session, product_id=product_id, owner_user_id=owner_user_id)
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=target_user_id,
        action="delete",
        resource_type="product",
        resource_id=product_id,
        request_context=audit_context,
    )


@router.post("/products/{product_id}/reference-images", response_model=ProductDetailResponse)
async def upload_reference_images_endpoint(
    product_id: str,
    reference_images: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductDetailResponse:
    reference_payloads: list[tuple[bytes, str, str]] = []
    validate_reference_image_count(len(reference_images))
    for reference_image in reference_images:
        validated_reference = await read_validated_image_upload(reference_image, fallback_filename="reference.bin")
        reference_payloads.append(
            (
                validated_reference.content,
                validated_reference.filename,
                validated_reference.mime_type,
            )
        )
    product = add_reference_images(
        session,
        product_id=product_id,
        owner_user_id=owner_user_id,
        reference_image_uploads=reference_payloads,
    )
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=product.owner_user_id,
        action="update",
        resource_type="product",
        resource_id=product.id,
        request_context=audit_context,
    )
    return serialize_product_detail(product)


@router.patch("/copy-sets/{copy_set_id}", response_model=CopySetResponse)
def update_copy_set_endpoint(
    copy_set_id: str,
    payload: CopySetUpdateRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> CopySetResponse:
    copy_set = update_copy_set(
        session,
        copy_set_id=copy_set_id,
        structured_payload=payload.structured_payload,
        owner_user_id=owner_user_id,
    )
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=copy_set.product.owner_user_id,
        action="update",
        resource_type="copy_set",
        resource_id=copy_set.id,
        request_context=audit_context,
    )
    return serialize_copy_set(copy_set)


@router.post("/copy-sets/{copy_set_id}/confirm", response_model=CopySetResponse)
def confirm_copy_set_endpoint(
    copy_set_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> CopySetResponse:
    copy_set = confirm_copy_set(session, copy_set_id=copy_set_id, owner_user_id=owner_user_id)
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=copy_set.product.owner_user_id,
        action="update",
        resource_type="copy_set",
        resource_id=copy_set.id,
        request_context=audit_context,
    )
    return serialize_copy_set(copy_set)


@router.get("/posters/{poster_id}/download")
def download_poster_endpoint(
    poster_id: str,
    variant: ImageVariantName = Query(default="original"),
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> FileResponse:
    poster = get_poster_variant_or_raise(session, poster_id, owner_user_id=owner_user_id)
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=poster.product.owner_user_id,
        action="download",
        resource_type="poster_variant",
        resource_id=poster.id,
        request_context=audit_context,
    )
    storage = LocalStorage()
    try:
        path, media_type = storage.resolve_for_variant(
            poster.storage_path,
            variant,
            fallback_media_type=poster.mime_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="海报文件不存在") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="海报文件不存在")
    filename = build_variant_filename(
        f"{poster.kind.value}{Path(poster.storage_path).suffix or '.png'}",
        variant=variant,
        resolved_suffix=path.suffix,
    )
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/source-assets/{asset_id}/download")
def download_source_asset_endpoint(
    asset_id: str,
    variant: ImageVariantName = Query(default="original"),
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> FileResponse:
    asset = get_source_asset_or_raise(session, asset_id, owner_user_id=owner_user_id)
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=asset.product.owner_user_id,
        action="download",
        resource_type="source_asset",
        resource_id=asset.id,
        request_context=audit_context,
    )
    storage = LocalStorage()
    try:
        path, media_type = storage.resolve_for_variant(
            asset.storage_path,
            variant,
            fallback_media_type=asset.mime_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="源图文件不存在") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="源图文件不存在")
    filename = build_variant_filename(asset.original_filename, variant=variant, resolved_suffix=path.suffix)
    return FileResponse(path, media_type=media_type, filename=filename)


@router.delete("/source-assets/{asset_id}", response_model=ProductDetailResponse)
def delete_source_asset_endpoint(
    asset_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductDetailResponse:
    product = delete_reference_image(session, asset_id=asset_id, owner_user_id=owner_user_id)
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=product.owner_user_id,
        action="delete",
        resource_type="source_asset",
        resource_id=asset_id,
        request_context=audit_context,
    )
    return serialize_product_detail(product)


@router.get("/products/{product_id}/history", response_model=ProductHistoryResponse)
def get_product_history_endpoint(
    product_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str | None = Depends(current_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductHistoryResponse:
    product = get_product_detail(session, product_id, owner_user_id)
    history = get_product_history(session, product_id, owner_user_id)
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=product.owner_user_id,
        action="read",
        resource_type="product_history",
        resource_id=product_id,
        request_context=audit_context,
    )
    return ProductHistoryResponse(
        copy_sets=[serialize_copy_set(item) for item in history["copy_sets"]],
        poster_variants=[serialize_poster_variant(item) for item in history["poster_variants"]],
    )
