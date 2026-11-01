"""
InkLoop S9 Capability Registry - Agent Canvas & Expressive Bubble Tools Tests.
Verifies autonomous agent control over canvas creation, template switching, panel reshaping,
expressive speech bubble lettering, and full page assembly.
"""
import pytest
from app.agent.schemas import ToolCall
from app.agent.registry import CapabilityRegistry


@pytest.fixture
def registry():
    return CapabilityRegistry.get_instance()


@pytest.fixture
def test_ctx():
    return {
        "project_id": "inkloop_test_canvas",
        "offline_mode": True,
    }


def test_canvas_create_page_from_template(registry, test_ctx):
    """Verifies agent can create a page with any of the 16 layout templates."""
    tool = registry.get_tool("canvas.create_page_from_template")
    assert tool is not None

    call = ToolCall(
        call_id="call_test_create",
        tool_id="canvas.create_page_from_template",
        arguments={
            "layout_template": "diagonal_slash_battle",
            "project_id": "inkloop_test_canvas",
            "reading_direction": "rtl",
        },
    )
    res = registry.dispatch(call, test_ctx)
    assert res.status.value == "success" if hasattr(res.status, "value") else str(res.status) == "success", f"Failed: {res.error}"
    out = res.output
    assert "page_id" in out
    assert out["layout_template"] == "diagonal_slash_battle"
    assert out["panel_count"] == 6
    assert len(out["panel_ids"]) == 6


def test_custom_page_tool_persists_polygon_panels_and_spacing_inspector_measures_real_gaps(registry, test_ctx):
    from app.agent.registry import IMAGE_CHAT_TOOL_IDS
    from app.agent.coordinator import _tools_for_turn
    from app.api.routers.editor import get_page_store
    from app.canvas.models import LayoutTemplateId

    assert "canvas.create_custom_page" in IMAGE_CHAT_TOOL_IDS
    assert "canvas.inspect_page_spacing" in IMAGE_CHAT_TOOL_IDS
    callable_chat_tools = registry.list_image_chat_tools()
    selected_tools = {tool.tool_id for tool in _tools_for_turn(callable_chat_tools, "scratch custom panels and inspect spacing")}
    assert "canvas.create_custom_page" in selected_tools
    assert "canvas.inspect_page_spacing" in selected_tools
    created = registry.dispatch(ToolCall(
        call_id="create_custom_scratch_page",
        tool_id="canvas.create_custom_page",
        arguments={
            "project_id": test_ctx["project_id"],
            "reading_direction": "ltr",
            "panel_geometry": [
                {"panel_id": "p_left", "reading_order": 1, "rect": {"x": 0, "y": 0, "width": 0.45, "height": 0.45}},
                {"panel_id": "p_right", "reading_order": 2, "polygon": [
                    {"x": 0.50, "y": 0}, {"x": 1.0, "y": 0},
                    {"x": 0.95, "y": 0.45}, {"x": 0.55, "y": 0.45},
                ]},
                {"panel_id": "p_lower", "reading_order": 3, "polygon": [
                    {"x": 0.0, "y": 0.55}, {"x": 0.45, "y": 0.50}, {"x": 0.42, "y": 1.0}, {"x": 0.0, "y": 1.0},
                ]},
            ],
        },
    ), test_ctx)
    assert created.status == "success", created.error
    assert created.output["created_from"] == "custom_panel_geometry"
    document = get_page_store().get(created.output["page_id"])
    assert document.layout.template_id == LayoutTemplateId.CUSTOM
    assert document.layout.get_panel("p_right").has_polygon
    assert document.layout.reading_order_panel_ids == ["p_left", "p_right", "p_lower"]

    measured = registry.dispatch(ToolCall(
        call_id="inspect_custom_panel_spacing",
        tool_id="canvas.inspect_page_spacing",
        arguments={"page_id": created.output["page_id"], "panel_id": "p_left"},
    ), test_ctx)
    assert measured.status == "success", measured.error
    assert measured.output["revision"] == document.revision
    assert measured.output["configured_gutters_px"]["horizontal"] == 18
    nearest = measured.output["panels"][0]["nearest_panels"][0]
    assert nearest["panel_id"] == "p_right"
    assert nearest["minimum_edge_gap_px"] == pytest.approx(40.5, abs=1.1)
    assert measured.output["panels"][0]["measured_margins_px"]["top"] == 45.0
    assert measured.output["panels"][0]["margin_clearance_valid"] is True
    assert measured.output["margin_clearance_valid"] is True
    assert get_page_store().get(created.output["page_id"]).revision == document.revision


def test_custom_page_rejects_overlapping_polygons_without_persisting(registry, test_ctx):
    from app.api.routers.editor import get_page_store

    result = registry.dispatch(ToolCall(
        call_id="reject_overlapping_custom_panels",
        tool_id="canvas.create_custom_page",
        arguments={"project_id": test_ctx["project_id"], "page_id": "page_invalid_custom_overlap", "panel_geometry": [
            {"panel_id": "p1", "reading_order": 1, "rect": {"x": 0, "y": 0, "width": 0.7, "height": 0.7}},
            {"panel_id": "p2", "reading_order": 2, "rect": {"x": 0.5, "y": 0.5, "width": 0.4, "height": 0.4}},
        ]},
    ), test_ctx)
    assert result.status == "failed"
    assert "overlap" in (result.error or "").casefold()
    with pytest.raises(Exception):
        get_page_store().get("page_invalid_custom_overlap")


def test_canvas_page_creation_can_persist_six_planned_story_beats_in_same_document(registry, test_ctx):
    scene_id = "six_beat_silent_seedling_story"
    events = [
        ("establishing", "Muse opens the hillside clinic at dawn.", "Muse at the clinic doorway"),
        ("action_preparation", "Muse notices a drooping seedling on the porch.", "the wilted leaves in the pot"),
        ("detail", "Muse touches the dry soil to check it.", "Muse's paw beside cracked soil"),
        ("action_continuation", "Muse waters the seedling carefully.", "water soaking the pot"),
        ("reaction", "A sunbeam returns and one leaf lifts.", "the first upright leaf"),
        ("aftermath", "Muse places the revived seedling in the bright clinic window.", "the plant glowing in the window"),
    ]
    planned = registry.dispatch(ToolCall(
        call_id="plan_six_beat_seedling_story",
        tool_id="planning.plan_panels",
        arguments={
            "project_id": test_ctx["project_id"],
            "scene_id": scene_id,
            "scene_summary": "Muse opens the clinic and helps a wilted seedling recover.",
            "reading_direction": "ltr",
            "beats": [{
                "beat_id": f"beat_{index:02d}",
                "panel_id": f"panel_{index:02d}",
                "narrative_function": function,
                "story_event": event,
                "reader_takeaway": event,
                "character_ids": ["muse"],
                "environment": "small sunlit hillside clinic",
                "visual_focus": focus,
                "emotional_intent": "gentle hope",
                "text": {"content_kind": "none", "carrier": "none"},
            } for index, (function, event, focus) in enumerate(events, 1)],
        },
    ), test_ctx)
    assert planned.status == "success", planned.error
    page_plans = [
        {**item, "scene_id": scene_id if index <= 3 else f"{scene_id}_followup"}
        for index, item in enumerate(planned.output["plans"], start=1)
    ]
    created = registry.dispatch(ToolCall(
        call_id="create_six_beat_seedling_page",
        tool_id="canvas.create_page_from_template",
        arguments={
            "project_id": test_ctx["project_id"],
            "layout_template": "six_panel_classic",
            "reading_direction": "ltr",
            "panel_plans": page_plans,
        },
    ), test_ctx)
    assert created.status == "success", created.error
    assert created.output["panel_count"] == 6
    assert created.output["planned_panel_count"] == 6
    assert created.output["story_scene_id"] is None
    assert created.output["story_scene_ids"] == [scene_id, f"{scene_id}_followup"]

    from app.api.routers.editor import get_page_store
    saved = get_page_store().get(created.output["page_id"])
    assert saved.project_id == test_ctx["project_id"]
    assert [slot.panel_id for slot in sorted(saved.layout.panel_slots, key=lambda item: item.reading_order)] == [
        f"panel_{index:02d}" for index in range(1, 7)
    ]
    assert all(slot.descriptor and slot.descriptor.narrative.scene_beat_description for slot in saved.layout.panel_slots)


def test_canvas_switch_page_template(registry, test_ctx):
    """Verifies agent can switch an existing page's layout template."""
    # 1. Create page
    call1 = ToolCall(
        call_id="call_test_create_sw",
        tool_id="canvas.create_page_from_template",
        arguments={
            "layout_template": "dynamic_shonen",
            "project_id": "inkloop_test_canvas",
        },
    )
    create_res = registry.dispatch(call1, test_ctx)
    page_id = create_res.output["page_id"]

    # 2. Switch template to three_tier_action_slant
    call2 = ToolCall(
        call_id="call_test_switch",
        tool_id="canvas.switch_page_template",
        arguments={
            "page_id": page_id,
            "expected_revision": 1,
            "layout_template": "three_tier_action_slant",
            "preserve_layers": True,
        },
    )
    sw_res = registry.dispatch(call2, test_ctx)
    assert sw_res.status.value == "success" if hasattr(sw_res.status, "value") else str(sw_res.status) == "success", f"Failed: {sw_res.error}"
    assert sw_res.output["layout_template"] == "three_tier_action_slant"
    assert sw_res.output["revision"] == 2
    assert sw_res.output["panel_count"] == 4


def test_canvas_add_speech_bubble(registry, test_ctx):
    """Verifies agent can place and style expressive speech bubbles."""
    call1 = ToolCall(
        call_id="call_test_create_bubble",
        tool_id="canvas.create_page_from_template",
        arguments={
            "layout_template": "four_panel_cinematic",
            "project_id": "inkloop_test_canvas",
        },
    )
    create_res = registry.dispatch(call1, test_ctx)
    page_id = create_res.output["page_id"]
    panel_id = create_res.output["panel_ids"][0]
    from app.api.routers.editor import get_page_store
    panel_slot = get_page_store().get(page_id).layout.get_panel(panel_id)

    # Add a shout_burst bubble with lightning bolt tail
    call2 = ToolCall(
        call_id="call_test_add_bubble",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": page_id,
            "expected_revision": 1,
            "panel_id": panel_id,
            "text": "Nour! Watch out!",
            "speaker": "Nour",
            "speaker_character_id": "nour",
            "bubble_shape": "shout_burst",
            "tail_type": "lightning_bolt",
            "tail_target": {"x": panel_slot.rect.center.x, "y": panel_slot.rect.center.y + 40},
            "font_size": 28.0,
        },
    )
    bubble_res = registry.dispatch(call2, test_ctx)
    assert bubble_res.status.value == "success" if hasattr(bubble_res.status, "value") else str(bubble_res.status) == "success", f"Failed: {bubble_res.error}"
    out = bubble_res.output
    assert out["page_id"] == page_id
    assert out["bubble_shape"] == "shout_burst"
    assert out["tail_type"] == "lightning_bolt"
    assert out["revision"] == 2
    assert out["bounds"]["x"] >= 0 and out["bounds"]["y"] >= 0
    assert out["bounds"]["x"] + out["bounds"]["width"] <= 900
    assert out["bounds"]["y"] + out["bounds"]["height"] <= 1200

    saved_document = get_page_store().get(page_id)
    saved_bubble = next(layer for layer in saved_document.layers if layer.layer_id == out["bubble_id"])
    assert saved_bubble.panel_id == panel_id
    assert saved_bubble.metadata["speaker"] == "Nour"
    assert saved_bubble.metadata["has_halftone_shadow"] is False


def test_agent_rejects_dialogue_that_cannot_fit_selected_panel(registry, test_ctx):
    create = registry.dispatch(
        ToolCall(
            call_id="call_create_bubble_overflow_page",
            tool_id="canvas.create_page_from_template",
            arguments={"layout_template": "four_panel_cinematic", "project_id": test_ctx["project_id"]},
        ),
        test_ctx,
    )
    result = registry.dispatch(
        ToolCall(
            call_id="call_bubble_overflow",
            tool_id="canvas.add_speech_bubble",
            arguments={
                "page_id": create.output["page_id"],
                "expected_revision": create.output["revision"],
                "panel_id": create.output["panel_ids"][0],
                "text": "This is an intentionally very long line of dialogue that cannot fit safely inside this little panel without becoming unreadable. " * 30,
                "font_size": 28,
            },
        ),
        test_ctx,
    )
    assert str(getattr(result.status, "value", result.status)) == "failed"
    assert result.error_code == "ERR_BUBBLE_TEXT_OVERFLOW"


def test_bubble_can_cross_panel_edge_but_stays_on_page_and_reports_collisions(registry, test_ctx):
    create = registry.dispatch(
        ToolCall(call_id="create_bubble_bleed_page", tool_id="canvas.create_page_from_template", arguments={
            "layout_template": "four_panel_cinematic", "project_id": test_ctx["project_id"],
        }),
        test_ctx,
    )
    page_id, panel_id = create.output["page_id"], create.output["panel_ids"][0]
    from app.api.routers.editor import get_page_store
    page = get_page_store().get(page_id)
    panel = page.layout.get_panel(panel_id)
    placement = {"x": panel.rect.x - 20, "y": panel.rect.y + 30}

    first = registry.dispatch(ToolCall(
        call_id="bubble_bleed_first", tool_id="canvas.add_speech_bubble", arguments={
            "page_id": page_id, "expected_revision": page.revision, "panel_id": panel_id,
            "text": "Look over here", "position": placement, "width": 120, "height": 60,
            "tail_type": "none",
        },
    ), test_ctx)
    assert str(getattr(first.status, "value", first.status)) == "success", first.error
    assert any(warning["code"] == "BUBBLE_CROSSES_PANEL_EDGE" for warning in first.output["warnings"])
    assert first.output["bounds"]["x"] + first.output["bounds"]["width"] <= page.layout.trim_box.right

    second = registry.dispatch(ToolCall(
        call_id="bubble_bleed_overlap", tool_id="canvas.add_speech_bubble", arguments={
            "page_id": page_id, "expected_revision": first.output["revision"], "panel_id": panel_id,
            "text": "Same area", "position": placement, "width": 120, "height": 60,
            "tail_type": "none",
        },
    ), test_ctx)
    assert str(getattr(second.status, "value", second.status)) == "success", second.error
    assert any(warning["code"] == "BUBBLE_OVERLAP" for warning in second.output["warnings"])

    outside = registry.dispatch(ToolCall(
        call_id="bubble_outside_page", tool_id="canvas.add_speech_bubble", arguments={
            "page_id": page_id, "expected_revision": second.output["revision"], "panel_id": panel_id,
            "text": "Off page", "position": {"x": page.layout.trim_box.right - 20, "y": panel.rect.y + 30},
            "width": 100, "height": 60, "tail_type": "none",
        },
    ), test_ctx)
    assert str(getattr(outside.status, "value", outside.status)) == "failed"
    assert outside.error_code == "ERR_BUBBLE_OUTSIDE_PAGE"
    assert get_page_store().get(page_id).revision == second.output["revision"]


def test_agent_requires_explicit_multi_character_speaker_and_reuses_confirmed_anchor(registry, test_ctx):
    create = registry.dispatch(
        ToolCall(call_id="create_speaker_anchor_page", tool_id="canvas.create_page_from_template", arguments={
            "layout_template": "four_panel_cinematic", "project_id": test_ctx["project_id"],
        }),
        test_ctx,
    )
    page_id, panel_id = create.output["page_id"], create.output["panel_ids"][0]
    from app.api.routers.editor import get_page_store
    page = get_page_store().get(page_id)
    panel = page.layout.get_panel(panel_id)
    agent_ctx = {**test_ctx, "_agent_chat": True, "selected_character_ids": ["nour", "another_character"]}

    missing_speaker = registry.dispatch(ToolCall(
        call_id="missing_speaker", tool_id="canvas.add_speech_bubble", arguments={
            "page_id": page_id, "expected_revision": page.revision, "panel_id": panel_id,
            "text": "You first.",
        },
    ), agent_ctx)
    assert str(getattr(missing_speaker.status, "value", missing_speaker.status)) == "failed"
    assert missing_speaker.error_code == "ERR_BUBBLE_SPEAKER_REQUIRED"

    unselected_speaker = registry.dispatch(ToolCall(
        call_id="unselected_speaker", tool_id="canvas.add_speech_bubble", arguments={
            "page_id": page_id, "expected_revision": page.revision, "panel_id": panel_id,
            "text": "I found the notice.", "speaker_character_id": "muse",
        },
    ), agent_ctx)
    assert str(getattr(unselected_speaker.status, "value", unselected_speaker.status)) == "failed"
    assert unselected_speaker.error_code == "ERR_BUBBLE_SPEAKER_NOT_SELECTED"

    missing_anchor = registry.dispatch(ToolCall(
        call_id="missing_anchor", tool_id="canvas.add_speech_bubble", arguments={
            "page_id": page_id, "expected_revision": page.revision, "panel_id": panel_id,
            "text": "I am Nour.", "speaker_character_id": "nour",
        },
    ), agent_ctx)
    assert str(getattr(missing_anchor.status, "value", missing_anchor.status)) == "failed"
    assert missing_anchor.error_code == "ERR_BUBBLE_TAIL_ANCHOR_REQUIRED"

    confirmed = registry.dispatch(ToolCall(
        call_id="confirm_nour_anchor", tool_id="canvas.add_speech_bubble", arguments={
            "page_id": page_id, "expected_revision": page.revision, "panel_id": panel_id,
            "text": "I am here.", "speaker_character_id": "nour",
            "tail_target": {"x": panel.rect.center.x, "y": panel.rect.center.y},
        },
    ), test_ctx)
    assert str(getattr(confirmed.status, "value", confirmed.status)) == "success", confirmed.error

    reused = registry.dispatch(ToolCall(
        call_id="reuse_nour_anchor", tool_id="canvas.add_speech_bubble", arguments={
            "page_id": page_id, "expected_revision": confirmed.output["revision"], "panel_id": panel_id,
            "text": "Then I will speak.", "speaker_character_id": "nour",
        },
    ), agent_ctx)
    assert str(getattr(reused.status, "value", reused.status)) == "success", reused.error
    saved = get_page_store().get(page_id)
    bubble = next(layer for layer in saved.layers if layer.layer_id == reused.output["bubble_id"])
    assert bubble.metadata["speaker_character_id"] == "nour"
    assert bubble.metadata["tail_target"] == {"x": panel.rect.center.x, "y": panel.rect.center.y}
    assert bubble.metadata["tail_anchor_source"] == "saved_character_anchor"
    assert bubble.metadata["font_size"] == 24


def test_agent_bubble_uses_panel_artwork_for_head_target_and_collision_free_position(registry, test_ctx, monkeypatch, tmp_path):
    import io
    from types import SimpleNamespace
    from PIL import Image, ImageDraw
    from app.api.routers import assets as assets_router, editor as editor_router
    from app.contracts.artifacts import AssetType
    from app.editor.store import PageDocumentStore
    from app.storage.registry import AssetRegistry

    asset_registry = AssetRegistry(tmp_path / "artifact_store", tmp_path / "assets.db", tmp_path)
    page_store = PageDocumentStore(tmp_path / "pages.db", asset_registry)
    monkeypatch.setattr(assets_router, "get_registry", lambda: asset_registry)
    monkeypatch.setattr(editor_router, "get_page_store", lambda: page_store)
    monkeypatch.setattr("app.agent.registry._get_project_bible", lambda _project_id: SimpleNamespace(
        characters={"nour": SimpleNamespace(name="Nour")},
    ))

    image = Image.new("RGB", (600, 800), (235, 238, 240))
    draw = ImageDraw.Draw(image)
    draw.ellipse((210, 110, 390, 300), fill=(235, 195, 165), outline=(20, 20, 20), width=5)
    draw.rounded_rectangle((170, 270, 430, 710), radius=60, fill=(35, 45, 68), outline=(20, 20, 20), width=5)
    output = io.BytesIO()
    image.save(output, format="PNG")
    art = asset_registry.ingest_bytes(
        output.getvalue(), "single_speaker.png", test_ctx["project_id"], AssetType.IMAGE_REFERENCE,
        name="Single speaker test artwork",
    )

    created = registry.dispatch(ToolCall(
        call_id="create_page_for_bubble_bounds",
        tool_id="canvas.create_custom_page",
        arguments={"project_id": test_ctx["project_id"], "panel_geometry": [
            {"panel_id": "speaker_panel", "reading_order": 1, "rect": {"x": 0, "y": 0, "width": 1, "height": 1}},
        ]},
    ), test_ctx)
    assert created.status == "success", created.error
    placed = registry.dispatch(ToolCall(
        call_id="place_speaker_test_art",
        tool_id="canvas.place_panel_artwork",
        arguments={"page_id": created.output["page_id"], "expected_revision": 1, "panel_id": "speaker_panel", "asset_id": art.asset_id},
    ), test_ctx)
    assert placed.status == "success", placed.error
    agent_ctx = {**test_ctx, "_agent_chat": True, "selected_character_ids": ["nour", "another_selected_character"]}
    detected = registry.dispatch(ToolCall(
        call_id="measure_speaker_test_art",
        tool_id="canvas.detect_character_anchor",
        arguments={"page_id": created.output["page_id"], "panel_id": "speaker_panel"},
    ), agent_ctx)
    assert detected.status == "success", detected.error
    assert detected.output["identity_recognized"] is False

    bubble = registry.dispatch(ToolCall(
        call_id="auto_place_speaker_bubble",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": created.output["page_id"], "expected_revision": placed.output["revision"],
            "panel_id": "speaker_panel", "text": "What was that?", "speaker_character_id": "nour",
            "emotional_intent": "curious wonder", "delivery": "questioning",
            "story_event": "Nour notices a strange moving shadow.",
            "dialogue_text": "What was that?",
            "action_context": None,
            "bubble_preset_id": "bubble_spoken_classic",
            "position": {"x": detected.output["character_bounds"]["x"], "y": detected.output["character_bounds"]["y"]},
        },
    ), agent_ctx)
    assert bubble.status == "success", bubble.error
    assert bubble.output["bubble_shape"] == "scalloped_flower"
    assert bubble.output["bubble_preset_id"] is None
    assert bubble.output["tail_anchor_source"] == "multi_selected_focal_estimate"
    assert any(item["code"] == "MULTI_CHARACTER_SPEAKER_ANCHOR_IS_FOCAL_ESTIMATE" for item in bubble.output["warnings"])
    assert any(item["code"] == "AGENT_POSITION_AUTO_ADJUSTED" for item in bubble.output["warnings"])
    bubble_bounds = bubble.output["bounds"]
    subject = detected.output["character_bounds"]
    assert bubble_bounds["x"] + bubble_bounds["width"] <= subject["x"] or subject["x"] + subject["width"] <= bubble_bounds["x"] or bubble_bounds["y"] + bubble_bounds["height"] <= subject["y"] or subject["y"] + subject["height"] <= bubble_bounds["y"]
    assert bubble.output["tail_target"]["x"] == pytest.approx(subject["x"] + subject["width"] / 2.0, abs=1.1)
    saved_doc = page_store.get(created.output["page_id"])
    saved_bubble = next(layer for layer in saved_doc.layers if layer.layer_id == bubble.output["bubble_id"])
    assert saved_bubble.metadata["requested_bubble_preset_id"] == "bubble_spoken_classic"
    assert saved_bubble.metadata["font_size"] == 24.0
    assert saved_bubble.metadata["align"] == "center"
    assert saved_bubble.metadata["direction"] == "ltr"
    assert saved_bubble.metadata["text_measurement"]["source"] == "Pillow font metrics"
    assert saved_bubble.metadata["text_measurement"]["line_count"] >= 1
    assert saved_bubble.metadata["text_measurement"]["max_line_width_px"] > 0
    panel_slot = saved_doc.layout.get_panel("speaker_panel")
    assert bubble_bounds["width"] < panel_slot.rect.width * 0.78


def test_agent_bubble_measures_arabic_and_mixed_script_with_the_selected_font(registry, test_ctx, monkeypatch):
    from app.contracts.geometry import Rect
    from app.api.routers.editor import get_page_store

    created = registry.dispatch(ToolCall(
        call_id="create_multilingual_bubble_page", tool_id="canvas.create_page_from_template",
        arguments={"layout_template": "four_panel_cinematic", "project_id": test_ctx["project_id"]},
    ), test_ctx)
    assert created.status == "success", created.error
    panel_id = created.output["panel_ids"][0]
    monkeypatch.setattr(
        "app.canvas.character_locator.locate_character_in_panel",
        lambda *_args, **_kwargs: Rect(x=130, y=180, width=150, height=240),
    )
    agent_ctx = {**test_ctx, "_agent_chat": True, "selected_character_ids": ["nour"]}
    revision = created.output["revision"]
    texts = ["أين المصباح؟", "Muse, أين الضوء?"]
    directions = []

    for index, text in enumerate(texts, start=1):
        result = registry.dispatch(ToolCall(
            call_id=f"measured_multilingual_bubble_{index}", tool_id="canvas.add_speech_bubble",
            arguments={
                "page_id": created.output["page_id"], "expected_revision": revision,
                "panel_id": panel_id, "text": text, "speaker_character_id": "nour",
            },
        ), agent_ctx)
        assert result.status == "success", result.error
        revision = result.output["revision"]
        page = get_page_store().get(created.output["page_id"])
        bubble = next(layer for layer in page.layers if layer.layer_id == result.output["bubble_id"])
        assert bubble.metadata["text_measurement"]["source"] == "Pillow font metrics"
        assert bubble.metadata["text_measurement"]["max_line_width_px"] > 0
        assert bubble.metadata["font_size"] == 24.0
        directions.append(bubble.metadata["direction"])

    assert directions == ["rtl", "ltr"]


def test_canvas_update_speech_bubble_preserves_id_and_rebuilds_tail_and_font(registry, test_ctx):
    from uuid import uuid4
    test_run_id = uuid4().hex
    create = registry.dispatch(
        ToolCall(
            call_id=f"{test_run_id}_create_bubble_update_page",
            tool_id="canvas.create_page_from_template",
            arguments={"layout_template": "four_panel_cinematic", "project_id": test_ctx["project_id"]},
        ),
        test_ctx,
    )
    page_id = create.output["page_id"]
    panel_id = create.output["panel_ids"][0]
    added = registry.dispatch(
        ToolCall(
            call_id=f"{test_run_id}_add_bubble_to_update",
            tool_id="canvas.add_speech_bubble",
            arguments={
                "page_id": page_id,
                "expected_revision": create.output["revision"],
                "panel_id": panel_id,
                "text": "Check this.",
                "bubble_preset_id": "bubble_spoken_halftone",
            },
        ),
        test_ctx,
    )
    assert str(getattr(added.status, "value", added.status)) == "success", added.error
    bubble_id = added.output["bubble_id"]

    updated = registry.dispatch(
        ToolCall(
            call_id=f"{test_run_id}_refine_bubble_geometry_and_font",
            tool_id="canvas.update_speech_bubble",
            arguments={
                "page_id": page_id,
                "expected_revision": added.output["revision"],
                "bubble_id": bubble_id,
                "properties": {
                    "text": "Look at the chart.",
                    "position": {"x": 80, "y": 75},
                    "width": 210,
                    "height": 58,
                    "tail_target": {"x": 180, "y": 210},
                    "font_family": "Comic Neue",
                    "font_weight": "bold",
                    "line_height": 1.1,
                },
            },
        ),
        test_ctx,
    )

    assert str(getattr(updated.status, "value", updated.status)) == "success", updated.error
    assert updated.output["bubble_id"] == bubble_id
    assert updated.output["revision"] == added.output["revision"] + 1
    from app.api.routers.editor import get_page_store
    document = get_page_store().get(page_id)
    saved = next(layer for layer in document.layers if layer.layer_id == bubble_id)
    assert saved.panel_id == panel_id
    assert saved.metadata["text"] == "Look at the chart."
    assert saved.metadata["font_family"] == "Comic Neue"
    assert saved.metadata["font_weight"] == "bold"
    assert saved.metadata["tail_target"] == {"x": 180.0, "y": 210.0}
    assert saved.metadata["svg_path"]
    assert saved.metadata["tail_path"]


def test_canvas_update_speech_bubble_rejects_stale_revision_without_write(registry, test_ctx):
    from uuid import uuid4
    test_run_id = uuid4().hex
    create = registry.dispatch(
        ToolCall(
            call_id=f"{test_run_id}_create_stale_bubble_update_page",
            tool_id="canvas.create_page_from_template",
            arguments={"layout_template": "four_panel_cinematic", "project_id": test_ctx["project_id"]},
        ),
        test_ctx,
    )
    added = registry.dispatch(
        ToolCall(
            call_id=f"{test_run_id}_add_stale_bubble_update",
            tool_id="canvas.add_speech_bubble",
            arguments={
                "page_id": create.output["page_id"],
                "expected_revision": create.output["revision"],
                "panel_id": create.output["panel_ids"][0],
                "text": "Read carefully.",
            },
        ),
        test_ctx,
    )
    assert str(getattr(added.status, "value", added.status)) == "success", added.error
    result = registry.dispatch(
        ToolCall(
            call_id=f"{test_run_id}_stale_bubble_update",
            tool_id="canvas.update_speech_bubble",
            arguments={
                "page_id": create.output["page_id"],
                "expected_revision": create.output["revision"],
                "bubble_id": added.output["bubble_id"],
                "properties": {"font_family": "Comic Neue"},
            },
        ),
        test_ctx,
    )
    assert str(getattr(result.status, "value", result.status)) == "failed"
    assert result.error_code == "ERR_STALE_PAGE_REVISION"
    from app.api.routers.editor import get_page_store
    assert get_page_store().get(create.output["page_id"]).revision == added.output["revision"]


def test_agent_searches_and_applies_stable_layout_and_bubble_preset_ids(registry, test_ctx):
    layout_search = registry.dispatch(
        ToolCall(
            call_id="call_search_layouts",
            tool_id="canvas.search_panel_layout_presets",
            arguments={"query": "comedic setup and payoff", "limit": 5},
        ),
        test_ctx,
    )
    assert str(getattr(layout_search.status, "value", layout_search.status)) == "success"
    assert layout_search.output["count"] > 0
    assert all(item["id"].startswith("panel_layout_") and item["use_case"] for item in layout_search.output["presets"])

    create = registry.dispatch(
        ToolCall(
            call_id="call_create_recipe_layout",
            tool_id="canvas.create_page_from_template",
            arguments={
                "panel_preset_id": "panel_layout_dynamic_shonen_action",
                "project_id": test_ctx["project_id"],
            },
        ),
        test_ctx,
    )
    assert str(getattr(create.status, "value", create.status)) == "success", create.error
    assert create.output["panel_preset_id"] == "panel_layout_dynamic_shonen_action"
    assert create.output["panel_count"] == 4

    bubble_search = registry.dispatch(
        ToolCall(
            call_id="call_search_bubbles",
            tool_id="canvas.search_bubble_presets",
            arguments={"query": "urgent shout", "limit": 5},
        ),
        test_ctx,
    )
    assert str(getattr(bubble_search.status, "value", bubble_search.status)) == "success"
    assert any(item["id"] == "bubble_shout_halftone" for item in bubble_search.output["presets"])

    bubble = registry.dispatch(
        ToolCall(
            call_id="call_apply_bubble_preset",
            tool_id="canvas.add_speech_bubble",
            arguments={
                "page_id": create.output["page_id"],
                "expected_revision": create.output["revision"],
                "panel_id": create.output["panel_ids"][0],
                "text": "Look out!",
                "bubble_preset_id": "bubble_shout_halftone",
            },
        ),
        test_ctx,
    )
    assert str(getattr(bubble.status, "value", bubble.status)) == "success", bubble.error
    assert bubble.output["bubble_preset_id"] == "bubble_shout_halftone"
    assert bubble.output["bubble_shape"] == "shout_burst"
    assert bubble.output["bubble_id"].startswith("bbl_")
    assert bubble.output["revision"] == create.output["revision"] + 1

    from app.api.routers.editor import get_page_store
    saved_document = get_page_store().get(create.output["page_id"])
    assert saved_document.layout.layout_preset_id == "panel_layout_dynamic_shonen_action"
    saved_bubble = next(layer for layer in saved_document.layers if layer.layer_id == bubble.output["bubble_id"])
    assert saved_bubble.metadata["bubble_preset_id"] == "bubble_shout_halftone"
    assert saved_bubble.metadata["bubble_id"] == bubble.output["bubble_id"]


def test_canvas_assemble_full_page(registry, test_ctx):
    """Verifies master one-shot page assembly tool."""
    call = ToolCall(
        call_id="call_test_assemble",
        tool_id="canvas.assemble_full_page",
        arguments={
            "layout_template": "dynamic_shonen",
            "project_id": "inkloop_test_canvas",
            "reading_direction": "rtl",
            "panel_assignments": [
                {
                    "panel_id": "panel_01",
                    "dialogues": [
                        {
                            "text": "The quiet dawn arrives...",
                            "bubble_shape": "oval",
                            "tail_type": "smooth_pointer",
                        }
                    ],
                },
                {
                    "panel_id": "panel_02",
                    "dialogues": [
                        {
                            "text": "Time for breakfast tea.",
                            "bubble_shape": "thought_cloud",
                            "tail_type": "bubble_chain",
                        }
                    ],
                },
            ],
        },
    )
    res = registry.dispatch(call, test_ctx)
    assert res.status.value == "success" if hasattr(res.status, "value") else str(res.status) == "success", f"Failed: {res.error}"
    out = res.output
    assert "page_id" in out
    assert out["layout_template"] == "dynamic_shonen"
    assert out["placed_bubbles_count"] == 2


def test_canvas_assembly_reports_invalid_panel_instead_of_fake_success(registry, test_ctx):
    result = registry.dispatch(
        ToolCall(
            call_id="call_assemble_bad_panel",
            tool_id="canvas.assemble_full_page",
            arguments={
                "layout_template": "dynamic_shonen",
                "project_id": test_ctx["project_id"],
                "panel_assignments": [{
                    "panel_id": "panel_does_not_exist",
                    "dialogues": [{"text": "This must not be reported as placed."}],
                }],
            },
        ),
        test_ctx,
    )
    assert str(getattr(result.status, "value", result.status)) == "failed"
    assert result.error_code == "ERR_PAGE_ASSEMBLY_PARTIAL"
    assert "panel_does_not_exist" in result.error
    assert "inspect page" in result.error
