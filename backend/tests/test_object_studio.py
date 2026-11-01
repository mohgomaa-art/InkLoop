from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image, ImageDraw

from app.agent.production import PanelProduction, StoryProductionJob
from app.agent.story_to_canvas import StoryToCanvasWorkflow
from app.api.routers import assets, creative
from app.contracts.artifacts import AssetType
from app.creative import analyzer as analyzer_module
from app.creative.analyzer import ObjectAnalyzer
from app.project.bible import (
    apply_canon_mutation,
    create_canonical_nour_bible,
    load_bible,
    save_bible,
)
from app.project.canon import PropAnalysisRecord, PropDefinition, PropIdentityFeature
from app.schemas import PropSpec, ReferenceAsset, SceneSpec
from app.storage.registry import AssetRegistry
from app.context_builder import build_panel_context_packet
from tests.fixtures.benchmark_fixtures import CANONICAL_M0_STORY_BIBLE


def _png_bytes(color=(190, 150, 80)) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (64, 64), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 55, 55), outline=(20, 20, 20), width=4)
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _registry(tmp_path: Path) -> AssetRegistry:
    root = tmp_path / "asset-store"
    root.mkdir(parents=True, exist_ok=True)
    return AssetRegistry(store_root=root, db_path=root / "registry.db", project_root=tmp_path)


def _vision_result():
    return {
        "observed_summary": "A compact framed hand lamp with a glass chamber.",
        "inferred_purpose": "Portable illumination.",
        "form_and_proportions": "Short rectangular frame around a small glass chamber.",
        "materials": ["dark metal frame", "clear glass"],
        "palette": ["black", "warm amber"],
        "components": ["top handle", "glass chamber", "base frame"],
        "distinctive_marks": ["small rivets at each corner"],
        "stable_invariants": ["compact framed silhouette", "glass chamber inside metal rails"],
        "allowed_states": ["lit", "unlit", "carried"],
        "uncertain_traits": ["fuel source is hidden"],
        "trait_provenance": {
            "description": "model_observation",
            "form_and_proportions": "model_observation",
            "materials": "model_observation",
            "palette": "model_observation",
            "components": "model_observation",
            "distinctive_marks": "model_observation",
            "stable_invariants": "model_observation",
            "allowed_states": "model_inference",
        },
        "visual_features": [
            {"label": "Enclosed chamber", "description": "A glass chamber is enclosed by a compact dark frame.", "stability": "stable", "provenance": "model_observation"},
            {"label": "Illumination", "description": "The chamber can be lit or unlit without changing its construction.", "stability": "state", "provenance": "model_inference"},
        ],
    }


def test_object_analyzer_uses_registered_image_bytes_and_separates_sources(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.PROJECT_ROOT", tmp_path)
    registry = _registry(tmp_path)
    image_bytes = _png_bytes()
    asset = registry.ingest_bytes(
        data=image_bytes,
        filename="lamp_reference.png",
        project_id="object_project",
        asset_type=AssetType.IMAGE_REFERENCE,
    )
    seen = {}

    def analyze(_config, images, _prompt, _kind):
        seen["images"] = images
        return _vision_result()

    monkeypatch.setattr(analyzer_module, "_call_vision_json", analyze)
    profile = ObjectAnalyzer(registry, config=SimpleNamespace(muse_spark_model="test-vision-model")).analyze_object(
        project_id="object_project",
        prop_id="hand_lamp",
        name="Hand lamp",
        asset_ids=[asset.asset_id],
        creator_notes="The brass hinge was repaired by the owner.",
    )

    assert seen["images"] == [(image_bytes, "image/png")]
    assert profile.approval_status == "draft"
    assert profile.analysis.analysis_status == "completed"
    assert profile.analysis.analysis_source == "live_vision_model"
    assert profile.analysis.observed_summary.startswith("A compact framed")
    assert profile.analysis.inferred_purpose == "Portable illumination."
    assert "fuel source is hidden" in profile.analysis.unknown_or_occluded
    assert profile.analysis.creator_authored_facts == ["The brass hinge was repaired by the owner."]
    assert profile.trait_provenance["materials"] == "model_observation"
    assert profile.trait_provenance["allowed_states"] == "model_inference"
    assert profile.identity_features[0].evidence_asset_ids == [asset.asset_id]
    assert profile.reference_assets[0].expected_hash == asset.content_sha256


def test_object_analyzer_rejects_cross_project_reference_before_model_call(tmp_path, monkeypatch):
    registry = _registry(tmp_path)
    asset = registry.ingest_bytes(
        data=_png_bytes(), filename="other_project.png", project_id="another_project", asset_type=AssetType.IMAGE_REFERENCE
    )
    monkeypatch.setattr(analyzer_module, "_call_vision_json", lambda *_args: pytest.fail("provider must not receive cross-project bytes"))
    with pytest.raises(ValueError, match="does not belong to this project"):
        ObjectAnalyzer(registry, config=SimpleNamespace(muse_spark_model="test")).analyze_object(
            project_id="object_project", prop_id="lamp", name="Lamp", asset_ids=[asset.asset_id]
        )


def test_context_packet_uses_selected_object_reference_and_keeps_state_separate():
    bible = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    ref = ReferenceAsset(asset_id="asset_hand_lamp", file_path="runs/object_project/lamp.png", content_hash="a" * 64)
    bible.props = {
        "hand_lamp": PropSpec(
            prop_id="hand_lamp",
            version="3",
            name="Hand lamp",
            description="Compact framed metal-and-glass lamp.",
            form_and_proportions="Short rectangular frame around a glass chamber.",
            stable_invariants=["glass chamber inside metal rails", "top handle attached to frame"],
            materials=["dark metal", "clear glass"],
            components=["handle", "frame", "glass chamber"],
            allowed_states=["lit", "unlit", "carried"],
            reference_assets=[ref],
        ),
        "unused_object": PropSpec(prop_id="unused_object", name="Unused", description="Must not appear"),
    }
    scene = SceneSpec(
        scene_id="lamp_scene", scene_index=0, title="The lamp", shot_type="medium shot",
        action="Gomaa carries the lamp through a quiet street.", character_ids=["nour"],
        prop_ids=["hand_lamp"], prop_states={"hand_lamp": "lit"},
    )
    packet = build_panel_context_packet(
        bible, scene, panel_id="panel_01", project_id="object_project", enable_catalogue_retrieval=False
    )
    assert packet.prop_ids == ["hand_lamp"]
    assert packet.prop_reference_assets[0].asset_id == "asset_hand_lamp"
    assert packet.prop_reference_assets[0].content_hash == "a" * 64
    assert "hand_lamp" in packet.generation_prompt
    assert "glass chamber inside metal rails" in packet.generation_prompt
    assert "Current state in this panel: lit" in packet.generation_prompt
    assert "No object-reference images are attached" not in packet.generation_prompt
    assert "unused_object" not in packet.generation_prompt


def test_story_job_saves_text_only_object_as_draft_then_attaches_real_anchor(tmp_path, monkeypatch):
    project_id = "object_project"
    monkeypatch.setattr("app.config.PROJECT_ROOT", tmp_path)
    registry = _registry(tmp_path)
    monkeypatch.setattr(assets, "get_registry", lambda: registry)
    bible_path = tmp_path / "runs" / project_id / "bible.json"
    bible_path.parent.mkdir(parents=True)
    bible = create_canonical_nour_bible(tmp_path, project_id=project_id)
    save_bible(bible, target_path=bible_path)

    workflow = StoryToCanvasWorkflow.__new__(StoryToCanvasWorkflow)
    workflow.project_id = project_id
    job = StoryProductionJob(
        job_id="storyjob_lamp",
        run_id="storyjob_lamp",
        project_id=project_id,
        source_request_message_id="message_1",
        source_plan_call_id="call_1",
        plan={
            "recurring_objects": [{
                "prop_id": "hand_lamp", "name": "Hand lamp", "description": "Compact framed reading lamp.",
                "form_and_proportions": "Short frame around a glass chamber.", "materials": ["dark metal", "clear glass"],
                "components": ["handle", "glass chamber"], "stable_invariants": ["glass stays inside the metal frame"],
                "allowed_states": ["lit", "unlit", "carried"], "uncertain_traits": [],
            }],
            "plans": [
                {"panel_id": "panel_01", "prop_ids": ["hand_lamp"], "prop_states": {"hand_lamp": "lit"}},
                {"panel_id": "panel_02", "prop_ids": ["hand_lamp"], "prop_states": {"hand_lamp": "carried"}},
            ],
        },
        panels={
            "panel_01": PanelProduction(panel_id="panel_01", page_number=1, prop_ids=["hand_lamp"]),
            "panel_02": PanelProduction(panel_id="panel_02", page_number=1, prop_ids=["hand_lamp"]),
        },
    )
    plans = {plan["panel_id"]: plan for plan in job.plan["plans"]}
    workflow._prepare_story_object_drafts(job, plans)
    saved = load_bible(bible_path).props["hand_lamp"]
    assert saved.approval_status == "draft"
    assert saved.draft_origin == "agent_story_plan"
    assert saved.draft_job_id == job.job_id
    assert saved.analysis.analysis_status == "not_run"
    assert saved.reference_assets == []
    assert job.panels["panel_01"].prop_versions == {"hand_lamp": 1}
    assert job.panels["panel_02"].prop_versions == {"hand_lamp": 1}
    assert job.panels["panel_02"].prop_states == {"hand_lamp": "carried"}
    assert job.prop_versions == {"hand_lamp": 1}

    generated = registry.ingest_bytes(
        data=_png_bytes((50, 50, 50)), filename="panel_01.png", project_id=project_id,
        asset_type=AssetType.IMAGE_GENERATED, extra_metadata={"is_simulated": False},
    )
    workflow._persist_object_anchor("hand_lamp", generated.asset_id, job.job_id)
    anchored = load_bible(bible_path).props["hand_lamp"]
    assert anchored.version == 1  # Identity version stays pinned for this production job.
    assert len(anchored.reference_assets) == 1
    assert anchored.reference_assets[0].asset_id == generated.asset_id
    assert anchored.reference_assets[0].expected_hash == generated.content_sha256
    assert "not been independently verified" in anchored.analysis.unknown_or_occluded[-1]


def test_story_job_reuses_creator_edited_object_draft_without_overwriting_it(tmp_path, monkeypatch):
    project_id = "object_edited_draft"
    monkeypatch.setattr("app.config.PROJECT_ROOT", tmp_path)
    bible_path = tmp_path / "runs" / project_id / "bible.json"
    bible_path.parent.mkdir(parents=True)
    bible = create_canonical_nour_bible(tmp_path, project_id=project_id)
    bible.props["hand_lamp"] = PropDefinition(
        prop_id="hand_lamp", name="Hand lamp", description="Creator-reviewed framed glass lamp.",
        materials=["creator-selected brass"], stable_invariants=["glass remains inside the frame"],
        trait_provenance={"materials": "user_authored"}, approval_status="draft", draft_origin="object_studio",
    )
    save_bible(bible, target_path=bible_path)
    workflow = StoryToCanvasWorkflow.__new__(StoryToCanvasWorkflow)
    workflow.project_id = project_id
    job = StoryProductionJob(
        job_id="storyjob_reuse_edited_prop", run_id="storyjob_reuse_edited_prop", project_id=project_id,
        source_request_message_id="message_1", source_plan_call_id="call_1",
        plan={"recurring_objects": [{
            "prop_id": "hand_lamp", "name": "Hand lamp", "description": "Creator-reviewed framed glass lamp.",
            "stable_invariants": ["glass remains inside the frame"], "materials": ["silver plated metal"],
        }]},
        panels={
            "panel_01": PanelProduction(panel_id="panel_01", page_number=1),
            "panel_02": PanelProduction(panel_id="panel_02", page_number=1),
        },
    )
    plans = {
        "panel_01": {"panel_id": "panel_01", "prop_ids": ["hand_lamp"], "prop_states": {"hand_lamp": "unlit"}},
        "panel_02": {"panel_id": "panel_02", "prop_ids": ["hand_lamp"], "prop_states": {"hand_lamp": "lit"}},
    }
    workflow._prepare_story_object_drafts(job, plans)
    saved = load_bible(bible_path).props["hand_lamp"]
    assert saved.materials == ["creator-selected brass"]
    assert saved.draft_origin == "object_studio"
    assert saved.approval_status == "draft"
    assert job.prop_versions == {"hand_lamp": saved.version}
    assert job.panels["panel_01"].prop_states == {"hand_lamp": "unlit"}
    assert job.panels["panel_02"].prop_states == {"hand_lamp": "lit"}


def test_production_reuses_only_matching_object_version_state_and_reference(tmp_path, monkeypatch):
    registry = _registry(tmp_path)
    project_id = "object_project"
    ref_asset = registry.ingest_bytes(data=_png_bytes(), filename="lamp.png", project_id=project_id, asset_type=AssetType.IMAGE_REFERENCE)
    artwork = registry.ingest_bytes(data=_png_bytes((20, 30, 40)), filename="panel.png", project_id=project_id, asset_type=AssetType.IMAGE_GENERATED)
    monkeypatch.setattr(assets, "get_registry", lambda: registry)
    workflow = StoryToCanvasWorkflow.__new__(StoryToCanvasWorkflow)
    workflow.project_id = project_id
    workflow.selected_character_ids = []
    workflow.canonical_characters = {}
    workflow.selected_style_profile = None
    panel = PanelProduction(
        panel_id="panel_01", page_number=1, prop_ids=["hand_lamp"], prop_versions={"hand_lamp": 4},
        prop_states={"hand_lamp": "lit"}, prop_reference_asset_ids_by_prop={"hand_lamp": [ref_asset.asset_id]},
    )
    output = {
        "panel_id": "panel_01", "asset_id": artwork.asset_id, "is_simulated": False,
        "character_ids": [], "character_versions": {}, "prop_ids": ["hand_lamp"],
        "prop_versions": {"hand_lamp": 4}, "prop_states": {"hand_lamp": "lit"},
        "prop_reference_asset_ids": [ref_asset.asset_id],
        "reference_image_roles": [{"asset_id": ref_asset.asset_id, "role": "object_reference", "prop_id": "hand_lamp"}],
        "style_profile_id": None, "style_profile_version": None,
        "character_reference_asset_ids": [], "reference_asset_ids": [ref_asset.asset_id],
    }
    assert workflow._asset_matches_panel(output, panel)
    assert not workflow._asset_matches_panel({**output, "prop_ids": ["paper_lantern"]}, panel)
    assert not workflow._asset_matches_panel({**output, "prop_versions": {"hand_lamp": 3}}, panel)
    assert not workflow._asset_matches_panel({**output, "prop_states": {"hand_lamp": "unlit"}}, panel)
    assert not workflow._asset_matches_panel({**output, "prop_reference_asset_ids": []}, panel)


def test_later_panel_detects_failed_prior_object_anchor_instead_of_generating_without_reference():
    job = StoryProductionJob(
        job_id="storyjob_anchor_failure", run_id="storyjob_anchor_failure", project_id="object_project",
        source_request_message_id="message_1", source_plan_call_id="call_1",
        plan={},
        panels={
            "panel_01": PanelProduction(
                panel_id="panel_01", page_number=1, asset_id="art_panel_01", prop_ids=["hand_lamp"],
                prop_reference_asset_ids_by_prop={"hand_lamp": []},
                provenance={"object_anchor_errors": ["Bible version conflict"]},
            ),
            "panel_02": PanelProduction(
                panel_id="panel_02", page_number=1, prop_ids=["hand_lamp"],
                prop_reference_asset_ids_by_prop={"hand_lamp": []},
            ),
        },
    )
    prior = StoryToCanvasWorkflow._prior_generated_unanchored_object(job, "panel_02", "hand_lamp")
    assert prior is job.panels["panel_01"]
    assert StoryToCanvasWorkflow._prior_generated_unanchored_object(job, "panel_01", "hand_lamp") is None


def test_object_draft_project_scope_duplicate_guard_and_existing_canon_approval(tmp_path, monkeypatch):
    project_id = "object_project"
    monkeypatch.setattr(creative, "PROJECT_ROOT", tmp_path)
    registry = _registry(tmp_path)
    monkeypatch.setattr(creative, "get_registry", lambda: registry)
    bible_path = tmp_path / "runs" / project_id / "bible.json"
    bible_path.parent.mkdir(parents=True)
    save_bible(create_canonical_nour_bible(tmp_path, project_id=project_id), target_path=bible_path)
    image = registry.ingest_bytes(data=_png_bytes(), filename="ref.png", project_id=project_id, asset_type=AssetType.IMAGE_REFERENCE)
    foreign = registry.ingest_bytes(data=_png_bytes((5, 5, 5)), filename="foreign.png", project_id="foreign_project", asset_type=AssetType.IMAGE_REFERENCE)
    req = creative.ObjectDraftRequest(
        prop=PropDefinition(prop_id="hand_lamp", name="Hand lamp", description="Compact metal frame and glass chamber.", approval_status="draft", draft_origin="object_studio"),
        expected_bible_version=1,
        reference_asset_ids=[image.asset_id],
    )
    result = creative.create_object_draft(project_id, req)
    assert result["prop"]["approval_status"] == "draft"
    assert result["prop"]["reference_assets"][0]["asset_id"] == image.asset_id
    with pytest.raises(HTTPException) as duplicate:
        creative.create_object_draft(project_id, req.model_copy(update={"expected_bible_version": 2}))
    assert duplicate.value.status_code == 409
    with pytest.raises(HTTPException) as cross_project:
        creative.create_object_draft(project_id, req.model_copy(update={
            "prop": req.prop.model_copy(update={"prop_id": "other_lamp"}),
            "expected_bible_version": 2,
            "reference_asset_ids": [foreign.asset_id],
        }))
    assert cross_project.value.status_code == 422

    proposal_result = creative.propose_object_to_canon(
        project_id, "hand_lamp", creative.ProposeCanonRequest(change_description="Reviewed object identity."),
    )
    proposal_id = proposal_result["proposal"]["proposal_id"]
    assert load_bible(bible_path).props["hand_lamp"].approval_status == "draft"
    approved = apply_canon_mutation(bible_path, proposal_id=proposal_id, approved_by="creator")
    assert approved.props["hand_lamp"].approval_status == "approved"


def test_first_object_draft_creates_empty_project_bible_without_seed_canon(tmp_path, monkeypatch):
    project_id = "new_object_only_project"
    monkeypatch.setattr(creative, "PROJECT_ROOT", tmp_path)
    registry = _registry(tmp_path)
    monkeypatch.setattr(creative, "get_registry", lambda: registry)
    bible_path = tmp_path / "runs" / project_id / "bible.json"
    assert not bible_path.exists()

    result = creative.create_object_draft(project_id, creative.ObjectDraftRequest(
        prop=PropDefinition(
            prop_id="story_lantern",
            name="Story lantern",
            description="A lantern the creator will define from story context.",
            creator_notes="Keep this as a project draft until a reference is attached.",
            approval_status="draft",
            draft_origin="object_studio",
        ),
        expected_bible_version=1,
        reference_asset_ids=[],
    ))

    saved = load_bible(bible_path)
    assert result["prop"]["approval_status"] == "draft"
    assert saved.project_id == project_id
    assert saved.characters == {}
    assert saved.props.keys() == {"story_lantern"}
    assert saved.props["story_lantern"].reference_assets == []
    assert saved.style.style_id == "unspecified"


def test_changing_object_reference_set_invalidates_old_image_observations_but_keeps_creator_notes(tmp_path, monkeypatch):
    project_id = "object_reference_refresh"
    monkeypatch.setattr(creative, "PROJECT_ROOT", tmp_path)
    registry = _registry(tmp_path)
    monkeypatch.setattr(creative, "get_registry", lambda: registry)
    bible_path = tmp_path / "runs" / project_id / "bible.json"
    bible_path.parent.mkdir(parents=True)
    save_bible(create_canonical_nour_bible(tmp_path, project_id=project_id), target_path=bible_path)
    first = registry.ingest_bytes(data=_png_bytes((40, 80, 120)), filename="lamp-a.png", project_id=project_id, asset_type=AssetType.IMAGE_REFERENCE)
    replacement = registry.ingest_bytes(data=_png_bytes((120, 80, 40)), filename="lamp-b.png", project_id=project_id, asset_type=AssetType.IMAGE_REFERENCE)
    analyzed = PropDefinition(
        prop_id="hand_lamp", name="Hand lamp", description="Observed compact silver lamp.",
        form_and_proportions="Short frame around a glass chamber.", materials=["silver metal"],
        stable_invariants=["glass chamber in metal frame"], required_attributes=["glass chamber in metal frame"],
        trait_provenance={"description": "model_observation", "form_and_proportions": "model_observation", "materials": "model_observation", "stable_invariants": "model_observation"},
        identity_features=[PropIdentityFeature(
            feature_id="lamp_feature", label="Frame", description="Silver rails around the glass.",
            stability="stable", provenance="model_observation", evidence_asset_ids=[first.asset_id],
        )],
        analysis=PropAnalysisRecord(
            analysis_status="completed", analysis_source="test_provider", observed_summary="Observed compact silver lamp.",
            creator_authored_facts=["The owner calls it Old Faithful."],
        ),
        creator_notes="The owner calls it Old Faithful.", approval_status="draft", draft_origin="object_studio",
    )
    created = creative.create_object_draft(project_id, creative.ObjectDraftRequest(
        prop=analyzed, expected_bible_version=1, reference_asset_ids=[first.asset_id],
    ))
    result = creative.update_object_draft(project_id, "hand_lamp", creative.ObjectDraftRequest(
        prop=PropDefinition.model_validate(created["prop"]),
        expected_bible_version=created["bible_version"],
        reference_asset_ids=[replacement.asset_id],
    ))

    saved = load_bible(bible_path).props["hand_lamp"]
    assert result["prop"]["version"] == 2
    assert saved.analysis.analysis_status == "not_run"
    assert saved.analysis.analysis_source == "references_changed_requires_analysis"
    assert saved.description == ""
    assert saved.form_and_proportions == ""
    assert saved.materials == []
    assert saved.identity_features == []
    assert saved.creator_notes == "The owner calls it Old Faithful."
    assert saved.analysis.creator_authored_facts == ["The owner calls it Old Faithful."]
    assert saved.reference_assets[0].asset_id == replacement.asset_id


def test_object_draft_rejects_reference_whose_registered_hash_no_longer_matches_bytes(tmp_path, monkeypatch):
    project_id = "object_hash_mismatch"
    monkeypatch.setattr(creative, "PROJECT_ROOT", tmp_path)
    registry = _registry(tmp_path)
    monkeypatch.setattr(creative, "get_registry", lambda: registry)
    bible_path = tmp_path / "runs" / project_id / "bible.json"
    bible_path.parent.mkdir(parents=True)
    save_bible(create_canonical_nour_bible(tmp_path, project_id=project_id), target_path=bible_path)
    asset = registry.ingest_bytes(data=_png_bytes(), filename="registered.png", project_id=project_id, asset_type=AssetType.IMAGE_REFERENCE)
    resolved = registry.resolve_asset(asset.asset_id, verify_integrity=True)
    resolved.absolute_path.write_bytes(_png_bytes((10, 20, 30)))
    req = creative.ObjectDraftRequest(
        prop=PropDefinition(prop_id="hand_lamp", name="Hand lamp", description="A metal frame around glass.", approval_status="draft"),
        expected_bible_version=1,
        reference_asset_ids=[asset.asset_id],
    )
    with pytest.raises(HTTPException) as mismatch:
        creative.create_object_draft(project_id, req)
    assert mismatch.value.status_code == 422
    assert mismatch.value.detail["error_code"] == "ERR_INVALID_OBJECT_REFERENCES"
    assert "hash" in mismatch.value.detail["message"].casefold() or "integrity" in mismatch.value.detail["message"].casefold()
    assert "hand_lamp" not in load_bible(bible_path).props

