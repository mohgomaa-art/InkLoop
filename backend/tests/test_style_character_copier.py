"""
Comprehensive Unit & Integration Test Suite for Style Copier & Character Copier.
Verifies:
1. Data Model & Storage Contracts (versioning, project isolation, reference roles)
2. Prompt Builder (strict semantic separation between style, character identity, and scene)
3. Reference Analyzers (StyleAnalyzer, CharacterAnalyzer, and CharacterSheetPlan)
4. Provider Extension & Multi-Reference Handling (no credential leakage, accurate capabilities)
5. StyleIdentityQA (style fidelity, identity preservation, anti-copy-paste variation check)
6. CreativeOrchestrator Bounded Generation & Targeted Single-Pass Refinement
7. Canon Mutation Proposal Integration (invariants proposed without silent mutation)
8. End-to-End Acceptance: Style + Character + Scene generation with persistence
"""
import pytest
from io import BytesIO
from PIL import Image, ImageDraw
from pathlib import Path

from app.contracts.artifacts import AssetType
from app.storage.registry import AssetRegistry, AssetFilter
from app.image_adapter import (
    SimulatedImageGenerationAdapter,
    GenerationRequest,
    ReferenceImagePayload,
    ProviderCapabilities,
)
from app.creative.models import (
    StyleProfile,
    CharacterIdentityProfile,
    ReferenceBinding,
    SemanticReferenceRole,
    CharacterViewRole,
    ProfileStatus,
    GenerationReferenceSet,
    GenerationReferenceItem,
    QASeverity,
    QACategory,
)
from app.creative.storage import CreativeProfileStore
from app.creative.prompt_builder import build_creative_generation_prompt
from app.creative.analyzer import StyleAnalyzer, CharacterAnalyzer
from app.creative.orchestration import CreativeOrchestrator
from app.verification.style_identity_qa import StyleIdentityQAService


def create_test_png(color=(100, 100, 100), draw_shape: str = "rect") -> bytes:
    """Generates a small valid PNG with distinct patterns for testing."""
    buf = BytesIO()
    img = Image.new("RGB", (128, 128), color=color)
    draw = ImageDraw.Draw(img)
    if draw_shape == "rect":
        draw.rectangle([20, 20, 108, 108], fill=(20, 20, 20), outline=(255, 255, 255))
    elif draw_shape == "circle":
        draw.ellipse([20, 20, 108, 108], fill=(200, 200, 200), outline=(0, 0, 0))
    elif draw_shape == "lines":
        for y in range(10, 120, 10):
            draw.line([(10, y), (118, y)], fill=(0, 0, 0), width=2)
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def temp_store(tmp_path):
    db_file = tmp_path / "test_creative.db"
    return CreativeProfileStore(db_path=db_file)


@pytest.fixture
def temp_registry(tmp_path):
    store_root = tmp_path / "artifacts"
    db_path = store_root / "registry.db"
    store_root.mkdir(parents=True, exist_ok=True)
    return AssetRegistry(store_root=store_root, db_path=db_path, project_root=tmp_path)


# =============================================================================
# 1. Data Model & Storage Contracts Tests
# =============================================================================

def test_style_profile_lifecycle_and_versioning(temp_store):
    """Test StyleProfile creation, editing, monotonic version bump upon re-save, and archiving."""
    prof = StyleProfile(
        profile_id="style_manga_noir_v1",
        project_id="proj_alpha",
        name="Manga Noir Screentone",
        version=1,
        style_prompt_core="Deep blacks, crisp 60-line screentones, sharp contour inking",
        negative_constraints=["no color", "no 3D render", "no dialogue balloons"],
        references=[],
    )
    saved = temp_store.save_style_profile(prof)
    assert saved.profile_id == "style_manga_noir_v1"
    assert saved.version == 1
    assert saved.status == ProfileStatus.DRAFT

    # Approve profile
    approved = temp_store.approve_style_profile("proj_alpha", "style_manga_noir_v1")
    assert approved.approved_by_user is True
    assert approved.status == ProfileStatus.APPROVED

    # Modifying an approved profile causes version bump
    approved.name = "Manga Noir Screentone Enhanced"
    approved.approved_by_user = False  # Becomes draft again until reviewed
    updated = temp_store.save_style_profile(approved)
    assert updated.version == 2
    assert updated.name == "Manga Noir Screentone Enhanced"

    # Project isolation test: shouldn't appear in another project
    assert temp_store.get_style_profile("proj_beta", "style_manga_noir_v1") is None

    # Archive
    archived = temp_store.archive_style_profile("proj_alpha", "style_manga_noir_v1")
    assert archived.status == ProfileStatus.ARCHIVED
    active_list = temp_store.list_style_profiles("proj_alpha", include_archived=False)
    assert len(active_list) == 0
    all_list = temp_store.list_style_profiles("proj_alpha", include_archived=True)
    assert len(all_list) == 1


def test_character_profile_lifecycle_and_invariants(temp_store):
    """Test CharacterIdentityProfile storage, invariant separation, and versioning."""
    char_prof = CharacterIdentityProfile(
        profile_id="char_nour_v1",
        project_id="proj_alpha",
        character_id="nour",
        name="Nour",
        version=1,
        identity_invariants=[
            "Short dark unruly hair with distinctive silver lock on left fringe",
            "Sharp angular jawline with slight scar over left eyebrow",
        ],
        allowed_variations=[
            "Dynamic running and leaping poses",
            "Expressive emotion ranging from calm stoicism to intense battle focus",
            "360-degree camera perspective",
        ],
        uncertain_traits=["Exact boot style not visible in headshot"],
        forbidden_drift=["Never render Nour with round chin or blonde hair"],
        prompt_identity_core="Nour, young manga protagonist with sharp eyes and silver hair streak",
        references=[],
    )
    saved = temp_store.save_character_profile(char_prof)
    assert saved.character_id == "nour"
    assert len(saved.identity_invariants) == 2
    assert len(saved.allowed_variations) == 3
    assert len(saved.uncertain_traits) == 1

    # Retrieve by character_id
    by_cid = temp_store.get_character_profile_by_character_id("proj_alpha", "nour")
    assert by_cid is not None
    assert by_cid.profile_id == "char_nour_v1"


# =============================================================================
# 2. Prompt Builder & Semantic Separation Tests
# =============================================================================

def test_prompt_builder_strict_separation():
    """Verify that style reference instructions DO NOT copy characters and character refs DO NOT freeze pose."""
    style_prof = StyleProfile(
        profile_id="style_01",
        project_id="p1",
        name="Screentone",
        style_prompt_core="Manga black and white ink with 60-line halftones",
        negative_constraints=["color bleed", "western comic shading"],
    )
    char_prof = CharacterIdentityProfile(
        profile_id="char_01",
        project_id="p1",
        character_id="nour",
        name="Nour",
        identity_invariants=["Silver hair streak", "Scar over left brow"],
        allowed_variations=["High-speed running", "Determined grimace"],
        forbidden_drift=["Never erase silver streak"],
        prompt_identity_core="Nour with sharp eyes and silver streak",
    )
    ref_set = GenerationReferenceSet(
        project_id="p1",
        references=[
            GenerationReferenceItem(
                asset_id="ast_style_01",
                role=SemanticReferenceRole.STYLE_REFERENCE,
                weight=1.0,
            ),
            GenerationReferenceItem(
                asset_id="ast_char_01",
                role=SemanticReferenceRole.CHARACTER_REFERENCE,
                character_id="nour",
                view_role=CharacterViewRole.FRONT,
                weight=1.0,
            ),
        ]
    )

    prompt = build_creative_generation_prompt(
        scene_action="leaps across rooftops under heavy rain",
        shot_type="Wide action tracking shot, low angle",
        style_profile=style_prof,
        character_profiles=[char_prof],
        reference_set=ref_set,
        lighting_intent="Dramatic rim light and street reflections",
    )

    # Invariants checks:
    # 1. Style Reference must explicitly prohibit copying character/layout
    assert "DO NOT copy any characters, faces, clothing, or layout" in prompt
    # 2. Character Reference must adapt pose to scene action
    assert "Adapt pose, emotion, and angle to the requested scene action" in prompt
    # 3. Requested scene action must be present
    assert "leaps across rooftops under heavy rain" in prompt
    assert "Wide action tracking shot, low angle" in prompt
    # 4. Mandatory invariants and allowed variations are present
    assert "Silver hair streak" in prompt
    assert "Allowed dynamic variations: High-speed running; Determined grimace" in prompt
    assert "Never erase silver streak" in prompt
    # 5. Clean artwork invariant (no dialogue/watermarks)
    assert "Clean artwork only: do not draw lettering, speech bubbles" in prompt


# =============================================================================
# 3. Reference Analyzers Tests
# =============================================================================

def test_style_analyzer_extracts_evidence_and_traits(temp_registry, monkeypatch):
    """Test structured analysis using deterministic mocked provider output and actual registered bytes."""
    img1 = create_test_png(color=(50, 50, 50), draw_shape="lines")
    img2 = create_test_png(color=(200, 200, 200), draw_shape="rect")

    ast1 = temp_registry.ingest_bytes(img1, "style_ref1.png", "p1", AssetType.IMAGE_REFERENCE)
    ast2 = temp_registry.ingest_bytes(img2, "style_ref2.png", "p1", AssetType.IMAGE_REFERENCE)

    import app.creative.analyzer as analyzer_module
    captured = {}
    def mocked_style_vision(config, images, prompt, task):
        captured["prompt"] = prompt
        captured["images"] = images
        return {
        "medium": "ink illustration", "linework_summary": "Visible varied line weight", "linework_rules": ["Keep outer contours heavier"],
        "stroke_behavior_summary": "Broad opaque strokes", "stroke_behavior_rules": ["Keep broad painted marks"],
        "edge_quality_summary": "Soft paint edges", "edge_quality_rules": ["Preserve softened edges"],
        "shading_summary": "Visible clustered dark values", "shading_rules": ["Preserve dark value clusters"],
        "palette_summary": "Mostly neutral values", "palette_rules": ["Use measured neutral values"],
        "lighting_summary": "Soft directional light", "lighting_rules": ["Keep shadows soft"],
        "background_detail_summary": "Backgrounds stay restrained", "background_detail_rules": ["Avoid adding fine background detail"],
        "texture_summary": "Visible textured strokes", "texture_rules": ["Retain stroke texture"],
        "shape_language_summary": "Angular shapes", "shape_language_rules": ["Keep angular contours"],
        "screentones_and_fx": [], "negative_constraints": [], "style_prompt_core": "Observed reference style",
        }
    monkeypatch.setattr(analyzer_module, "_call_vision_json", mocked_style_vision)
    analyzer = StyleAnalyzer(temp_registry)
    analysis = analyzer.analyze_references("p1", [ast1.asset_id, ast2.asset_id], user_instructions="strong darks")

    assert analysis.medium == "ink illustration"
    assert "linework" in analysis.traits
    assert "shading" in analysis.traits
    assert "palette" in analysis.traits
    assert "stroke_behavior" in analysis.traits
    assert "edge_quality" in analysis.traits
    assert "background_detail" in analysis.traits
    assert analysis.traits["linework"].confidence is None
    assert ast1.asset_id in analysis.traits["linework"].evidence_asset_ids
    assert analysis.user_directives == "strong darks"
    assert len(captured["images"]) == 2
    assert "depicted content" in captured["prompt"]
    assert "number/order of panels" in captured["prompt"]
    assert "background-detail density separately" in captured["prompt"]
    assert "Do not label a reference watercolor merely because" in captured["prompt"]
    assert "Distinguish opaque gouache-like coverage" in captured["prompt"]


def test_character_analyzer_and_sheet_plan(temp_registry, monkeypatch):
    """Test character analysis with deterministic mocked provider output."""
    face_img = create_test_png(color=(128, 128, 128), draw_shape="circle")
    body_img = create_test_png(color=(80, 80, 80), draw_shape="rect")

    ast_face = temp_registry.ingest_bytes(face_img, "nour_face.png", "p1", AssetType.IMAGE_REFERENCE)
    ast_body = temp_registry.ingest_bytes(body_img, "nour_body.png", "p1", AssetType.IMAGE_REFERENCE)

    refs = [
        ReferenceBinding(asset_id=ast_face.asset_id, role=SemanticReferenceRole.CHARACTER_REFERENCE, view_role=CharacterViewRole.FRONT),
        ReferenceBinding(asset_id=ast_body.asset_id, role=SemanticReferenceRole.CHARACTER_REFERENCE, view_role=CharacterViewRole.FULL_BODY),
    ]

    import app.creative.analyzer as analyzer_module
    monkeypatch.setattr(analyzer_module, "_call_vision_json", lambda config, images, prompt, task: {
        "character_name": "Nour", "hair": "Dark hair, silver streak visible", "face_and_expression": "Angular jaw and sharp eyes",
        "outfit": "Dark jacket visible", "identity_invariants": ["Silver streak in hair", "Angular jaw"],
        "allowed_variations": ["Pose", "Expression"], "forbidden_drift": ["Do not remove silver streak"],
        "prompt_identity_core": "Reviewable character description",
    })
    analyzer = CharacterAnalyzer(temp_registry)
    profile = analyzer.analyze_character("p1", "nour", "Nour", refs)

    assert profile.character_id == "nour"
    assert len(profile.identity_invariants) >= 2
    assert profile.allowed_variations == ["Pose", "Expression"]
    assert profile.analysis_source == "live_vision_model"

    sheet_plan = analyzer.generate_sheet_plan(profile)
    assert sheet_plan.character_name == "Nour"
    assert len(sheet_plan.views) == 4
    view_types = [v.view_type for v in sheet_plan.views]
    assert "identity_overview" in view_types
    assert "form_turnaround" in view_types
    assert "identity_feature_detail" in view_types
    assert "approved_variation" in view_types
    assert all("do not humanize" in view.prompt.lower() for view in sheet_plan.views[:1])


def test_arbitrary_being_analysis_and_generation_preserve_declared_form(temp_registry, monkeypatch):
    """A nonhuman or abstract being receives no invented human identity fields."""
    circle_bytes = create_test_png(color=(255, 230, 40), draw_shape="circle")
    ref = temp_registry.ingest_bytes(circle_bytes, "smiley-circle.png", "p1", AssetType.IMAGE_REFERENCE)
    binding = ReferenceBinding(
        asset_id=ref.asset_id,
        role=SemanticReferenceRole.CHARACTER_REFERENCE,
        view_role=CharacterViewRole.FULL_FORM,
    )

    import app.creative.analyzer as analyzer_module
    monkeypatch.setattr(analyzer_module, "_call_vision_json", lambda config, images, prompt, task: {
        "character_name": "Sunny",
        "entity_kind": "smiling circle creature",
        "morphology": "perfectly round, flat disk with no separate head or limbs",
        "surface_description": "solid yellow surface",
        "appendages_or_parts": [],
        "sensory_features": ["one simple curved smile"],
        "locomotion": "unknown",
        "visual_features": [{"label": "smile", "description": "single curved black smile", "stability": "stable", "provenance": "model_observation"}],
        "face_check_applicable": False,
        "identity_invariants": ["Keep the silhouette exactly circular", "Keep one simple curved smile"],
        "allowed_variations": ["position and rotation"],
        "forbidden_drift": ["Do not add a body or limbs"],
        "unknown_or_occluded": [],
        "prompt_identity_core": "A flat yellow smiling circle.",
    })
    profile = CharacterAnalyzer(temp_registry).analyze_character("p1", "sunny", "Sunny", [binding])

    assert profile.entity_kind == "smiling circle creature"
    assert profile.morphology.startswith("perfectly round")
    assert profile.face_check_applicable is False
    assert profile.base_outfit is None
    assert not profile.identity_features[0].label.lower().startswith("hair")
    assert profile.identity_features[0].evidence_asset_ids == [ref.asset_id]

    prompt = build_creative_generation_prompt("rolls across the page", character_profiles=[profile])
    assert "perfectly round" in prompt
    assert "one simple curved smile" in prompt
    assert "Do not humanize" in prompt
    assert "Costume:" not in prompt

    from app.creative.analyzer import CharacterAnalyzer as Analyzer
    sheet_plan = Analyzer(temp_registry).generate_sheet_plan(profile)
    assert all("do not humanize" in view.prompt.lower() for view in sheet_plan.views)


def test_face_resolution_check_is_skipped_for_declared_faceless_being():
    """A small object-like subject must not fail a face-specific heuristic it does not use."""
    from app.schemas import BoundingBox, Tolerances
    checker = __import__("app.verification.l1_subject", fromlist=["L1SubjectChecker"]).L1SubjectChecker()
    small_png = create_test_png(color=(255, 255, 255), draw_shape="circle")
    result = checker.check(
        small_png,
        concept="smiling circle creature",
        tolerances=Tolerances(face_check_applicable=False),
        is_simulated=True,
        mock_boxes=[BoundingBox(x=20, y=20, width=88, height=88, label="smiling circle", confidence=1.0)],
    )
    assert result.passed


def test_new_canon_beings_do_not_enable_face_validation_by_default():
    """Fresh canon identities remain valid when they have no declared face landmarks."""
    from app.project.canon import CharacterDefinition
    char = CharacterDefinition(character_id="orb", name="Orb", attributes=[])
    assert char.entity_kind == "unspecified being"
    assert char.tolerances.face_check_applicable is False


def test_creative_director_sheet_plan_is_form_neutral_and_has_no_fake_cost(tmp_path):
    """Production reference plans stay generic for nonhuman profiles and do not invent rates."""
    from app.creative.schemas import CharacterIdentityProfile as DirectorCharacterProfile
    from app.creative.service import CreativeDirectorService
    service = CreativeDirectorService(packages_dir=tmp_path / "packages")
    being = DirectorCharacterProfile(
        character_id="orb",
        name="Orb",
        entity_kind="living glass sphere",
        morphology="a floating sphere with no head or limbs",
        surface_description="translucent blue glass",
        visual_invariants=["exactly spherical", "one internal star"],
    )
    plan = service._build_sheet_plans("p1", {"orb": being})["orb"]
    assert plan.estimated_cost_usd is None
    assert all("do not humanize" in view.prompt.lower() for view in plan.views)
    assert all("no head or limbs" in view.prompt.lower() for view in plan.views)


# =============================================================================
# 4. Provider Multi-Reference Extension & Capabilities
# =============================================================================

def test_provider_multi_reference_and_capabilities():
    """Verify that multi-reference payloads pass correctly and capabilities are honest."""
    sim_adapter = SimulatedImageGenerationAdapter()
    caps = sim_adapter.get_capabilities()

    # Honest capabilities: NO fake hard identity lock
    assert caps.multi_image_reference is True
    assert caps.identity_lock_guarantee is False  # Honest reporting
    assert caps.max_reference_images >= 5

    ref1 = ReferenceImagePayload(image_bytes=b"fake_bytes_1", role="style_reference")
    ref2 = ReferenceImagePayload(image_bytes=b"fake_bytes_2", role="character_reference", character_id="nour")

    req = GenerationRequest(
        prompt="Manga panel of Nour leaping across rooftops",
        reference_images=[ref1, ref2],
        panel_id="panel_test_1",
    )

    resp = sim_adapter.generate(req)
    assert resp.success is True
    assert resp.is_simulated is True
    assert resp.sanitized_metadata["has_reference"] is True
    assert resp.sanitized_metadata["reference_count"] == 2
    assert "style_reference" in resp.sanitized_metadata["reference_roles"]
    assert "character_reference" in resp.sanitized_metadata["reference_roles"]


# =============================================================================
# 5. StyleIdentityQA (Quality Assurance & Variation Check)
# =============================================================================

def test_style_identity_qa_does_not_claim_semantic_pose_verification():
    qa = StyleIdentityQAService()
    ref_png = create_test_png(color=(100, 100, 100), draw_shape="circle")

    # If the output image is identical to the character reference, it must fail the variation check!
    result = qa.evaluate(
        run_id="run_qa_01",
        asset_id="ast_out_01",
        image_bytes=ref_png,
        requested_scene_action="charges into battle with drawn sword",
        reference_images={"char_nour_ref": ref_png},
    )

    assert result.status == "not_verified"
    assert result.variation_score is None
    assert "pose_variation" in result.not_checked_dimensions


def test_style_identity_qa_does_not_claim_leakage_verification():
    qa = StyleIdentityQAService()
    style_ref_png = create_test_png(color=(30, 30, 30), draw_shape="lines")
    style_prof = StyleProfile(profile_id="s1", project_id="p1", name="Noir")

    # Output is identical to style reference -> leakage!
    result = qa.evaluate(
        run_id="run_qa_02",
        asset_id="ast_out_02",
        image_bytes=style_ref_png,
        requested_scene_action="sitting at a café table",
        style_profile=style_prof,
        reference_images={"style_ref_noir": style_ref_png},
    )

    assert result.leakage_detected is None
    assert "reference_leakage" in result.not_checked_dimensions


# =============================================================================
# 6. CreativeOrchestrator End-to-End Generation & Refinement
# =============================================================================

def test_orchestrator_combined_generation_and_refinement(temp_registry, temp_store):
    """
    Test complete end-to-end flow:
    1. Ingest style ref and character ref
    2. Save StyleProfile and CharacterIdentityProfile
    3. Generate panel with both profiles
    4. Verify AssetRegistry lineage and QA findings
    """
    style_img = create_test_png(color=(40, 40, 40), draw_shape="lines")
    char_img = create_test_png(color=(140, 140, 140), draw_shape="circle")

    ast_style = temp_registry.ingest_bytes(style_img, "style_ref.png", "p_main", AssetType.IMAGE_REFERENCE)
    ast_char = temp_registry.ingest_bytes(char_img, "nour_ref.png", "p_main", AssetType.IMAGE_REFERENCE)

    style_prof = StyleProfile(
        profile_id="style_main",
        project_id="p_main",
        name="Manga Ink",
        style_prompt_core="Authentic manga screentone inking",
        negative_constraints=["color bleed", "western comic shading"],
        references=[ReferenceBinding(asset_id=ast_style.asset_id, role=SemanticReferenceRole.STYLE_REFERENCE)],
        approved_by_user=True,
    )
    temp_store.save_style_profile(style_prof)

    char_prof = CharacterIdentityProfile(
        profile_id="char_nour",
        project_id="p_main",
        character_id="nour",
        name="Nour",
        identity_invariants=["Silver hair streak on left side", "Sharp determined eyes"],
        allowed_variations=["Dynamic action poses", "Low angle camera"],
        forbidden_drift=["Never erase silver streak"],
        references=[ReferenceBinding(asset_id=ast_char.asset_id, role=SemanticReferenceRole.CHARACTER_REFERENCE, view_role=CharacterViewRole.FRONT)],
        approved_by_user=True,
    )
    temp_store.save_character_profile(char_prof)

    orchestrator = CreativeOrchestrator(
        registry=temp_registry,
        profile_store=temp_store,
        image_adapter=SimulatedImageGenerationAdapter(),
    )

    result = orchestrator.generate(
        project_id="p_main",
        scene_action="leaps through broken glass window into the rain",
        shot_type="Dramatic dynamic action, low-angle Dutch tilt",
        style_profile_id="style_main",
        character_profile_ids=["char_nour"],
        panel_id="panel_18",
        scene_id="scene_03",
        max_attempts=2,
    )

    assert result.success is True
    assert result.output_asset_id is not None
    assert result.qa_result is not None
    assert result.qa_result.status == "not_verified"
    assert result.is_simulated is True
    assert result.style_profile_id == "style_main"
    assert len(result.character_profiles_used) == 1
    assert result.character_profiles_used[0]["id"] == "nour"

    # Verify generated asset exists in AssetRegistry with proper lineage
    out_asset = temp_registry.get_asset(result.output_asset_id)
    assert out_asset is not None
    assert out_asset.asset_type == AssetType.IMAGE_GENERATED
    assert out_asset.lineage_operation.startswith("creative_")
    # Original source references remain completely unchanged and untruncated
    assert temp_registry.get_asset(ast_style.asset_id) is not None
    assert temp_registry.get_asset(ast_char.asset_id) is not None


def test_multi_character_scene_prompt_disambiguation():
    """Verify that multiple characters in a frame get distinct references and ensemble directives."""
    c1 = CharacterIdentityProfile(
        profile_id="c_nour",
        project_id="p1",
        character_id="nour",
        name="Nour",
        identity_invariants=["Silver hair streak on left side"],
        forbidden_drift=["Never remove silver streak"],
        prompt_identity_core="Nour, agile protagonist",
    )
    c2 = CharacterIdentityProfile(
        profile_id="c_tariq",
        project_id="p1",
        character_id="tariq",
        name="Tariq",
        identity_invariants=["Tall broad-shouldered frame", "Braided copper hair"],
        forbidden_drift=["Never draw short hair"],
        prompt_identity_core="Tariq, stoic mentor",
    )

    prompt = build_creative_generation_prompt(
        scene_action="stand back-to-back facing surrounding shadows",
        character_profiles=[c1, c2],
    )

    assert "Nour, Tariq stand back-to-back" in prompt
    assert "Multi-character requirement: keep each being's declared form and identity features distinct" in prompt
    assert "Silver hair streak on left side" in prompt
    assert "Braided copper hair" in prompt


def test_persistence_across_store_reopen(tmp_path):
    """Verify that profiles, versions, and traits persist across distinct store connections."""
    db_file = tmp_path / "persistent_profiles.db"
    store_a = CreativeProfileStore(db_path=db_file)

    prof = StyleProfile(
        profile_id="style_persistent",
        project_id="proj_x",
        name="Persistent Halftone",
        version=1,
        style_prompt_core="Halftone dots",
    )
    store_a.save_style_profile(prof)
    store_a.approve_style_profile("proj_x", "style_persistent")

    # Reopen with brand new store instance
    store_b = CreativeProfileStore(db_path=db_file)
    loaded = store_b.get_style_profile("proj_x", "style_persistent")

    assert loaded is not None
    assert loaded.name == "Persistent Halftone"
    assert loaded.version == 1
    assert loaded.status == ProfileStatus.APPROVED
    assert loaded.approved_by_user is True


def test_creative_api_endpoints():
    """Test Creative API endpoints using FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from app.api.server import create_app

    client = TestClient(create_app())

    # 1. Capabilities
    caps_resp = client.get("/api/v1/projects/default_project/creative/capabilities")
    assert caps_resp.status_code == 200
    caps_data = caps_resp.json()
    assert caps_data["multi_image_reference"] is True
    assert caps_data["identity_lock_guarantee"] is False  # Honest declaration

    # 2. Save Style Profile
    style_payload = {
        "profile_id": "api_style_01",
        "project_id": "default_project",
        "name": "API Test Screentone",
        "version": 1,
        "style_prompt_core": "Manga screentone lines",
        "negative_constraints": ["color"],
        "references": [],
    }
    style_resp = client.post("/api/v1/projects/default_project/creative/styles", json=style_payload)
    assert style_resp.status_code == 200
    assert style_resp.json()["name"] == "API Test Screentone"

    # 3. List Style Profiles
    list_styles = client.get("/api/v1/projects/default_project/creative/styles")
    assert list_styles.status_code == 200
    assert any(s["profile_id"] == "api_style_01" for s in list_styles.json())

    # 4. Save Character Profile
    char_payload = {
        "profile_id": "api_char_nour",
        "project_id": "default_project",
        "character_id": "nour",
        "name": "Nour",
        "version": 1,
        "identity_invariants": ["Silver streak"],
        "allowed_variations": ["Running"],
        "forbidden_drift": ["Blonde"],
        "references": [],
    }
    char_resp = client.post("/api/v1/projects/default_project/creative/characters/profiles", json=char_payload)
    assert char_resp.status_code == 200
    assert char_resp.json()["character_id"] == "nour"

    # 5. List Character Profiles
    list_chars = client.get("/api/v1/projects/default_project/creative/characters/profiles")
    assert list_chars.status_code == 200
    assert any(c["character_id"] == "nour" for c in list_chars.json())

    # 6. Generate with Profiles
    gen_payload = {
        "scene_action": "running on rooftops",
        "shot_type": "Wide low-angle",
        "style_profile_id": "api_style_01",
        "character_profile_ids": ["api_char_nour"],
        "panel_id": "api_p1",
        "scene_id": "api_s1",
        "max_attempts": 1,
    }
    gen_resp = client.post("/api/v1/projects/default_project/creative/generate", json=gen_payload)
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["success"] is True
    assert gen_data["output_asset_id"] is not None
    assert gen_data["qa_result"]["passed"] is False
    assert gen_data["qa_result"]["status"] == "not_verified"
    assert gen_data["is_simulated"] is True

    # 7. Generate Turnaround Sheet Execution
    sheet_resp = client.post(
        "/api/v1/projects/default_project/creative/characters/profiles/api_char_nour/generate-sheet",
        json={"style_profile_id": "api_style_01", "max_attempts": 1}
    )
    assert sheet_resp.status_code == 200
    sheet_data = sheet_resp.json()
    assert sheet_data["character_id"] == "nour"
    assert sheet_data["total_views"] >= 4
    assert len(sheet_data["views"]) >= 4
    for view in sheet_data["views"]:
        assert view["asset_id"] != ""
        assert view["qa_score"] is None

    # 8. Propose Character Invariants to Canon
    canon_resp = client.post(
        "/api/v1/projects/default_project/creative/characters/profiles/api_char_nour/propose-canon",
        json={"change_description": "Propose tested invariants from reference analysis."}
    )
    assert canon_resp.status_code == 200
    canon_data = canon_resp.json()
    assert canon_data["status"] == "proposal_created"
    assert "proposal" in canon_data


