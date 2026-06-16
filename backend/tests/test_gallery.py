from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from helpers import _login, _make_demo_image_bytes

from productflow_backend.application import gallery as gallery_app
from productflow_backend.application.auth_sessions import Principal, build_viewer
from productflow_backend.domain.enums import ImageSessionAssetKind
from productflow_backend.domain.errors import BusinessValidationError
from productflow_backend.infrastructure.db.models import (
    AuditLog,
    GalleryEntryReport,
    ImageGalleryEntry,
    ImageSession,
    ImageSessionAsset,
    ImageSessionRound,
    UserCanvasTemplate,
)
from productflow_backend.infrastructure.db.session import get_session_factory
from productflow_backend.presentation.api import create_app


def _viewer(*, user_id: str | None = None, username: str = "admin"):
    kind = "user" if user_id is not None else "admin"
    return build_viewer(
        Principal(
            session_id=f"session-{user_id or 'admin'}",
            kind=kind,
            new_api_user_id=user_id,
            username=username,
            email=None,
            group=None,
            role="1" if user_id is not None else "admin",
            new_api_token_id=None,
            new_api_token_name=None,
            new_api_token=None,
        )
    )


def _write_storage_image(storage_root: Path, relative_path: str) -> None:
    path = storage_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_make_demo_image_bytes())


def test_generated_image_can_be_saved_to_gallery_idempotently(configured_env: Path, db_session) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client, user_id="user-a", username="alice", role="1")
    product = client.post(
        "/api/products",
        data={"name": "画廊商品"},
        files={"image": ("source.png", _make_demo_image_bytes(), "image/png")},
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    created_session = client.post("/api/image-sessions", json={"product_id": product_id, "title": "画廊会话"})
    assert created_session.status_code == 201
    session_id = created_session.json()["id"]

    asset = ImageSessionAsset(
        session_id=session_id,
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="generated.png",
        mime_type="image/png",
        storage_path="image-sessions/generated.png",
    )
    db_session.add(asset)
    db_session.flush()
    round_item = ImageSessionRound(
        session_id=session_id,
        prompt="一张用于画廊的图",
        assistant_message="ok",
        size="1024x1024",
        model_name="mock-image-chat-v1",
        provider_name="mock",
        prompt_version="responses-image-session-v1",
        provider_output_json={
            "_productflow": {
                "actual_image_size": "1024x1024",
                "notes": [],
            }
        },
        candidate_count=2,
        generated_asset_id=asset.id,
    )
    db_session.add(round_item)
    db_session.commit()
    asset_id = asset.id
    first_round = round_item

    saved = client.post("/api/gallery", json={"image_session_asset_id": asset_id})
    assert saved.status_code == 201
    payload = saved.json()
    assert payload["image_session_asset_id"] == asset_id
    assert payload["image_session_round_id"] == first_round.id
    assert payload["shared_by_user_id"] == "user-a"
    assert payload["shared_by_username"] == "alice"
    assert payload["forked_from_entry_id"] is None
    assert payload["image_session_id"] == session_id
    assert payload["image_session_title"] == "画廊会话"
    assert payload["product_id"] == product_id
    assert payload["product_name"] == "画廊商品"
    assert payload["prompt"] == "一张用于画廊的图"
    assert payload["size"] == "1024x1024"
    assert payload["actual_size"] == "1024x1024"
    assert payload["provider_name"] == "mock"
    assert payload["candidate_index"] == 1
    assert payload["candidate_count"] == 2
    assert payload["image"]["thumbnail_url"].endswith("variant=thumbnail")

    saved_again = client.post("/api/gallery", json={"image_session_asset_id": asset_id})
    assert saved_again.status_code == 200
    assert saved_again.json()["id"] == payload["id"]
    assert db_session.query(ImageGalleryEntry).count() == 1

    listed = client.get("/api/gallery")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == payload["id"]
    assert items[0]["image"]["download_url"].startswith("/api/image-session-assets/")

    detail = client.get(f"/api/gallery/{payload['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == payload["id"]


def test_gallery_rejects_non_generated_session_assets(configured_env: Path) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)
    created_session = client.post("/api/image-sessions", json={"title": "参考图会话"})
    assert created_session.status_code == 201
    session_id = created_session.json()["id"]
    uploaded = client.post(
        f"/api/image-sessions/{session_id}/reference-images",
        files=[("reference_images", ("reference.png", _make_demo_image_bytes(), "image/png"))],
    )
    assert uploaded.status_code == 200
    reference_asset_id = uploaded.json()["assets"][0]["id"]

    saved = client.post("/api/gallery", json={"image_session_asset_id": reference_asset_id})
    assert saved.status_code == 400
    assert saved.json()["detail"] == "只有生成结果可以保存到画廊"


def test_gallery_rejects_generated_asset_without_round(configured_env: Path, db_session) -> None:
    session = ImageSession(title="孤立生成图", owner_user_id="user-a")
    db_session.add(session)
    db_session.flush()
    asset = ImageSessionAsset(
        session_id=session.id,
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="orphan.png",
        mime_type="image/png",
        storage_path="image-sessions/orphan.png",
    )
    db_session.add(asset)
    db_session.commit()

    app = create_app()
    client = TestClient(app)
    _login(client, user_id="user-a", username="alice", role="1")

    saved = client.post("/api/gallery", json={"image_session_asset_id": asset.id})
    assert saved.status_code == 404
    assert saved.json()["detail"] == "生成记录不存在"


def test_gallery_save_handles_integrity_race(
    configured_env: Path,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = ImageSession(title="并发保存会话", owner_user_id="user-a")
    db_session.add(session)
    db_session.flush()
    asset = ImageSessionAsset(
        session_id=session.id,
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="race.png",
        mime_type="image/png",
        storage_path="image-sessions/race.png",
    )
    db_session.add(asset)
    db_session.flush()

    round_item = ImageSessionRound(
        session_id=session.id,
        prompt="并发保存",
        assistant_message="ok",
        size="1024x1024",
        model_name="mock",
        provider_name="mock",
        prompt_version="v1",
        generated_asset_id=asset.id,
    )
    db_session.add(round_item)
    db_session.commit()
    existing = ImageGalleryEntry(
        image_session_asset_id=asset.id,
        image_session_round_id=round_item.id,
    )
    db_session.add(existing)
    db_session.commit()
    existing_id = existing.id

    real_get_gallery_entry = gallery_app._get_gallery_entry_by_asset_id
    calls = {"count": 0}

    def stale_initial_gallery_lookup(session, image_session_asset_id: str):
        calls["count"] += 1
        if calls["count"] == 1:
            return None
        return real_get_gallery_entry(session, image_session_asset_id)

    monkeypatch.setattr(gallery_app, "_get_gallery_entry_by_asset_id", stale_initial_gallery_lookup)

    factory = get_session_factory()
    race_session = factory()
    try:
        result = gallery_app.save_generated_asset_to_gallery(
            race_session,
            viewer=_viewer(user_id="user-a", username="alice"),
            image_session_asset_id=asset.id,
        )

        assert result.created is False
        assert result.entry.id == existing_id
        assert calls["count"] == 2
    finally:
        race_session.close()

    assert db_session.query(ImageGalleryEntry).count() == 1


def test_gallery_share_records_sso_user_author_snapshot(configured_env: Path, db_session) -> None:  # noqa: ARG001
    image_session = ImageSession(title="Alice gallery", owner_user_id="user-a")
    db_session.add(image_session)
    db_session.flush()
    asset = ImageSessionAsset(
        session_id=image_session.id,
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="alice.png",
        mime_type="image/png",
        storage_path="image-sessions/alice.png",
    )
    db_session.add(asset)
    db_session.flush()
    round_item = ImageSessionRound(
        session_id=image_session.id,
        prompt="Alice share",
        assistant_message="ok",
        size="1024x1024",
        model_name="mock",
        provider_name="mock",
        prompt_version="v1",
        generated_asset_id=asset.id,
    )
    db_session.add(round_item)
    db_session.commit()

    result = gallery_app.save_generated_asset_to_gallery(
        db_session,
        viewer=_viewer(user_id="user-a", username="alice"),
        image_session_asset_id=asset.id,
    )

    assert result.created is True
    assert result.entry.shared_by_user_id == "user-a"
    assert result.entry.shared_by_username == "alice"


def test_gallery_share_rejects_cross_user_asset(configured_env: Path, db_session) -> None:  # noqa: ARG001
    image_session = ImageSession(title="Alice private asset", owner_user_id="user-a")
    db_session.add(image_session)
    db_session.flush()
    asset = ImageSessionAsset(
        session_id=image_session.id,
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="alice.png",
        mime_type="image/png",
        storage_path="image-sessions/alice.png",
    )
    db_session.add(asset)
    db_session.flush()
    round_item = ImageSessionRound(
        session_id=image_session.id,
        prompt="Alice private",
        assistant_message="ok",
        size="1024x1024",
        model_name="mock",
        provider_name="mock",
        prompt_version="v1",
        generated_asset_id=asset.id,
    )
    db_session.add(round_item)
    db_session.commit()

    with pytest.raises(BusinessValidationError, match="只能保存自己的生成结果到画廊"):
        gallery_app.save_generated_asset_to_gallery(
            db_session,
            viewer=_viewer(user_id="user-b", username="bob"),
            image_session_asset_id=asset.id,
        )


def test_gallery_report_records_user_reason(configured_env: Path, db_session) -> None:  # noqa: ARG001
    image_session = ImageSession(title="Alice reportable asset", owner_user_id="user-a")
    db_session.add(image_session)
    db_session.flush()
    asset = ImageSessionAsset(
        session_id=image_session.id,
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="alice.png",
        mime_type="image/png",
        storage_path="image-sessions/alice-report.png",
    )
    db_session.add(asset)
    db_session.flush()
    round_item = ImageSessionRound(
        session_id=image_session.id,
        prompt="Alice public",
        assistant_message="ok",
        size="1024x1024",
        model_name="mock",
        provider_name="mock",
        prompt_version="v1",
        generated_asset_id=asset.id,
    )
    db_session.add(round_item)
    db_session.flush()
    entry = ImageGalleryEntry(
        image_session_asset_id=asset.id,
        image_session_round_id=round_item.id,
        shared_by_user_id="user-a",
        shared_by_username="alice",
    )
    db_session.add(entry)
    db_session.commit()

    report = gallery_app.report_gallery_entry(
        db_session,
        viewer=_viewer(user_id="user-b", username="bob"),
        entry_id=entry.id,
        reason_code="copyright",
        reason_text=" copied prompt ",
    )

    assert report.entry_id == entry.id
    assert report.reporter_user_id == "user-b"
    assert report.reason_code == "copyright"
    assert report.reason_text == "copied prompt"
    assert db_session.query(GalleryEntryReport).count() == 1


def test_gallery_import_creates_user_session_and_reshares_with_lineage(configured_env: Path, db_session) -> None:
    app = create_app()
    client = TestClient(app)
    _write_storage_image(configured_env, "image-sessions/source-gallery.png")
    source_session = ImageSession(title="Alice source", owner_user_id="user-a")
    db_session.add(source_session)
    db_session.flush()
    source_asset = ImageSessionAsset(
        session_id=source_session.id,
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="source-gallery.png",
        mime_type="image/png",
        storage_path="image-sessions/source-gallery.png",
    )
    db_session.add(source_asset)
    db_session.flush()
    source_round = ImageSessionRound(
        session_id=source_session.id,
        prompt="source work",
        assistant_message="ok",
        size="1024x1024",
        model_name="mock",
        provider_name="mock",
        prompt_version="v1",
        generated_asset_id=source_asset.id,
    )
    db_session.add(source_round)
    db_session.commit()

    _login(client, user_id="user-a", username="alice", role="1")
    shared = client.post("/api/gallery", json={"image_session_asset_id": source_asset.id})
    assert shared.status_code == 201
    source_entry_id = shared.json()["id"]

    _login(client, user_id="user-b", username="bob", role="1")
    imported = client.post(f"/api/gallery/{source_entry_id}/import")
    assert imported.status_code == 201
    imported_payload = imported.json()
    assert imported_payload["product_id"] is None
    assert imported_payload["assets"][0]["kind"] == "reference_upload"
    assert imported_payload["assets"][0]["imported_from_gallery_entry_id"] == source_entry_id

    db_session.expire_all()
    imported_session = db_session.get(ImageSession, imported_payload["id"])
    assert imported_session is not None
    assert imported_session.owner_user_id == "user-b"

    imported_asset_id = imported_payload["assets"][0]["id"]
    _write_storage_image(configured_env, "image-sessions/remix-gallery.png")
    remix_asset = ImageSessionAsset(
        session_id=imported_payload["id"],
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="remix-gallery.png",
        mime_type="image/png",
        storage_path="image-sessions/remix-gallery.png",
    )
    db_session.add(remix_asset)
    db_session.flush()
    remix_round = ImageSessionRound(
        session_id=imported_payload["id"],
        prompt="remix from gallery",
        assistant_message="ok",
        size="1024x1024",
        model_name="mock",
        provider_name="mock",
        prompt_version="v1",
        selected_reference_asset_ids=[imported_asset_id],
        generated_asset_id=remix_asset.id,
    )
    db_session.add(remix_round)
    db_session.commit()
    reshared = client.post("/api/gallery", json={"image_session_asset_id": remix_asset.id})
    assert reshared.status_code == 201
    assert reshared.json()["shared_by_user_id"] == "user-b"
    assert reshared.json()["forked_from_entry_id"] == source_entry_id


def test_gallery_template_share_unshare_and_import_flow(configured_env: Path, db_session) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client, user_id="user-a", username="alice", role="1")

    created = client.post(
        "/api/products",
        data={"name": "模板分享商品"},
        files={"image": ("template-share.png", _make_demo_image_bytes(), "image/png")},
    )
    assert created.status_code == 201
    product_id = created.json()["id"]
    workflow = client.get(f"/api/products/{product_id}/workflow").json()
    copy_node = next(node for node in workflow["nodes"] if node["node_type"] == "copy_generation")
    image_node = next(node for node in workflow["nodes"] if node["node_type"] == "image_generation")
    output_node = next(node for node in workflow["nodes"] if node["node_type"] == "reference_image")

    saved = client.post(
        f"/api/products/{product_id}/workflow/user-template-groups",
        json={
            "title": "Alice public chain",
            "description": "share me",
            "node_ids": [copy_node["id"], image_node["id"], output_node["id"]],
        },
    )
    assert saved.status_code == 201
    template_id = saved.json()["user_template_id"]

    shared = client.post(f"/api/gallery/templates/{template_id}/share")
    assert shared.status_code == 200
    shared_payload = shared.json()
    assert shared_payload["is_public"] is True
    assert shared_payload["shared_by_username"] == "alice"
    assert shared_payload["preview_nodes"][0]["config_json"] is not None

    listed = client.get("/api/gallery/templates")
    assert listed.status_code == 200
    assert template_id in {item["user_template_id"] for item in listed.json()["items"]}
    detail = client.get(f"/api/gallery/templates/{template_id}")
    assert detail.status_code == 200
    assert detail.json()["user_template_id"] == template_id

    _login(client, user_id="user-b", username="bob", role="1")
    imported = client.post(f"/api/gallery/templates/{template_id}/import")
    assert imported.status_code == 201
    imported_payload = imported.json()
    assert imported_payload["is_public"] is False
    assert imported_payload["forked_from_template_id"] == template_id

    db_session.expire_all()
    imported_row = db_session.get(UserCanvasTemplate, imported_payload["user_template_id"])
    assert imported_row is not None
    assert imported_row.owner_user_id == "user-b"
    assert imported_row.forked_from_template_id == template_id

    _login(client, user_id="user-a", username="alice", role="1")
    unshared = client.delete(f"/api/gallery/templates/{template_id}/share")
    assert unshared.status_code == 200
    assert unshared.json()["is_public"] is False
    listed_after_unshare = client.get("/api/gallery/templates")
    assert listed_after_unshare.status_code == 200
    assert template_id not in {item["user_template_id"] for item in listed_after_unshare.json()["items"]}


def test_admin_can_delete_user_gallery_entry_through_api_with_audit(configured_env: Path, db_session) -> None:
    image_session = ImageSession(title="Alice public asset", owner_user_id="user-a")
    db_session.add(image_session)
    db_session.flush()
    asset = ImageSessionAsset(
        session_id=image_session.id,
        kind=ImageSessionAssetKind.GENERATED_IMAGE,
        original_filename="alice.png",
        mime_type="image/png",
        storage_path="image-sessions/alice-public.png",
    )
    db_session.add(asset)
    db_session.flush()
    round_item = ImageSessionRound(
        session_id=image_session.id,
        prompt="Alice public asset",
        assistant_message="ok",
        size="1024x1024",
        model_name="mock",
        provider_name="mock",
        prompt_version="v1",
        generated_asset_id=asset.id,
    )
    db_session.add(round_item)
    db_session.flush()
    entry = ImageGalleryEntry(
        image_session_asset_id=asset.id,
        image_session_round_id=round_item.id,
        shared_by_user_id="user-a",
        shared_by_username="alice",
    )
    db_session.add(entry)
    db_session.commit()
    entry_id = entry.id

    app = create_app()
    client = TestClient(app)
    _login(client, user_id=None)

    deleted = client.delete(f"/api/gallery/{entry_id}", headers={"user-agent": "gallery-admin"})
    assert deleted.status_code == 204

    db_session.expire_all()
    assert db_session.get(ImageGalleryEntry, entry_id) is None
    logs = db_session.query(AuditLog).all()
    assert len(logs) == 1
    assert logs[0].admin_user_id == "emergency-admin"
    assert logs[0].target_user_id == "user-a"
    assert logs[0].action == "delete_gallery_entry"
    assert logs[0].resource_type == "gallery_entry"
    assert logs[0].resource_id == entry_id
