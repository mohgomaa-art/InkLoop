"""Project-scope contract tests for the asset-list endpoint.

All files and SQLite state are confined to ``tmp_path``; the workspace and the
running local API are never used by these tests.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from PIL import Image
import io

from app.api import server
from app.api.routers import assets
from app.project.bible import create_canonical_nour_bible, save_bible
from app.storage.registry import AssetType


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (12, 8), color)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _write_project(root, project_id: str) -> None:
    project_dir = root / "runs" / project_id
    project_dir.mkdir(parents=True)
    bible = create_canonical_nour_bible(root, project_id=project_id)
    save_bible(bible, project_dir / "bible.json")


def _client_for_isolated_store(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(assets, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(assets, "_registry_instance", None)
    _write_project(tmp_path, "existing_project")
    _write_project(tmp_path, "other_project")

    registry = assets.get_registry()
    registry.ingest_bytes(
        data=_png_bytes((210, 30, 30)),
        filename="existing.png",
        project_id="existing_project",
        asset_type=AssetType.IMAGE_REFERENCE,
    )
    registry.ingest_bytes(
        data=_png_bytes((20, 30, 210)),
        filename="other.png",
        project_id="other_project",
        asset_type=AssetType.IMAGE_REFERENCE,
    )
    return TestClient(server.create_app())


def test_asset_list_requires_project_scope(tmp_path, monkeypatch):
    client = _client_for_isolated_store(tmp_path, monkeypatch)

    response = client.get("/api/v1/assets")

    assert response.status_code == 422


def test_asset_list_returns_typed_not_found_for_unknown_project(tmp_path, monkeypatch):
    client = _client_for_isolated_store(tmp_path, monkeypatch)

    response = client.get("/api/v1/assets", params={"project_id": "unknown_project"})

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "ERR_PROJECT_NOT_FOUND"


def test_asset_list_filters_a_real_project_registry(tmp_path, monkeypatch):
    client = _client_for_isolated_store(tmp_path, monkeypatch)

    response = client.get("/api/v1/assets", params={"project_id": "existing_project"})

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["project_id"] == "existing_project"
    assert rows[0]["original_filename"] == "existing.png"
