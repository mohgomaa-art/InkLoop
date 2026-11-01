"""
Comprehensive integration tests for InkLoop REST API endpoints.
Validates all domain routers, optimistic concurrency, batch orchestration,
verification gating, asset registry, catalogue governance, and budget management.
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from app.api.server import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data

def test_page_editor_accepts_verified_font_upload(client, tmp_path, monkeypatch):
    from app.api.routers import assets as asset_router
    from app.storage.registry import AssetRegistry
    registry = AssetRegistry(tmp_path / "objects", db_path=tmp_path / "registry.sqlite")
    monkeypatch.setattr(asset_router, "_registry_instance", registry)
    font_bytes = b"\x00\x01\x00\x00" + b"test-font-binary"
    response = client.post(
        "/api/v1/assets/fonts",
        data={"project_id": "font_upload_test"},
        files={"file": ("InkLoopTest.ttf", font_bytes, "font/ttf")},
    )
    assert response.status_code == 201
    asset = response.json()
    assert asset["asset_type"] == "font_file"
    assert asset["project_id"] == "font_upload_test"
    assert asset["font_metadata"]["format"] == "TrueType"

    invalid = client.post(
        "/api/v1/assets/fonts",
        data={"project_id": "font_upload_test"},
        files={"file": ("not-a-font.ttf", b"not font", "font/ttf")},
    )
    assert invalid.status_code == 422

def test_spa_frontend_serving(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "InkLoop" in res.text

def test_config_diagnostics_endpoint(client):
    res = client.get("/api/v1/config/diagnostics")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "storage" in data
    assert "budget_defaults" in data
    assert data["budget_defaults"]["default_spend_cap_usd"] == 25.0
    # Secret hygiene check: API key must never be exposed as raw string
    assert data["provider"]["api_key_masked"] in ("PRESENT (MASKED)", "NOT_CONFIGURED", "[SET - REDACTED]", "[NOT SET]")

def test_projects_and_bible_lifecycle(client):
    # 1. List projects
    res = client.get("/api/v1/projects")
    assert res.status_code == 200
    projects = res.json()
    assert len(projects) >= 1
    project_id = projects[0]["project_id"]

    # 2. Get Bible
    res = client.get(f"/api/v1/projects/{project_id}/bible")
    assert res.status_code == 200
    bible = res.json()
    assert bible["project_id"] == project_id
    assert "canon_hash" in bible
    assert bible["canon_hash"] is not None
    current_hash = bible["canon_hash"]

    # 3. Optimistic concurrency conflict test
    conflict_payload = {
        "bible": bible,
        "expected_canon_hash": "stale_hash_that_does_not_match",
    }
    res_conflict = client.put(f"/api/v1/projects/{project_id}/bible", json=conflict_payload)
    assert res_conflict.status_code == 409
    assert res_conflict.json()["detail"]["error_code"] == "ERR_1006_VERSION_MISMATCH"

    # 4. Save with matching hash
    valid_payload = {
        "bible": bible,
        "expected_canon_hash": current_hash,
    }
    res_save = client.put(f"/api/v1/projects/{project_id}/bible", json=valid_payload)
    assert res_save.status_code == 200
    assert res_save.json()["status"] == "saved"

def test_canon_mutation_proposal(client):
    req = {
        "target_type": "character",
        "target_id": "nour",
        "change_description": "Add scene continuity notes",
        "proposed_changes": {"notes": "Updated for scene continuity"},
    }
    res = client.post("/api/v1/projects/default_project/bible/propose-mutation", json=req)
    assert res.status_code == 200
    data = res.json()
    assert "proposal_id" in data
    assert data["target_id"] == "nour"

def test_narrative_timeline_endpoints(client):
    # Append event
    ev = {
        "event_id": "ev_test_01",
        "panel_id": "panel_01",
        "target_entity": "nour",
        "state_delta": {"jacket_worn": True},
        "description": "Nour puts on jacket",
    }
    res = client.post("/api/v1/projects/default_project/timeline/event", json=ev)
    assert res.status_code == 200
    assert res.json()["status"] == "appended"

    # List events
    res_list = client.get("/api/v1/projects/default_project/timeline")
    assert res_list.status_code == 200
    assert any(e["event_id"] == "ev_test_01" for e in res_list.json())

    # Resolve panel state
    res_res = client.get("/api/v1/projects/default_project/timeline/resolve/panel_01")
    assert res_res.status_code == 200
    resolved = res_res.json()
    assert resolved["panel_id"] == "panel_01"
    assert "nour" in resolved["resolved_state"]
    assert resolved["resolved_state"]["nour"]["jacket_worn"] is True

def test_context_compilation_endpoint(client):
    req = {
        "project_id": "default_project",
        "story_id": "story_01",
        "panel_id": "panel_01",
        "scene": {
            "scene_id": "scene_01",
            "scene_index": 0,
            "title": "Opening Shot",
            "shot_type": "medium close-up",
            "action": "Nour adjusting glasses thoughtfully",
            "character_ids": ["nour"]
        }
    }
    res = client.post("/api/v1/generation/compile-context", json=req)
    assert res.status_code == 200
    data = res.json()
    assert "generation_prompt" in data
    assert "context_fingerprint" in data
    assert len(data["context_fingerprint"]) == 64  # SHA-256 length
    assert "character_specs" in data

def test_batch_generation_simulated(client):
    batch_id = f"test_batch_api_{uuid.uuid4().hex[:10]}"
    req = {
        "batch_id": batch_id,
        "project_id": "default_project",
        "story_id": "story_01",
        "scenes": [
            {
                "scene_id": "scene_01",
                "scene_index": 0,
                "title": "Scene 1",
                "shot_type": "medium close-up",
                "action": "Nour stands in workshop",
                "character_ids": ["nour"]
            }
        ],
        "is_simulated": True,
        "max_retries_per_panel": 1,
        "spend_cap_usd": 10.0,
    }
    res = client.post("/api/v1/generation/batches", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["batch_id"] == batch_id
    assert data["total_panels"] == 1
    assert data["successful_panels"] == 1
    assert data["is_simulated"] is True
    assert len(data["panel_results"]) == 1

    # Fetch batch detail
    res_get = client.get(f"/api/v1/generation/batches/{batch_id}")
    assert res_get.status_code == 200
    assert res_get.json()["batch_id"] == batch_id

def test_verification_endpoints(client):
    # Rules
    res_rules = client.get("/api/v1/verification/rules")
    assert res_rules.status_code == 200
    rules = res_rules.json()
    assert "l0_code" in rules
    assert "l1_sam_subject" in rules
    assert "l2_vision_judge" in rules

    # Verification must not silently substitute a sample asset when no image was selected.
    req = {
        "project_id": "default_project",
        "character_id": "nour",
        "mode": "simulated"
    }
    res_verify = client.post("/api/v1/verification/verify", json=req)
    assert res_verify.status_code == 404
    assert res_verify.json()["detail"]["error_code"] == "ERR_1005_UNKNOWN_ENTITY_REFERENCE"

def test_assets_endpoints(client):
    res = client.get("/api/v1/assets?project_id=inkloop")
    assert res.status_code == 200
    assets = res.json()
    assert isinstance(assets, list)

    manifest_res = client.get("/api/v1/assets/manifest/export?project_id=inkloop")
    assert manifest_res.status_code == 200
    manifest = manifest_res.json()
    assert "manifest_id" in manifest
    assert "assets" in manifest

def test_asset_lineage_endpoint(client):
    res = client.get("/api/v1/assets?project_id=inkloop")
    assert res.status_code == 200
    assets = res.json()
    if assets:
        asset_id = assets[0]["asset_id"]
        res_lineage = client.get(f"/api/v1/assets/{asset_id}/lineage")
        assert res_lineage.status_code == 200
        data = res_lineage.json()
        assert data["asset_id"] == asset_id
        assert "parents" in data
        assert "children" in data
        assert isinstance(data["parents"], list)
        assert isinstance(data["children"], list)

def test_catalogue_endpoints(client):
    # Summary
    res_sum = client.get("/api/v1/catalogue/summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["total_groups"] == 60
    assert sum_data["total_canonical_elements"] == 840

    # Groups list
    res_groups = client.get("/api/v1/catalogue/groups")
    assert res_groups.status_code == 200
    groups = res_groups.json()
    assert len(groups) == 60

    # Specific group detail (Group 60)
    res_g60 = client.get("/api/v1/catalogue/groups/tax_60_visual_continuity_validation")
    assert res_g60.status_code == 200
    g60 = res_g60.json()
    assert g60["group_id"] == "tax_60_visual_continuity_validation"
    assert g60["coverage_status"] == "experimentally_tested"

    # Licenses
    res_lic = client.get("/api/v1/catalogue/licenses")
    assert res_lic.status_code == 200
    licenses = res_lic.json()
    assert len(licenses) >= 6

    # Retrieval Endpoint (T6.3)
    retrieval_payload = {
        "scene_id": "api_test_scene_01",
        "shot_type": "medium close-up",
        "action": "standing calmly",
        "camera_angle": "eye level",
        "character_ids": ["nour"],
        "has_reference_images": True,
        "style_line_and_tone": "clean linework with screentone shading",
        "target_model": "muse-image-1.0",
    }
    res_ret = client.post("/api/v1/catalogue/retrieve", json=retrieval_payload)
    assert res_ret.status_code == 200
    ret_data = res_ret.json()
    assert ret_data["scene_id"] == "api_test_scene_01"
    assert "selection_hash" in ret_data
    assert len(ret_data["selected_rules"]) > 0

    # Explain Endpoint (T6.3 Dry-Run)
    res_exp = client.post("/api/v1/catalogue/explain", json=retrieval_payload)
    assert res_exp.status_code == 200
    exp_data = res_exp.json()
    assert exp_data["scene_id"] == "api_test_scene_01"
    assert "explanation_markdown" in exp_data
    assert len(exp_data["provenance_sources"]) > 0

def test_execution_budgets_endpoint(client):
    res = client.get("/api/v1/execution/budgets")
    assert res.status_code == 200
    data = res.json()
    assert "global_cap_usd" in data
    assert data["global_cap_usd"] == 25.0
    assert data["accounting_mode"] == "strict_decimal_minor_units"

def test_evaluation_benchmarks_and_regressions(client):
    # M0 Benchmark
    res_m0 = client.get("/api/v1/evaluation/benchmarks/m0")
    assert res_m0.status_code == 200
    m0 = res_m0.json()
    assert m0["experiment_id"] == "exp_m0_visual_feasibility"
    assert len(m0["sample_records"]) == 12  # 6 Arm A + 6 Arm B

    # 7-Domain Regressions
    res_reg = client.get("/api/v1/evaluation/regressions")
    assert res_reg.status_code == 200
    reg = res_reg.json()
    assert "readiness_inventory" in reg
    assert len(reg["cases"]) == 7

    # Engine Readiness
    res_readiness = client.get("/api/v1/evaluation/readiness")
    assert res_readiness.status_code == 200
    readiness = res_readiness.json()
    assert "e1_image_generation" in readiness["implemented_engines"]
    assert "e2_canvas_generation" in readiness["unimplemented_engines"]

def test_execution_events_limit_and_run_query(client):
    """Regression test: verify querying events with limit parameter succeeds without TypeError."""
    res = client.get("/api/v1/execution/events?limit=50")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_execution_crash_recovery_endpoint(client):
    """Regression test: verify crash recovery endpoint executes without dictionary unpacking ValueError."""
    res = client.post("/api/v1/execution/recover", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "total_recovered_runs" in data
    assert "total_recovered_operations" in data
    assert isinstance(data["recovered_runs"], list)

def test_agent_coordinator_operational_endpoints(client):
    """Verify S9 coordinator endpoints are mounted, operational, and capable of generating typed plans."""
    res_status = client.get("/api/v1/agent/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["status"] == "operational"
    assert status_data["runtime_ready"] is True
    assert status_data["tools_registered"] >= 20

    res_capabilities = client.get("/api/v1/agent/capabilities")
    assert res_capabilities.status_code == 200
    tools = res_capabilities.json()
    assert len(tools) >= 20

    res_plan = client.post("/api/v1/agent/plans", json={"project_id": "default_project", "goal": "Generate comic scene"})
    assert res_plan.status_code == 200
    plan_data = res_plan.json()
    assert "plan_id" in plan_data
    assert plan_data["status"] == "PLANNED"
    assert len(plan_data["steps"]) >= 1


def test_character_anchor_generation_and_set_api(client, monkeypatch):
    """Verify generating and setting a canonical anchor for a character via REST API."""
    monkeypatch.setenv("INKLOOP_OFFLINE_MODE", "1")
    # 1. Generate anchor portrait for nour
    res = client.post("/api/v1/projects/default_project/characters/nour/generate-anchor")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["character_id"] == "nour"
    assert "asset_id" in data
    assert data["url"].startswith("/api/v1/assets/")
    asset_id = data["asset_id"]

    # 2. Verify bible inspection reflects anchor
    res_bible = client.get("/api/v1/projects/default_project/bible")
    assert res_bible.status_code == 200
    b_data = res_bible.json()
    assert "nour" in b_data["characters"]
    nour_refs = b_data["characters"]["nour"].get("reference_assets", [])
    assert len(nour_refs) >= 1
    assert nour_refs[0]["asset_id"] == asset_id

    # 3. Explicitly set anchor with set-anchor endpoint
    res_set = client.post(
        "/api/v1/projects/default_project/characters/nour/anchor",
        json={"asset_id": asset_id},
    )
    assert res_set.status_code == 200
    assert res_set.json()["status"] == "success"


def test_editor_composite_and_export_endpoints(client):
    """Verify POST /api/v1/editor/pages/{id}/composite and /export endpoints."""
    import uuid
    from app.canvas.models import CanvasSpec, PageSpec, LayoutTemplateId
    from app.canvas.engine import CanvasEngine

    uid = uuid.uuid4().hex[:8]
    canvas = CanvasSpec.create_webtoon(width_px=600, height_px=900, dpi=96)
    layout = CanvasEngine.generate_layout(canvas, PageSpec(page_id=f"page_api_{uid}"), LayoutTemplateId.MANGA_GRID)

    res_create = client.post(
        "/api/v1/editor/pages",
        json={
            "project_id": "default_project",
            "layout": layout.model_dump(mode="json"),
            "source_artifact_ids": [],
        },
    )
    assert res_create.status_code in (200, 201), res_create.text
    page_id = res_create.json()["page_id"]

    # 2. Composite the page
    res_comp = client.post(f"/api/v1/editor/pages/{page_id}/composite")
    assert res_comp.status_code == 200, res_comp.text
    comp_data = res_comp.json()
    assert comp_data["success"] is True
    assert "composite_artifact_id" in comp_data
    assert comp_data["image_url"].startswith("/api/v1/assets/")

    # 3. Export as PDF
    res_exp = client.post(
        f"/api/v1/editor/pages/{page_id}/export",
        json={"target_format": "pdf", "reading_direction": "rtl"},
    )
    assert res_exp.status_code == 200, res_exp.text
    exp_data = res_exp.json()
    assert exp_data["success"] is True
    assert exp_data["target_format"] == "pdf"
    assert exp_data["page_count"] == 1
    assert "download_url" in exp_data



