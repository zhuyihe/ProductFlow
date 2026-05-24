from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from productflow_backend.application.auth_sessions import Viewer
from productflow_backend.domain.enums import ImageSessionAssetKind
from productflow_backend.domain.errors import BusinessValidationError, NotFoundError
from productflow_backend.infrastructure.db.models import (
    GalleryEntryReport,
    ImageGalleryEntry,
    ImageSession,
    ImageSessionAsset,
    ImageSessionRound,
)
from productflow_backend.infrastructure.db.models import ImageSessionAsset as _ImageSessionAssetModel
from productflow_backend.infrastructure.storage import LocalStorage


@dataclass(frozen=True, slots=True)
class GallerySaveResult:
    entry: ImageGalleryEntry
    created: bool


@dataclass(frozen=True, slots=True)
class GalleryDeleteResult:
    target_user_id: str | None
    requires_admin_audit: bool


def _gallery_entry_query():
    return (
        select(ImageGalleryEntry)
        .options(
            selectinload(ImageGalleryEntry.asset)
            .selectinload(ImageSessionAsset.session)
            .selectinload(ImageSession.product),
            selectinload(ImageGalleryEntry.round),
        )
        .order_by(desc(ImageGalleryEntry.created_at))
    )


def list_gallery_entries(session: Session) -> list[ImageGalleryEntry]:
    return list(session.scalars(_gallery_entry_query()).all())


def get_gallery_entry(session: Session, entry_id: str) -> ImageGalleryEntry:
    entry = session.scalar(_gallery_entry_query().where(ImageGalleryEntry.id == entry_id))
    if entry is None:
        raise NotFoundError("画廊条目不存在")
    return entry


def _get_gallery_entry_by_asset_id(session: Session, image_session_asset_id: str) -> ImageGalleryEntry | None:
    return session.scalar(
        _gallery_entry_query().where(ImageGalleryEntry.image_session_asset_id == image_session_asset_id)
    )


def _gallery_fork_source_entry_id(session: Session, round_item: ImageSessionRound) -> str | None:
    asset_ids = [round_item.base_asset_id] if round_item.base_asset_id else []
    asset_ids.extend(round_item.selected_reference_asset_ids or [])
    if not asset_ids:
        return None
    for asset_id in asset_ids:
        source_entry_id = session.scalar(
            select(_ImageSessionAssetModel.imported_from_gallery_entry_id).where(_ImageSessionAssetModel.id == asset_id)
        )
        if source_entry_id is not None:
            return source_entry_id
    return None


def _gallery_share_user_id(viewer: Viewer, owner_user_id: str | None) -> str | None:
    if viewer.kind == "user":
        if owner_user_id != viewer.user_id:
            raise BusinessValidationError("只能保存自己的生成结果到画廊")
        return viewer.user_id
    if owner_user_id is not None:
        raise BusinessValidationError("只能保存自己的生成结果到画廊")
    return None


def save_generated_asset_to_gallery(
    session: Session,
    *,
    viewer: Viewer,
    image_session_asset_id: str,
) -> GallerySaveResult:
    asset = session.scalar(
        select(ImageSessionAsset)
        .options(selectinload(ImageSessionAsset.session).selectinload(ImageSession.product))
        .where(ImageSessionAsset.id == image_session_asset_id)
    )
    if asset is None:
        raise NotFoundError("会话图片不存在")
    if asset.kind != ImageSessionAssetKind.GENERATED_IMAGE:
        raise BusinessValidationError("只有生成结果可以保存到画廊")

    sharer_user_id = _gallery_share_user_id(viewer, asset.session.owner_user_id)

    round_item = session.scalar(select(ImageSessionRound).where(ImageSessionRound.generated_asset_id == asset.id))
    if round_item is None:
        raise NotFoundError("生成记录不存在")

    existing = _get_gallery_entry_by_asset_id(session, image_session_asset_id)
    if existing is not None:
        updated = False
        if existing.shared_by_user_id is None and sharer_user_id is not None:
            existing.shared_by_user_id = sharer_user_id
            updated = True
        if existing.shared_by_username is None and viewer.principal.username:
            existing.shared_by_username = viewer.principal.username
            updated = True
        if existing.forked_from_entry_id is None:
            source_entry_id = _gallery_fork_source_entry_id(session, round_item)
            if source_entry_id is not None:
                existing.forked_from_entry_id = source_entry_id
                updated = True
        if updated:
            session.commit()
            session.expire(existing)
        return GallerySaveResult(entry=existing, created=False)

    forked_from_entry_id = _gallery_fork_source_entry_id(session, round_item)
    entry = ImageGalleryEntry(
        image_session_asset_id=asset.id,
        image_session_round_id=round_item.id,
        shared_by_user_id=sharer_user_id,
        shared_by_username=viewer.principal.username,
        forked_from_entry_id=forked_from_entry_id,
    )
    session.add(entry)
    try:
        session.flush()
        entry_id = entry.id
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = _get_gallery_entry_by_asset_id(session, image_session_asset_id)
        if existing is not None:
            return GallerySaveResult(entry=existing, created=False)
        raise
    session.expire_all()
    return GallerySaveResult(
        entry=session.scalar(_gallery_entry_query().where(ImageGalleryEntry.id == entry_id)) or entry,
        created=True,
    )


def import_gallery_entry_to_image_session(
    session: Session,
    *,
    viewer: Viewer,
    entry_id: str,
    storage: LocalStorage | None = None,
) -> ImageSession:
    entry = get_gallery_entry(session, entry_id)
    storage = storage or LocalStorage()
    owner_user_id = viewer.user_id if viewer.kind == "user" else None
    imported_session = ImageSession(
        owner_user_id=owner_user_id,
        product_id=None,
        title=f"{entry.asset.session.title}（导入）",
    )
    session.add(imported_session)
    session.flush()
    source_bytes = storage.resolve(entry.asset.storage_path).read_bytes()
    relative_path = storage.save_image_session_reference(
        imported_session.id,
        entry.asset.original_filename,
        source_bytes,
    )
    session.add(
        ImageSessionAsset(
            session_id=imported_session.id,
            kind=ImageSessionAssetKind.REFERENCE_UPLOAD,
            original_filename=entry.asset.original_filename,
            mime_type=entry.asset.mime_type,
            storage_path=relative_path,
            imported_from_gallery_entry_id=entry.id,
        )
    )
    session.commit()
    session.expire_all()
    from productflow_backend.application.image_sessions import get_image_session_detail

    return get_image_session_detail(session, imported_session.id, owner_user_id)


def delete_gallery_entry(
    session: Session,
    *,
    viewer: Viewer,
    entry_id: str,
) -> GalleryDeleteResult:
    entry = get_gallery_entry(session, entry_id)
    if viewer.kind == "user":
        if entry.shared_by_user_id != viewer.user_id:
            raise BusinessValidationError("只能撤回自己分享的画廊条目")
        requires_admin_audit = False
    else:
        requires_admin_audit = (
            entry.shared_by_user_id is not None
            and entry.shared_by_user_id != (viewer.principal.new_api_user_id or "").strip()
        )

    target_user_id = entry.shared_by_user_id
    session.delete(entry)
    session.commit()
    return GalleryDeleteResult(
        target_user_id=target_user_id,
        requires_admin_audit=requires_admin_audit,
    )


def report_gallery_entry(
    session: Session,
    *,
    viewer: Viewer,
    entry_id: str,
    reason_code: str,
    reason_text: str | None,
) -> GalleryEntryReport:
    if viewer.kind != "user":
        raise BusinessValidationError("只有登录用户可以举报画廊条目")
    entry = get_gallery_entry(session, entry_id)
    normalized_reason_code = reason_code.strip()
    if not normalized_reason_code:
        raise BusinessValidationError("举报原因不能为空")
    report = GalleryEntryReport(
        entry_id=entry.id,
        reporter_user_id=viewer.user_id,
        reason_code=normalized_reason_code,
        reason_text=(reason_text or "").strip() or None,
        status="open",
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report
