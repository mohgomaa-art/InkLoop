import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.api.server import create_app
from app.storage.registry import AssetType

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def _create_sample_png_bytes(width=100, height=100, color=(200, 50, 50)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_upload_image_asset_success(client):
    img_bytes = _create_sample_png_bytes(120, 120, (10, 20, 30))
    files = {"file": ("test_ref.png", img_bytes, "image/png")}
    data = {"project_id": "test_proj_upload", "asset_type": "image_reference"}
    
    response = client.post("/api/v1/assets/upload", files=files, data=data)
    assert response.status_code == 201
    res_data = response.json()
    assert "asset_id" in res_data
    assert res_data["asset_id"].startswith("art_")
    assert res_data["logical_filename"] == "test_ref.png"
    assert res_data["asset_type"] == "image_reference"
    assert res_data["mime_type"] == "image/png"
    assert res_data["content_sha256"] is not None

    # Verify retrieval
    asset_id = res_data["asset_id"]
    get_res = client.get(f"/api/v1/assets/{asset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["asset_id"] == asset_id

    # Verify file stream
    file_res = client.get(f"/api/v1/assets/{asset_id}/file")
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "image/png"

def test_upload_image_asset_rejects_empty_and_invalid(client):
    # Empty file
    files = {"file": ("empty.png", b"", "image/png")}
    res = client.post("/api/v1/assets/upload", files=files)
    assert res.status_code == 422
    assert res.json()["detail"]["error_code"] == "ERR_IMAGE_EMPTY"

    # Fake magic bytes
    files = {"file": ("fake.png", b"not-a-png-header-data", "image/png")}
    res = client.post("/api/v1/assets/upload", files=files)
    assert res.status_code == 422
    assert res.json()["detail"]["error_code"] == "ERR_ATTACHMENT_INVALID_FORMAT"
