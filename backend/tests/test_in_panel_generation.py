"""
Defensive unit and integration tests for Creator-First endpoints:
1. POST /api/v1/projects/quick_start
2. POST /api/v1/editor/pages/{page_id}/panels/{panel_id}/generate
"""
import pytest
from fastapi.testclient import TestClient

from app.api.server import create_app
from app.api.routers.editor import get_page_store


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_quick_start_project_success(client):
    """Verify 1-click project quick start boots up Story Bible and Page 1."""
    payload = {
        "title": "Neon Samurai Chronicles",
        "genre": "shonen",
        "premise": "A lone robotic samurai seeks redemption in a submerged neo-Kyoto.",
        "reading_direction": "rtl",
        "language": "ar"
    }
    resp = client.post("/api/v1/projects/quick_start", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["success"] is True
    assert "project_id" in data
    assert "page_1_id" in data
    assert data["genre"] == "shonen"
    assert data["layout_template"] == "dynamic_shonen"
    assert len(data["starter_characters"]) >= 1

    # Verify Page 1 actually exists in PageDocumentStore
    page_resp = client.get(f"/api/v1/editor/pages/{data['page_1_id']}")
    assert page_resp.status_code == 200
    page_data = page_resp.json()
    assert page_data["project_id"] == data["project_id"]
    assert len(page_data["layout"]["panel_slots"]) >= 3


def test_direct_in_panel_generation(client):
    """Verify in-panel image generation attaches image layer to the selected panel."""
    # Step 1: Quick start a project
    qs_resp = client.post("/api/v1/projects/quick_start", json={
        "title": "Desert Sorcerer",
        "genre": "seinen",
        "premise": "An ancient alchemist discovers forgotten glyphs in the dunes.",
        "reading_direction": "ltr",
        "language": "en"
    })
    assert qs_resp.status_code == 201
    qs_data = qs_resp.json()
    page_id = qs_data["page_1_id"]

    # Step 2: Get page to find first panel slot ID
    page_resp = client.get(f"/api/v1/editor/pages/{page_id}")
    assert page_resp.status_code == 200
    panel_slots = page_resp.json()["layout"]["panel_slots"]
    target_panel_id = panel_slots[0]["panel_id"]

    # Step 3: Trigger in-panel generation
    gen_payload = {
        "prompt": "Sara standing atop the sand dune looking into the setting sun",
        "character_ids": ["nour"],
        "camera_angle": "wide cinematic angle",
        "fit_mode": "cover",
        "is_simulated": True
    }
    gen_resp = client.post(f"/api/v1/editor/pages/{page_id}/panels/{target_panel_id}/generate", json=gen_payload)
    assert gen_resp.status_code == 200, gen_resp.text
    gen_data = gen_resp.json()

    assert gen_data["success"] is True
    assert gen_data["page_id"] == page_id
    assert gen_data["panel_id"] == target_panel_id
    assert "asset_id" in gen_data
    assert "image_url" in gen_data
    assert gen_data["generation_provenance"]["visual_verification_status"] == "NOT_RUN"
    assert gen_data["generation_provenance"]["character_ids"] == ["nour"]

    # Step 4: Verify the page document in storage now has the image layer
    updated_page = client.get(f"/api/v1/editor/pages/{page_id}").json()
    img_layers = [l for l in updated_page["layers"] if l["kind"] == "image" and l["panel_id"] == target_panel_id]
    assert len(img_layers) == 1
    assert img_layers[0]["source_asset_id"] == gen_data["asset_id"]


def test_in_panel_generation_invalid_panel(client):
    """Verify generating on a non-existent panel returns 404."""
    # Create project
    qs_resp = client.post("/api/v1/projects/quick_start", json={
        "title": "Test Comic",
        "genre": "comedy",
        "premise": "A funny cat comic.",
        "reading_direction": "ltr",
        "language": "en"
    })
    page_id = qs_resp.json()["page_1_id"]

    gen_resp = client.post(f"/api/v1/editor/pages/{page_id}/panels/non_existent_panel_99/generate", json={
        "prompt": "Cat jumping",
        "is_simulated": True
    })
    assert gen_resp.status_code == 404
