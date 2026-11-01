import pytest
import re
import hashlib
from pathlib import Path
from types import SimpleNamespace

from app.api.routers import creative as creative_router
from app.creative.models import ProfileStatus
from app.creative.quick_styles import (
    QUICK_STYLE_SAMPLE_PROMPT,
    QUICK_STYLE_TEMPLATES,
)


class _MemoryStyleStore:
    def __init__(self):
        self.profiles = {}
        self.save_count = 0

    def list_style_profiles(self, project_id, include_archived=False):
        return [profile for (project, _), profile in self.profiles.items() if project == project_id]

    def get_style_profile(self, project_id, profile_id):
        return self.profiles.get((project_id, profile_id))

    def save_style_profile(self, profile):
        self.save_count += 1
        self.profiles[(profile.project_id, profile.profile_id)] = profile
        return profile


def _verified_preview_registry(template):
    root = Path(__file__).resolve().parents[2]
    preview_name = template.preview_url.removeprefix("/quick-style-previews/")
    preview_path = root / "frontend" / "public" / "quick-style-previews" / preview_name
    data = preview_path.read_bytes()
    metadata = SimpleNamespace(
        asset_id=template.preview_asset_id,
        project_id="quick_style_preview_lab",
        mime_type="image/webp" if preview_path.suffix == ".webp" else "image/png",
        byte_size=len(data),
        content_sha256=hashlib.sha256(data).hexdigest(),
        lifecycle_status="approved",
        validation_state="valid",
        extra_metadata={"is_simulated": False},
    )
    resolved = SimpleNamespace(metadata=metadata, absolute_path=preview_path)

    class Registry:
        def get_asset(self, asset_id):
            return metadata if asset_id == template.preview_asset_id else None

        def resolve_asset(self, asset_id, verify_integrity=True):
            assert verify_integrity is True
            if asset_id != template.preview_asset_id:
                raise ValueError("unknown preview")
            return resolved

    return Registry(), resolved


def test_ten_quick_style_templates_have_the_same_preview_brief_and_complete_variables():
    assert len(QUICK_STYLE_TEMPLATES) == 10
    assert len({template.template_id for template in QUICK_STYLE_TEMPLATES}) == 10
    assert {template.name for template in QUICK_STYLE_TEMPLATES} == {
        "Gouache", "Manga", "Western Comic", "Anime",
        "3D", "Cartoon", "Fantasy Illustration",
        "Stylized Illustration", "Dark Gothic", "Cute Pink Pop",
    }
    assert all(template.sample_prompt == QUICK_STYLE_SAMPLE_PROMPT for template in QUICK_STYLE_TEMPLATES)
    required = {
        "medium", "linework", "stroke_behavior", "edge_quality", "shading",
        "palette", "lighting", "background_detail", "texture", "shape_language",
        "screentones_and_fx",
    }
    assert all(set(template.variables) == required for template in QUICK_STYLE_TEMPLATES)
    assert all(template.style_prompt_core and template.negative_constraints for template in QUICK_STYLE_TEMPLATES)


def test_quick_style_documents_preserve_source_heading_order_and_request_slots():
    root = Path(__file__).resolve().parents[2]
    folder = root / "templates" / "quick_styles"
    master = (folder / "master_schema.md").read_text(encoding="utf-8")
    expected_headings = re.findall(r"^#{1,3} .+$", master, flags=re.MULTILINE)
    for template in QUICK_STYLE_TEMPLATES:
        rendered = (folder / f"{template.template_id}.md").read_text(encoding="utf-8")
        headings = re.findall(r"^#{1,3} .+$", rendered, flags=re.MULTILINE)
        assert headings[1:] == expected_headings[1:]
        for slot in ("{N}", "{SCENE}", "{SUBJECTS}", "{PROPS}", "{FRAME}", "{ASPECT_RATIO}"):
            assert slot in rendered
        assert "no incidental people, creatures, or implied human anatomy" in rendered
        assert "native negative-prompt parameter" in rendered
        assert template.name not in ", ".join(template.negative_constraints)
        scene_slot = re.search(r"^SCENE: \{([^}]+)\}$", rendered, re.MULTILINE)
        subject_slot = re.search(r"^SUBJECTS: \{([^}]+)\}$", rendered, re.MULTILINE)
        assert scene_slot and subject_slot
        assert template.name.casefold() not in scene_slot.group(1).casefold()
        assert template.name.casefold() not in subject_slot.group(1).casefold()


def test_all_quick_style_previews_are_real_registered_outputs_with_shared_provenance():
    import json

    root = Path(__file__).resolve().parents[2]
    preview_root = root / "frontend" / "public" / "quick-style-previews"
    manifest = json.loads((preview_root / "manifest.json").read_text(encoding="utf-8"))
    for template in QUICK_STYLE_TEMPLATES:
        item = manifest["previews"][template.template_id]
        assert item["status"] == "generated"
        assert item["asset_id"].startswith("art_preview_")
        assert item["provider"]
        assert item["is_simulated"] is False
        assert item["prompt"] == QUICK_STYLE_SAMPLE_PROMPT
        assert item["template_version"] == template.version
        assert item["preview_url"].startswith("/quick-style-previews/")
        assert (root / "frontend" / "public" / item["preview_url"].lstrip("/")).is_file()
        assert template.preview_asset_id == item["asset_id"]
        assert template.preview_url == item["preview_url"]


def test_apply_quick_style_creates_pinned_draft_and_reuses_without_overwriting(monkeypatch):
    store = _MemoryStyleStore()
    monkeypatch.setattr(creative_router, "get_creative_profile_store", lambda: store)
    monkeypatch.setattr(creative_router, "get_registry", lambda: SimpleNamespace(resolve_asset=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("not configured"))))

    first = creative_router.apply_quick_style_template("project_a", "manga")

    assert first.status == ProfileStatus.DRAFT
    assert first.metadata["quick_style_template_id"] == "manga"
    assert first.metadata["quick_style_template_version"] == "inkloop.quick-style/1.0.0"
    assert first.style_variables
    assert all(variable.pinned and variable.source == "user_authored" for variable in first.style_variables.values())
    assert first.metadata["quick_style_preview_reference_status"] == "display_only_not_sent"

    first.style_prompt_core = "Creator edited Manga profile"
    store.save_style_profile(first)
    saved_before_reuse = store.save_count
    reused = creative_router.apply_quick_style_template("project_a", "manga")

    assert reused.style_prompt_core == "Creator edited Manga profile"
    assert store.save_count == saved_before_reuse


def test_quick_style_profiles_are_project_scoped_and_unknown_template_is_404(monkeypatch):
    from fastapi import HTTPException

    store = _MemoryStyleStore()
    monkeypatch.setattr(creative_router, "get_creative_profile_store", lambda: store)
    monkeypatch.setattr(creative_router, "get_registry", lambda: SimpleNamespace(resolve_asset=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("not configured"))))

    first = creative_router.apply_quick_style_template("project_a", "anime")
    second = creative_router.apply_quick_style_template("project_b", "anime")

    assert first.project_id == "project_a"
    assert second.project_id == "project_b"
    assert first.profile_id == second.profile_id
    assert len(store.profiles) == 2
    try:
        creative_router.apply_quick_style_template("project_a", "not-a-style")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Unknown style template must fail rather than create a profile")


def test_quick_style_apply_keeps_preview_display_only_and_out_of_style_profile(monkeypatch):
    template = next(item for item in QUICK_STYLE_TEMPLATES if item.template_id == "manga")
    registry, _resolved = _verified_preview_registry(template)
    store = _MemoryStyleStore()
    monkeypatch.setattr(creative_router, "get_creative_profile_store", lambda: store)
    monkeypatch.setattr(creative_router, "get_registry", lambda: registry)

    profile = creative_router.apply_quick_style_template("project_a", "manga")

    assert profile.metadata["quick_style_preview_reference_status"] == "display_only_not_sent"
    assert profile.metadata["preview_asset_id"] == template.preview_asset_id
    assert profile.references == []


def test_reapplying_old_draft_removes_preview_reference_without_overwriting_creator_edits(monkeypatch):
    from app.creative.models import ReferenceBinding, SemanticReferenceRole

    template = next(item for item in QUICK_STYLE_TEMPLATES if item.template_id == "anime")
    registry, _resolved = _verified_preview_registry(template)
    store = _MemoryStyleStore()
    monkeypatch.setattr(creative_router, "get_creative_profile_store", lambda: store)
    monkeypatch.setattr(creative_router, "get_registry", lambda: registry)
    first = creative_router.apply_quick_style_template("project_a", "anime")
    first.style_prompt_core = "Creator's own art direction"
    first.references = [ReferenceBinding(
        asset_id=template.preview_asset_id, role=SemanticReferenceRole.STYLE_REFERENCE,
        notes="legacy quick style preview",
    )]
    store.save_style_profile(first)

    reused = creative_router.apply_quick_style_template("project_a", "anime")

    assert reused.style_prompt_core == "Creator's own art direction"
    assert reused.references == []
    assert reused.metadata["quick_style_preview_reference_status"] == "display_only_not_sent"


def test_applied_quick_style_profile_flows_into_real_generation_context(monkeypatch):
    from app.agent.schemas import ToolCall
    from app.creative.models import ReferenceBinding, SemanticReferenceRole
    from tests.test_agent_generation_context import _CapturingAdapter, _registry_for_test

    store = _MemoryStyleStore()
    monkeypatch.setattr(creative_router, "get_creative_profile_store", lambda: store)
    tool_registry, assets = _registry_for_test(monkeypatch)
    template = next(item for item in QUICK_STYLE_TEMPLATES if item.template_id == "dark_gothic")
    preview_registry, resolved = _verified_preview_registry(template)
    monkeypatch.setattr(creative_router, "get_registry", lambda: preview_registry)
    assets.additional_assets[template.preview_asset_id] = resolved
    profile = creative_router.apply_quick_style_template("inkloop", "dark_gothic")
    # A legacy profile may still have this example image saved as a reference.
    # Generation must exclude it even when the bytes are resolvable.
    profile.references = [ReferenceBinding(
        asset_id=template.preview_asset_id, role=SemanticReferenceRole.STYLE_REFERENCE,
    )]
    store.save_style_profile(profile)
    monkeypatch.setattr("app.creative.storage.get_creative_profile_store", lambda: store)
    result = tool_registry.dispatch(
        ToolCall(call_id="quick-style-context", tool_id="generation.generate_image", arguments={
            "project_id": "inkloop",
            "prompt": QUICK_STYLE_SAMPLE_PROMPT,
            "style_profile_id": profile.profile_id,
            "style_profile_version": profile.version,
            "width": 512,
            "height": 512,
        }),
        {"project_id": "inkloop", "offline_mode": True},
    )

    assert result.status == "success", result.error
    compiled = _CapturingAdapter.requests[-1].prompt
    assert f"CREATOR-SELECTED STYLE PROFILE {profile.profile_id}@v{profile.version}" in compiled
    assert "[PINNED] Medium:" in compiled
    assert "[PINNED] Screentones And Fx:" in compiled
    assert _CapturingAdapter.requests[-1].reference_images == []
    assert result.output["style_reference_asset_ids"] == []
    assert result.output["excluded_style_preview_asset_ids"] == [template.preview_asset_id]
    assert assets.ingestions[-1]["extra_metadata"]["quick_style_template_id"] == "dark_gothic"
    assert assets.ingestions[-1]["extra_metadata"]["style_profile_id"] == profile.profile_id


def test_quick_style_generation_uses_prompt_when_display_only_preview_is_unavailable(monkeypatch):
    from app.agent.schemas import ToolCall
    from tests.test_agent_generation_context import _registry_for_test

    store = _MemoryStyleStore()
    monkeypatch.setattr(creative_router, "get_creative_profile_store", lambda: store)
    monkeypatch.setattr(creative_router, "get_registry", lambda: SimpleNamespace(resolve_asset=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("not configured"))))
    profile = creative_router.apply_quick_style_template("inkloop", "manga")
    monkeypatch.setattr("app.creative.storage.get_creative_profile_store", lambda: store)
    tool_registry, _assets = _registry_for_test(monkeypatch)

    result = tool_registry.dispatch(
        ToolCall(call_id="missing-quick-style-reference", tool_id="generation.generate_image", arguments={
            "project_id": "inkloop", "prompt": "A panel", "style_profile_id": profile.profile_id,
            "style_profile_version": profile.version,
        }),
        {"project_id": "inkloop", "offline_mode": True},
    )

    assert result.status == "success", result.error
    assert result.output["style_reference_asset_ids"] == []


def test_style_analysis_accepts_explicit_verified_shared_preview_bytes_but_rejects_other_projects():
    from app.creative.analyzer import StyleAnalyzer

    template = next(item for item in QUICK_STYLE_TEMPLATES if item.template_id == "manga")
    registry, resolved = _verified_preview_registry(template)
    analyzer = StyleAnalyzer(registry, config=SimpleNamespace(muse_spark_model="deterministic-test"))
    observed = {}

    def vision(images, _instructions=None):
        observed["images"] = images
        return {
            "medium": "ink illustration",
            "linework_summary": "Clean dark outlines.", "linework_rules": ["Keep lines crisp."],
            "stroke_behavior_summary": "Fine controlled marks.", "stroke_behavior_rules": ["Use fine marks."],
            "edge_quality_summary": "Mostly defined edges.", "edge_quality_rules": ["Separate forms clearly."],
            "shading_summary": "Hatched shadows.", "shading_rules": ["Use sparse hatching."],
            "palette_summary": "Monochrome values.", "palette_rules": ["Keep the palette grayscale."],
            "lighting_summary": "Directional light.", "lighting_rules": ["Use directional contrast."],
            "background_detail_summary": "Moderate detail.", "background_detail_rules": ["Keep background legible."],
            "texture_summary": "Paper-like grain.", "texture_rules": ["Use restrained grain."],
            "shape_language_summary": "Expressive forms.", "shape_language_rules": ["Use clear silhouettes."],
            "screentones_and_fx": [], "negative_constraints": [],
            "style_prompt_core": "Monochrome ink with clean lines and controlled hatching.",
        }

    analyzer._call_multimodal_style_vision = vision
    result = analyzer.analyze_references("another-project", [template.preview_asset_id])
    assert observed["images"] == [(resolved.absolute_path.read_bytes(), resolved.metadata.mime_type)]
    assert result.traits["linework"].evidence_asset_ids == [template.preview_asset_id]

    registry.get_asset = lambda _asset_id: SimpleNamespace(
        project_id="different-user-project", mime_type="image/png", byte_size=12,
        extra_metadata={},
    )
    with pytest.raises(ValueError, match="does not belong to this project"):
        analyzer.analyze_references("another-project", ["unlisted_shared_asset"])
