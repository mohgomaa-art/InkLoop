"""The agent E1 tool must use canonical context and real image references."""
from types import SimpleNamespace

from PIL import Image
import io
import hashlib

from app.agent import registry as registry_module
from app.agent.registry import CapabilityRegistry
from app.agent.schemas import ToolCall
from app.image_adapter import GenerationResponse
from app.context_builder import build_panel_context_packet
from app.schemas import AttributeCheck, CharacterSpec, PropSpec, ReferenceAsset, SceneSpec, StoryBible
from app.planning.panel_planner import PanelPlanningRequest, plan_panels
from app.canvas.descriptors import NarrativeFunction
from app.creative.models import StyleProfile, StyleAnalysisRecord, StyleDimensionTrait, StyleControlVariable, ReferenceBinding, SemanticReferenceRole
from app.creative.schemas import LocationSpec
from tests.fixtures.benchmark_fixtures import CANONICAL_M0_STORY_BIBLE


def _png_bytes():
    image = Image.new("RGB", (24, 32), color=(255, 255, 255))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class _CapturingAdapter:
    requests = []

    def __init__(self, **_kwargs):
        pass

    def generate(self, request):
        self.requests.append(request)
        return GenerationResponse(
            success=True,
            http_status=200,
            image_bytes=_png_bytes(),
            is_simulated=True,
            duration_seconds=0.01,
        )


class _FakeAssetRegistry:
    def __init__(self):
        self.ingestions = []
        self.selected_asset = None
        self.additional_assets = {}

    def ingest_bytes(self, **kwargs):
        self.ingestions.append(kwargs)
        return None

    def get_asset(self, asset_id):
        if self.selected_asset and self.selected_asset.metadata.asset_id == asset_id:
            return self.selected_asset.metadata
        if asset_id in self.additional_assets:
            return self.additional_assets[asset_id].metadata
        return None

    def resolve_asset(self, asset_id, verify_integrity=True):
        assert verify_integrity is True
        if asset_id in self.additional_assets:
            return self.additional_assets[asset_id]
        if self.selected_asset is None or self.selected_asset.metadata.asset_id != asset_id:
            raise ValueError("missing selected asset")
        return self.selected_asset


def _registry_for_test(monkeypatch):
    assets = _FakeAssetRegistry()
    _CapturingAdapter.requests = []
    monkeypatch.setattr(registry_module, "_get_project_bible", lambda _project_id: CANONICAL_M0_STORY_BIBLE)
    monkeypatch.setattr(registry_module, "_get_asset_registry", lambda: assets)
    monkeypatch.setattr("app.image_adapter.SimulatedImageGenerationAdapter", _CapturingAdapter)
    return CapabilityRegistry(), assets


def test_asset_ref_expected_hash_survives_generation_context_normalization():
    from app.context_builder import _normalize_reference_asset
    from app.project.asset_refs import AssetRef

    expected = "a" * 64
    asset = AssetRef(
        asset_id="asset_with_expected_hash",
        path="runs/reference.png",
        asset_type="character_sheet",
        expected_hash=expected,
        mime_type="image/png",
    )

    normalized = _normalize_reference_asset(asset, "fallback")

    assert normalized.asset_id == "asset_with_expected_hash"
    assert normalized.content_hash == expected


def test_generation_tool_compiles_canon_and_supplies_verified_character_reference(monkeypatch):
    registry, assets = _registry_for_test(monkeypatch)
    result = registry.dispatch(
        ToolCall(
            call_id="call_canonical_generation",
            tool_id="generation.generate_image",
            arguments={
                "prompt": "Nour discovers a brass key in her palm",
                "panel_id": "panel_01",
                "scene_id": "scene_01",
                "character_ids": ["nour"],
                "width": 512,
                "height": 768,
            },
        ),
        {"project_id": "inkloop", "offline_mode": True},
    )

    assert result.status == "success", result.error
    request = _CapturingAdapter.requests[0]
    assert request.reference_bytes
    assert request.reference_mime == "image/png"
    assert request.scene_id == "scene_01"
    assert "white streak on the left" in request.prompt
    assert "round glasses" in request.prompt
    assert "do not render words" in request.prompt.lower()
    assert request.parameters["reference_asset_ids"] == ["nour_reference"]
    assert result.output["context_fingerprint"]
    assert result.output["visual_verification_status"] == "NOT_RUN"
    assert assets.ingestions[0]["parent_asset_ids"] == ["nour_reference"]


def test_generation_sends_hash_verified_object_reference_bytes_with_prop_role_and_state(monkeypatch, tmp_path):
    tool_registry, assets = _registry_for_test(monkeypatch)
    image_bytes = _png_bytes()
    image_path = tmp_path / "hand-lamp-anchor.png"
    image_path.write_bytes(image_bytes)
    content_hash = hashlib.sha256(image_bytes).hexdigest()
    asset_id = "lamp_anchor_v1"
    metadata = SimpleNamespace(
        asset_id=asset_id,
        project_id="inkloop",
        mime_type="image/png",
        content_sha256=content_hash,
        validation_state="valid",
        lifecycle_status="approved",
        extra_metadata={"prop_id": "hand_lamp"},
    )
    assets.additional_assets[asset_id] = SimpleNamespace(metadata=metadata, absolute_path=image_path)

    bible = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible.props = {
        "hand_lamp": PropSpec(
            prop_id="hand_lamp", version="3", name="Hand lamp",
            description="Compact dark-metal frame enclosing clear glass.",
            form_and_proportions="Short rectangular frame around a glass chamber.",
            materials=["dark metal", "clear glass"], components=["handle", "frame", "glass chamber"],
            stable_invariants=["glass chamber remains inside the metal frame"],
            allowed_states=["lit", "unlit", "carried"],
            reference_assets=[ReferenceAsset(
                asset_id=asset_id, file_path="lamp-anchor.png", content_hash=content_hash, mime_type="image/png",
            )],
        ),
    }
    monkeypatch.setattr(registry_module, "_get_project_bible", lambda _project_id: bible)

    result = tool_registry.dispatch(
        ToolCall(call_id="call_lamp_reference", tool_id="generation.generate_image", arguments={
            "project_id": "inkloop", "prompt": "Muse carries the lamp through the rain.",
            "panel_id": "panel_01", "prop_ids": ["hand_lamp"],
            "prop_versions": {"hand_lamp": 3}, "prop_states": {"hand_lamp": "carried and lit"},
            "width": 512, "height": 512,
        }),
        {"project_id": "inkloop", "offline_mode": True},
    )

    assert result.status == "success", result.error
    request = _CapturingAdapter.requests[-1]
    assert len(request.reference_images) == 1
    ref = request.reference_images[0]
    assert ref.image_bytes == image_bytes
    assert ref.asset_id == asset_id
    assert ref.role == "object_reference"
    assert ref.prop_id == "hand_lamp"
    assert request.parameters["prop_ids"] == ["hand_lamp"]
    assert request.parameters["prop_versions"] == {"hand_lamp": 3}
    assert request.parameters["prop_states"] == {"hand_lamp": "carried and lit"}
    assert "stable physical identity of object hand_lamp only" in request.prompt
    assert result.output["prop_reference_asset_ids"] == [asset_id]
    assert result.output["object_visual_verification_status"] == "NOT_RUN"


def test_generation_skips_simulated_duplicate_character_refs_and_uses_real_canonical_anchor(monkeypatch, tmp_path):
    registry, assets = _registry_for_test(monkeypatch)
    dummy_path = tmp_path / "simulated-dummy.png"
    dummy_bytes = _png_bytes()
    dummy_path.write_bytes(dummy_bytes)
    anchor_path = tmp_path / "canonical-anchor.png"
    anchor_bytes = Image.new("RGB", (48, 64), color=(220, 220, 220))
    anchor_buffer = io.BytesIO()
    anchor_bytes.save(anchor_buffer, format="PNG")
    canonical_bytes = anchor_buffer.getvalue()
    anchor_path.write_bytes(canonical_bytes)

    def add_ref(asset_id, path, data, extra):
        metadata = SimpleNamespace(
            asset_id=asset_id,
            project_id="test_project",
            mime_type="image/png",
            content_sha256=hashlib.sha256(data).hexdigest(),
            validation_state="valid",
            lifecycle_status="approved",
            extra_metadata=extra,
        )
        assets.additional_assets[asset_id] = SimpleNamespace(metadata=metadata, absolute_path=path)
        return SimpleNamespace(asset_id=asset_id, path=str(path), expected_hash=metadata.content_sha256, mime_type="image/png")

    refs = [
        add_ref("dummy_a", dummy_path, dummy_bytes, {"is_simulated": True, "character_id": "muse"}),
        add_ref("dummy_b", dummy_path, dummy_bytes, {"is_simulated": True, "character_id": "muse"}),
        add_ref("muse_real_anchor", anchor_path, canonical_bytes, {"character_id": "muse", "canonical_anchor": True}),
    ]
    muse = SimpleNamespace(
        character_id="muse", id="muse", name="Muse", entity_kind="small nonhuman creature",
        morphology="round creature", surface_description="cream fuzzy surface", attributes=[],
        visual_invariants=["round cream creature"], restrictions=["do not make human"],
        clothing_attributes=[], reference_assets=refs, canon_version=1,
    )
    style = SimpleNamespace(
        style_id="test_style", version=1, medium="comic illustration", rendering_approach="clean ink",
        line_art_rules=[], tonal_rules=[], palette_or_screentone={}, background_detail_rules="",
        lighting_constraints=[], positive_constraints=[], negative_constraints=[], reference_assets=[],
    )
    bible = SimpleNamespace(
        project_id="test_project", bible_version=1, version=1, canon_hash="stable-test-canon",
        characters={"muse": muse}, character_assets={}, style=style, props={}, locations={},
        story_facts=[], status="validated",
    )
    monkeypatch.setattr(registry_module, "_get_project_bible", lambda _project_id: bible)

    result = registry.dispatch(
        ToolCall(call_id="skip-dummy-anchors", tool_id="generation.generate_image", arguments={
            "project_id": "test_project", "prompt": "Muse walks through a sunny garden.",
            "panel_id": "panel_01", "character_ids": ["muse"], "width": 512, "height": 512,
        }),
        {"project_id": "test_project", "offline_mode": True},
    )

    assert result.status == "success", result.error
    assert result.output["character_reference_asset_ids"] == ["muse_real_anchor"]
    assert [image.asset_id for image in _CapturingAdapter.requests[-1].reference_images] == ["muse_real_anchor"]
    assert assets.ingestions[-1]["parent_asset_ids"] == ["muse_real_anchor"]


def test_muse_generation_context_never_injects_nour_specific_catalogue_recipe():
    muse = CharacterSpec(
        id="muse",
        name="Muse",
        entity_kind="small fuzzy creature",
        attributes=[AttributeCheck(id="round_form", text="cream fuzzy round creature")],
        visual_invariants=["cream fuzzy round creature", "small smile"],
        restrictions=["do not make the creature human"],
    )
    bible = StoryBible(
        bible_id="muse-only-test",
        project_id="muse-only-test",
        characters={"muse": muse},
        character_assets={
            "muse": ReferenceAsset(
                asset_id="muse_reference",
                file_path="muse.png",
                content_hash="test-hash",
                mime_type="image/png",
            )
        },
    )
    packet = build_panel_context_packet(
        story_bible=bible,
        scene=SceneSpec(
            scene_id="scene_01",
            scene_index=0,
            title="Sandwich",
            shot_type="creator-specified panel",
            action="Muse eats a sandwich",
            character_ids=["muse"],
        ),
        panel_id="panel_01",
        project_id="muse-only-test",
    )

    assert "Nour" not in packet.generation_prompt
    assert "visible cast is exactly the creator-selected characters: Muse" in packet.generation_prompt
    assert "Do not add any unselected story character" in packet.generation_prompt
    assert "one standalone artwork image for one comic panel" in packet.generation_prompt


def test_character_specific_restrictions_do_not_cancel_another_selected_characters_traits():
    gomaa = CharacterSpec(
        id="gomaa", name="Gomaa", entity_kind="human",
        attributes=[AttributeCheck(id="hair", text="short curly black hair"), AttributeCheck(id="brows", text="thick dark eyebrows")],
        visual_invariants=["black half-rim glasses"], restrictions=[],
    )
    muse = CharacterSpec(
        id="muse", name="Muse", entity_kind="small fuzzy creature",
        attributes=[AttributeCheck(id="fuzz", text="cream dense fuzz")],
        visual_invariants=["small round body"], restrictions=["no hair, eyebrows, or human facial details"],
    )
    bible = StoryBible(
        bible_id="two-character-prompt-test", project_id="two-character-prompt-test",
        characters={"gomaa": gomaa, "muse": muse},
    )
    packet = build_panel_context_packet(
        story_bible=bible,
        scene=SceneSpec(
            scene_id="scene_two_cast", scene_index=0, title="Together", shot_type="two-shot",
            action="Gomaa and Muse examine a lantern", character_ids=["gomaa", "muse"],
        ),
        panel_id="panel_01", project_id="two-character-prompt-test",
    )

    prompt = packet.generation_prompt
    assert "Gomaa [gomaa]" in prompt and "short curly black hair" in prompt and "thick dark eyebrows" in prompt
    assert "Muse [muse]" in prompt and "no hair, eyebrows, or human facial details" in prompt
    global_negative_section = prompt.split("Avoid these prohibited visual traits:", 1)[-1]
    assert "no hair, eyebrows" not in global_negative_section


def test_agent_generation_resolves_selected_style_and_location_by_id_and_version(monkeypatch, tmp_path):
    tool_registry, assets = _registry_for_test(monkeypatch)
    style_path = tmp_path / "style.png"
    style_bytes = _png_bytes()
    style_path.write_bytes(style_bytes)
    style_metadata = SimpleNamespace(project_id="inkloop", mime_type="image/png", asset_id="style_asset_v3")
    assets.additional_assets["style_asset_v3"] = SimpleNamespace(metadata=style_metadata, absolute_path=style_path)

    analysis_summary = "Two-panel meme readability with recognizable clinical characters and thick panel borders."
    profile = StyleProfile(
        profile_id="style_selected", project_id="inkloop", name="Selected Ink", version=3,
        style_prompt_core=analysis_summary,
        analysis=StyleAnalysisRecord(
            analysis_status="completed",
            analysis_source="test_provider_boundary",
            analysis_summary=analysis_summary,
            traits={
                "linework": StyleDimensionTrait(
                    dimension="linework",
                    summary="Panel borders with clean medium-weight outlines; soft tapered contour lines.",
                ),
                "shading": StyleDimensionTrait(
                    dimension="shading",
                    summary="Soft blended digital painting; warm highlights on skin and props.",
                ),
            },
            measured_palette=["#B8D8DE", "#E8C99F"],
        ),
        references=[ReferenceBinding(asset_id="style_asset_v3", role=SemanticReferenceRole.STYLE_REFERENCE)],
        style_variables={
            "medium": StyleControlVariable(value="opaque gouache, no watercolor wash", pinned=True),
            "stroke_behavior": StyleControlVariable(value="broad opaque gouache-like brush marks", pinned=True),
            "background_detail": StyleControlVariable(value="keep backgrounds restrained", pinned=False),
        },
    )
    class ProfileStore:
        def get_style_profile(self, project_id, profile_id):
            return profile if (project_id, profile_id) == ("inkloop", "style_selected") else None
    monkeypatch.setattr("app.creative.storage.get_creative_profile_store", lambda: ProfileStore())

    location = LocationSpec(
        location_id="rooftop", name="Rainy Rooftop", atmosphere="tense and wet",
        spatial_layout="narrow roof with water tank", visual_anchors=["red antenna"],
        lighting_conditions="blue city glow", narrative_use="escape route",
        continuity_rules=["antenna remains on east side"], version=2,
    )
    package = SimpleNamespace(world_bible=SimpleNamespace(locations={"rooftop": location}))
    class Director:
        def get_package(self, project_id):
            assert project_id == "inkloop"
            return package
    monkeypatch.setattr("app.creative.service.CreativeDirectorService.get_instance", lambda: Director())

    result = tool_registry.dispatch(
        ToolCall(call_id="call_selected_context", tool_id="generation.generate_image", arguments={
            "prompt": "Nour runs toward the exit.", "character_ids": ["nour"],
            "style_profile_id": "style_selected", "style_profile_version": 3,
            "location_id": "rooftop", "location_version": 2,
        }),
        {"project_id": "inkloop", "offline_mode": True},
    )

    assert result.status == "success", result.error
    request = _CapturingAdapter.requests[-1]
    assert request.prompt.startswith("Opaque Gouache, No Watercolor Wash panel illustration")
    assert "[PINNED] Medium: opaque gouache, no watercolor wash" in request.prompt
    assert "CREATOR-SELECTED STYLE PROFILE style_selected@v3" in request.prompt
    assert "Linework: outlines" in request.prompt
    assert "Stroke Behavior: broad opaque gouache-like brush marks" in request.prompt
    assert "Background Detail: keep backgrounds restrained" in request.prompt
    assert "[PINNED] Stroke Behavior" in request.prompt
    assert "two-panel" not in request.prompt.lower()
    assert "Panel borders" not in request.prompt
    assert "black and white ink with screentone shading" not in request.prompt.lower()
    assert "clean linework, high contrast" not in request.prompt.lower()
    assert "Style directives:" not in request.prompt
    assert "Catalogue guidance:" not in request.prompt
    assert "Do not copy any style reference's subject" in request.prompt
    assert "Rainy Rooftop" in request.prompt
    assert "red antenna" in request.prompt
    assert [ref.role for ref in request.reference_images] == ["character_reference", "style_reference"]
    assert [ref.asset_id for ref in request.reference_images] == ["nour_reference", "style_asset_v3"]
    assert request.reference_images[0].character_id == "nour"
    assert result.output["style_reference_asset_ids"] == ["style_asset_v3"]
    assert result.output["character_reference_asset_ids"] == ["nour_reference"]
    assert result.output["style_reference_image_conditioning"] == "sent_as_ordered_best_effort_reference_images"


def test_generation_tool_uses_creator_selected_asset_as_reference_and_lineage(monkeypatch, tmp_path):
    registry, assets = _registry_for_test(monkeypatch)
    selected_path = tmp_path / "creator-selected.png"
    selected_path.write_bytes(_png_bytes())
    selected_metadata = SimpleNamespace(
        asset_id="art_creator_selected",
        project_id="inkloop",
        mime_type="image/png",
    )
    assets.selected_asset = SimpleNamespace(metadata=selected_metadata, absolute_path=selected_path)

    result = registry.dispatch(
        ToolCall(
            call_id="call_selected_reference",
            tool_id="generation.generate_image",
            arguments={
                "prompt": "Nour with a calm expression, same framing",
                "panel_id": "panel_variant_02",
                "character_ids": ["nour"],
                "reference_asset_id": "art_creator_selected",
                "width": 512,
                "height": 768,
            },
        ),
        {"project_id": "inkloop", "offline_mode": True},
    )

    assert result.status == "success", result.error
    request = _CapturingAdapter.requests[0]
    assert request.reference_bytes == selected_path.read_bytes()
    assert request.parameters["reference_asset_ids"] == ["nour_reference", "art_creator_selected"]
    assert [ref.role for ref in request.reference_images] == ["character_reference", "composition_reference"]
    assert assets.ingestions[0]["parent_asset_ids"] == ["nour_reference", "art_creator_selected"]


def test_generation_tool_rejects_plan_panel_id_mismatch_before_adapter(monkeypatch):
    registry, _assets = _registry_for_test(monkeypatch)
    planning = plan_panels(PanelPlanningRequest(
        scene_id="scene_01",
        beats=[{
            "beat_id": "beat_01",
            "narrative_function": NarrativeFunction.REVEAL,
            "story_event": "Nour discovers a brass key.",
            "reader_takeaway": "The key is important.",
            "character_ids": ["nour"],
            "visual_focus": "a brass key in Nour's palm",
            "emotional_intent": "surprise",
            "text": {"content_kind": "none", "carrier": "none"},
        }],
    )).plans[0]

    result = registry.dispatch(
        ToolCall(
            call_id="call_bad_plan_id",
            tool_id="generation.generate_image",
            arguments={
                "prompt": "Nour discovers a brass key.",
                "panel_id": "panel_wrong",
                "scene_id": "scene_01",
                "character_ids": ["nour"],
                "panel_plan": planning.model_dump(mode="json"),
            },
        ),
        {"project_id": "inkloop", "offline_mode": True},
    )

    assert result.status == "failed"
    assert result.error_code == "ERR_PANEL_PLAN_ID_MISMATCH"
    assert _CapturingAdapter.requests == []


def test_generation_tool_blocks_named_character_without_reference_anchor(monkeypatch):
    registry, _assets = _registry_for_test(monkeypatch)
    # Story bible with a new character without reference assets
    bible_without_ref = SimpleNamespace(
        project_id="test_project",
        bible_version="1.0.0",
        canon_hash="hash_123",
        story_facts=[],
        characters={"hero": SimpleNamespace(
            character_id="hero",
            name="Hero",
            role="Protagonist",
            attributes=[{"id": "hair", "text": "spiky brown hair", "required": True}],
            visual_invariants=["spiky brown hair", "red hooded cloak"],
            restrictions=["never remove cloak"],
            reference_assets=[],
        )},
        character_assets={},
        style=SimpleNamespace(reference_assets=[], positive_constraints=[], negative_constraints=[]),
    )
    monkeypatch.setattr(registry_module, "_get_project_bible", lambda _project_id: bible_without_ref)

    result = registry.dispatch(
        ToolCall(
            call_id="call_unanchored_story_scene",
            tool_id="generation.generate_image",
            arguments={
                "prompt": "hero sleeping in bed",
                "panel_id": "panel_01",
                "character_ids": ["hero"],
            },
        ),
        {"project_id": "test_project", "offline_mode": True},
    )

    assert result.status == "failed"
    assert result.error_code == "ERR_CANONICAL_REFERENCE_UNAVAILABLE"


def test_generation_tool_allows_initial_anchor_portrait_without_existing_reference(monkeypatch):
    registry, _assets = _registry_for_test(monkeypatch)
    bible_without_ref = SimpleNamespace(
        project_id="test_project",
        bible_version="1.0.0",
        canon_hash="hash_123",
        story_facts=[],
        characters={"hero": SimpleNamespace(
            character_id="hero",
            name="Hero",
            role="Protagonist",
            attributes=[{"id": "hair", "text": "spiky brown hair", "required": True}],
            visual_invariants=["spiky brown hair", "red hooded cloak"],
            restrictions=["never remove cloak"],
            reference_assets=[],
        )},
        character_assets={},
        style=SimpleNamespace(reference_assets=[], positive_constraints=[], negative_constraints=[]),
    )
    monkeypatch.setattr(registry_module, "_get_project_bible", lambda _project_id: bible_without_ref)

    result = registry.dispatch(
        ToolCall(
            call_id="call_initial_anchor_portrait",
            tool_id="generation.generate_image",
            arguments={
                "prompt": "Create an initial hero portrait to propose as the anchor",
                "panel_id": "panel_anchor_01",
                "character_ids": ["hero"],
                "is_anchor_generation": True,
            },
        ),
        {"project_id": "test_project", "offline_mode": True},
    )

    assert result.status == "success", result.error
    assert result.output["is_initial_anchor"] is True
    request = _CapturingAdapter.requests[0]
    assert "spiky brown hair" in request.prompt
    assert "red hooded cloak" in request.prompt


def test_canon_set_reference_anchor_tool(monkeypatch):
    registry, assets = _registry_for_test(monkeypatch)
    bible_without_ref = SimpleNamespace(
        project_id="test_project",
        bible_version="1.0.0",
        canon_hash="hash_123",
        story_facts=[],
        characters={"cassian": SimpleNamespace(
            character_id="cassian",
            name="Cassian Vane",
            role="Antagonist",
            attributes=[{"id": "coat", "text": "velvet frock coat", "required": True}],
            visual_invariants=["midnight velvet frock coat"],
            restrictions=["never unkempt"],
            reference_assets=[],
        )},
        character_assets={},
        style=SimpleNamespace(reference_assets=[], positive_constraints=[], negative_constraints=[]),
    )
    monkeypatch.setattr(registry_module, "_get_project_bible", lambda _project_id: bible_without_ref)

    # Ingest a fake asset into assets registry
    asset_meta = SimpleNamespace(
        asset_id="asset_cassian_portrait",
        mime_type="image/png",
        content_sha256="abcdef123456",
        byte_size=1024,
    )
    resolved_asset = SimpleNamespace(
        metadata=asset_meta,
        absolute_path=SimpleNamespace(
            is_file=lambda: True,
            resolve=lambda: SimpleNamespace(relative_to=lambda root: "runs/test/cassian.png"),
        ),
    )
    assets.selected_asset = resolved_asset

    # Call canon.set_reference_anchor tool
    res = registry.dispatch(
        ToolCall(
            call_id="call_set_anchor",
            tool_id="canon.set_reference_anchor",
            arguments={
                "character_id": "cassian",
                "asset_id": "asset_cassian_portrait",
                "project_id": "test_project",
            },
        ),
        {"project_id": "test_project"},
    )

    assert res.status == "success", res.error
    assert res.output["asset_id"] == "asset_cassian_portrait"
    assert len(bible_without_ref.characters["cassian"].reference_assets) == 1
    assert bible_without_ref.characters["cassian"].reference_assets[0].asset_id == "asset_cassian_portrait"


def test_generation_tool_resolves_reference_asset_via_asset_registry_when_relative_path_not_on_root(monkeypatch, tmp_path):
    registry, assets = _registry_for_test(monkeypatch)

    # Reference asset stored in managed object store, not directly on project root
    ref_file = tmp_path / "managed_anchor.png"
    ref_file.write_bytes(b"anchor_bytes_content_789")
    import hashlib
    ref_hash = hashlib.sha256(b"anchor_bytes_content_789").hexdigest()

    # AssetRegistry resolves this asset_id to the real path
    asset_meta = SimpleNamespace(
        asset_id="art_cassian_anchor_managed",
        project_id="test_project",
        mime_type="image/png",
        content_sha256=ref_hash,
        byte_size=len(b"anchor_bytes_content_789"),
    )
    resolved_asset = SimpleNamespace(
        metadata=asset_meta,
        absolute_path=ref_file,
    )
    assets.selected_asset = resolved_asset

    # Story bible has managed_path relative to store (e.g. objects/xx/yy.webp) which doesn't exist on project root
    bible = SimpleNamespace(
        project_id="test_project",
        bible_version="1.0.0",
        canon_hash="hash_123",
        story_facts=[],
        characters={
            "cassian": SimpleNamespace(
                character_id="cassian",
                name="Cassian Vane",
                role="Antagonist",
                attributes=[{"id": "coat", "text": "velvet frock coat", "required": True}],
                visual_invariants=["midnight velvet frock coat"],
                restrictions=["never unkempt"],
                reference_assets=[
                    SimpleNamespace(
                        asset_id="art_cassian_anchor_managed",
                        file_path="objects/ab/managed_anchor.webp",  # Non-existent relative to project root
                        content_hash=ref_hash,
                        mime_type="image/png",
                    )
                ],
            )
        },
        character_assets={},
        style=SimpleNamespace(reference_assets=[], positive_constraints=[], negative_constraints=[]),
    )
    monkeypatch.setattr(registry_module, "_get_project_bible", lambda _project_id: bible)

    result = registry.dispatch(
        ToolCall(
            call_id="call_anchor_resolve",
            tool_id="generation.generate_image",
            arguments={
                "project_id": "test_project",
                "prompt": "Cassian walking in rain",
                "character_ids": ["cassian"],
            },
        ),
        {"project_id": "test_project", "offline_mode": True},
    )

    assert result.status == "success", result.error
    assert _CapturingAdapter.requests, "Adapter was not invoked"
    request = _CapturingAdapter.requests[0]
    assert request.reference_bytes == b"anchor_bytes_content_789"
    assert "art_cassian_anchor_managed" in request.parameters["reference_asset_ids"]



