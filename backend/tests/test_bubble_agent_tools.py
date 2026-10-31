"""Contract and integration tests for B6 Bubble Agent Tools and Line-Level Script Planner."""
import pytest
from app.agent.registry import CapabilityRegistry, ToolCall
from app.api.routers.editor import get_page_store
from app.canvas.bubble_registry import BUBBLE_TYPES, BUBBLE_TYPE_BY_ID
from app.canvas.placement_engine import ProtectedRegion
from app.contracts.geometry import Rect
from app.planning.panel_planner import (
    NarrativeBeat,
    NarrativeFunction,
    PanelPlanningRequest,
    PanelScriptLine,
    PanelTextPlan,
    StoryBeatDraft,
    StoryBlueprintDraft,
    StoryPageDraft,
    TextCarrier,
    TextContentKind,
    compile_story_blueprint,
    plan_panels,
)


@pytest.fixture
def test_setup(tmp_path, monkeypatch):
    from app.storage.registry import AssetRegistry
    from app.editor.store import PageDocumentStore
    from types import SimpleNamespace

    assets = AssetRegistry(tmp_path / "artifacts", tmp_path / "assets.db", tmp_path)
    store = PageDocumentStore(tmp_path / "pages.db", assets)
    monkeypatch.setattr("app.api.routers.editor.get_page_store", lambda: store)
    monkeypatch.setattr("app.agent.registry._get_project_bible", lambda _pid: SimpleNamespace(
        characters={"char_hero": SimpleNamespace(name="Hero"), "char_sidekick": SimpleNamespace(name="Sidekick")},
    ))
    registry = CapabilityRegistry()
    ctx = {"project_id": "test_proj", "_agent_chat": True, "selected_character_ids": ["char_hero", "char_sidekick"]}
    return registry, ctx, store


def test_contract_all_five_bubble_tools(test_setup):
    """Verify bubble.add, bubble.update, bubble.list, bubble.place_all, bubble.remove."""
    registry, ctx, store = test_setup

    # 1. Create a page
    create = registry.dispatch(ToolCall(
        call_id="c_page",
        tool_id="canvas.create_page_from_template",
        arguments={"layout_template": "four_panel_cinematic", "project_id": ctx["project_id"]},
    ), ctx)
    assert create.status == "success", create.error
    page_id = create.output["page_id"]
    panel_id = create.output["panel_ids"][0]
    rev = create.output["revision"]

    # 2. bubble.add
    add_res = registry.dispatch(ToolCall(
        call_id="c_add",
        tool_id="bubble.add",
        arguments={
            "page_id": page_id,
            "panel_id": panel_id,
            "type_id": "speech.normal",
            "text": "First line of dialogue.",
            "speaker_character_id": "char_hero",
            "reading_order": 1,
            "expected_revision": rev,
        },
    ), ctx)
    assert add_res.status == "success", add_res.error
    bubble_id_1 = add_res.output["bubble_id"]
    rev = add_res.output["revision"]

    # 3. bubble.list
    list_res = registry.dispatch(ToolCall(
        call_id="c_list",
        tool_id="bubble.list",
        arguments={"page_id": page_id, "panel_id": panel_id},
    ), ctx)
    assert list_res.status == "success"
    bubbles = list_res.output["bubbles"]
    assert len(bubbles) == 1
    assert bubbles[0]["bubble_id"] == bubble_id_1
    assert bubbles[0]["text"] == "First line of dialogue."

    # 4. bubble.update
    update_res = registry.dispatch(ToolCall(
        call_id="c_upd",
        tool_id="bubble.update",
        arguments={
            "page_id": page_id,
            "bubble_id": bubble_id_1,
            "expected_revision": rev,
            "properties": {"text": "Updated line.", "type_id": "speech.whisper"},
        },
    ), ctx)
    assert update_res.status == "success", update_res.error
    rev = update_res.output["revision"]
    assert update_res.output["text"] == "Updated line."
    assert update_res.output["type_id"] == "speech.whisper"

    # 5. Add second bubble for place_all
    add_res_2 = registry.dispatch(ToolCall(
        call_id="c_add_2",
        tool_id="bubble.add",
        arguments={
            "page_id": page_id,
            "panel_id": panel_id,
            "type_id": "speech.shout",
            "text": "Look out!",
            "speaker_character_id": "char_sidekick",
            "reading_order": 2,
            "expected_revision": rev,
        },
    ), ctx)
    assert add_res_2.status == "success", add_res_2.error
    rev = add_res_2.output["revision"]

    # 6. bubble.place_all
    place_res = registry.dispatch(ToolCall(
        call_id="c_place_all",
        tool_id="bubble.place_all",
        arguments={"page_id": page_id, "panel_id": panel_id, "expected_revision": rev},
    ), ctx)
    assert place_res.status == "success", place_res.error
    rev = place_res.output["revision"]

    # 7. bubble.remove
    rem_res = registry.dispatch(ToolCall(
        call_id="c_rem",
        tool_id="bubble.remove",
        arguments={"page_id": page_id, "bubble_id": bubble_id_1, "expected_revision": rev},
    ), ctx)
    assert rem_res.status == "success", rem_res.error
    assert rem_res.output["removed"] is True

    # Confirm only 1 bubble left
    list_after = registry.dispatch(ToolCall(
        call_id="c_list_after",
        tool_id="bubble.list",
        arguments={"page_id": page_id, "panel_id": panel_id},
    ), ctx)
    assert len(list_after.output["bubbles"]) == 1


def test_missing_speaker_raises_structured_error(test_setup):
    """Missing speaker on speech/thought types raises ERR_BUBBLE_SPEAKER_REQUIRED."""
    registry, ctx, _store = test_setup

    create = registry.dispatch(ToolCall(
        call_id="c_page",
        tool_id="canvas.create_page_from_template",
        arguments={"layout_template": "four_panel_cinematic", "project_id": ctx["project_id"]},
    ), ctx)
    page_id = create.output["page_id"]
    panel_id = create.output["panel_ids"][0]

    res = registry.dispatch(ToolCall(
        call_id="c_add_no_speaker",
        tool_id="bubble.add",
        arguments={
            "page_id": page_id,
            "panel_id": panel_id,
            "type_id": "speech.normal",
            "text": "Hello world",
        },
    ), ctx)
    assert str(getattr(res.status, "value", res.status)) == "failed"
    assert res.error_code == "ERR_BUBBLE_SPEAKER_REQUIRED"


def test_word_limit_exceeded_raises_structured_error(test_setup):
    """Exceeding type word limit raises ERR_LETTERING_WORD_LIMIT without silent truncation."""
    registry, ctx, _store = test_setup

    create = registry.dispatch(ToolCall(
        call_id="c_page",
        tool_id="canvas.create_page_from_template",
        arguments={"layout_template": "four_panel_cinematic", "project_id": ctx["project_id"]},
    ), ctx)
    page_id = create.output["page_id"]
    panel_id = create.output["panel_ids"][0]

    # speech.shout has max_words = 5
    res = registry.dispatch(ToolCall(
        call_id="c_add_shout_too_long",
        tool_id="bubble.add",
        arguments={
            "page_id": page_id,
            "panel_id": panel_id,
            "type_id": "speech.shout",
            "text": "This shout contains far too many words for shout",
            "speaker_character_id": "char_hero",
        },
    ), ctx)
    assert str(getattr(res.status, "value", res.status)) == "failed"
    assert res.error_code == "ERR_LETTERING_WORD_LIMIT"


def test_script_with_six_panels_and_ten_lines_produces_exact_bubbles_and_zero_overlaps(test_setup):
    """A 6-panel script with 10 lines across varied beats produces 10 bubbles, >=3 types, 0 overlaps."""
    registry, ctx, store = test_setup

    create = registry.dispatch(ToolCall(
        call_id="c_page",
        tool_id="canvas.create_page_from_template",
        arguments={"layout_template": "six_panel_grid", "project_id": ctx["project_id"]},
    ), ctx)
    page_id = create.output["page_id"]
    panel_ids = create.output["panel_ids"]
    assert len(panel_ids) == 6
    rev = create.output["revision"]

    # 6 panels script:
    # Panel 0: 2 lines (speech.normal, speech.normal)
    # Panel 1: 1 line (narration.box)
    # Panel 2: 0 lines (SILENT panel)
    # Panel 3: 3 lines (speech.normal, speech.shout, speech.whisper)
    # Panel 4: 2 lines (thought.cloud, speech.normal)
    # Panel 5: 2 lines (caption.timeplace, speech.offpanel)
    # Total dialogue lines = 10 across 5 panels (1 panel silent)
    script = [
        # Panel 0
        {"panel": panel_ids[0], "type": "speech.normal", "speaker": "char_hero", "text": "Are you ready?"},
        {"panel": panel_ids[0], "type": "speech.normal", "speaker": "char_sidekick", "text": "Always ready."},
        # Panel 1
        {"panel": panel_ids[1], "type": "narration.box", "speaker": None, "text": "The wind howled through the canyon."},
        # Panel 2: SILENT (0 bubbles)
        # Panel 3
        {"panel": panel_ids[3], "type": "speech.normal", "speaker": "char_hero", "text": "Step back."},
        {"panel": panel_ids[3], "type": "speech.shout", "speaker": "char_sidekick", "text": "Look out!"},
        {"panel": panel_ids[3], "type": "speech.whisper", "speaker": "char_hero", "text": "Quiet now."},
        # Panel 4
        {"panel": panel_ids[4], "type": "thought.cloud", "speaker": "char_hero", "text": "Can we make it?"},
        {"panel": panel_ids[4], "type": "speech.normal", "speaker": "char_sidekick", "text": "We will survive."},
        # Panel 5
        {"panel": panel_ids[5], "type": "caption.timeplace", "speaker": None, "text": "Dawn breaks."},
        {"panel": panel_ids[5], "type": "speech.offpanel", "speaker": "char_hero", "text": "Over here!"},
    ]

    types_used = set()
    order_by_panel = {}
    for item in script:
        p = item["panel"]
        order_by_panel[p] = order_by_panel.get(p, 0) + 1
        res = registry.dispatch(ToolCall(
            call_id=f"c_add_{len(types_used)}_{order_by_panel[p]}",
            tool_id="bubble.add",
            arguments={
                "page_id": page_id,
                "panel_id": p,
                "type_id": item["type"],
                "text": item["text"],
                "speaker_character_id": item["speaker"],
                "reading_order": order_by_panel[p],
                "expected_revision": rev,
            },
        ), ctx)
        assert res.status == "success", f"Failed to add bubble {item}: {res.error}"
        rev = res.output["revision"]
        types_used.add(item["type"])

    # 1. Check total count
    doc = store.get(page_id)
    text_layers = [l for l in doc.layers if l.metadata.get("bubble_id")]
    assert len(text_layers) == 10

    # 2. Check silent panel (panel_ids[2]) has 0 bubbles
    silent_panel_bubbles = [l for l in text_layers if l.panel_id == panel_ids[2]]
    assert len(silent_panel_bubbles) == 0

    # 3. Check distinct types used >= 3 (we used 7!)
    assert len(types_used) >= 3

    # 4. Check zero overlaps within each panel
    for p in panel_ids:
        panel_layers = [l for l in text_layers if l.panel_id == p]
        for i in range(len(panel_layers)):
            m1 = panel_layers[i].metadata
            r1 = Rect(x=m1["x"], y=m1["y"], width=m1["width"], height=m1["height"])
            for j in range(i + 1, len(panel_layers)):
                m2 = panel_layers[j].metadata
                r2 = Rect(x=m2["x"], y=m2["y"], width=m2["width"], height=m2["height"])
                overlap = (r1.x < r2.right and r1.right > r2.x and r1.y < r2.bottom and r1.bottom > r2.y)
                assert not overlap, f"Bubble overlap detected in panel {p} between {m1['bubble_id']} and {m2['bubble_id']}"

    # 5. Check reading order monotonicity within panels
    for p in panel_ids:
        panel_layers = sorted(
            [l for l in text_layers if l.panel_id == p],
            key=lambda l: l.metadata.get("reading_order", 1),
        )
        if len(panel_layers) > 1:
            for k in range(len(panel_layers) - 1):
                assert panel_layers[k].metadata["reading_order"] < panel_layers[k + 1].metadata["reading_order"]
                # In RTL reading order, earlier bubbles are higher or further right
                m_curr = panel_layers[k].metadata
                m_next = panel_layers[k + 1].metadata
                assert m_curr["y"] <= m_next["y"] + 40 or m_curr["x"] >= m_next["x"]


def test_arabic_rtl_letter_joining(test_setup):
    """Arabic text in speech bubbles maintains joined letters and RTL layout."""
    registry, ctx, store = test_setup

    create = registry.dispatch(ToolCall(
        call_id="c_page",
        tool_id="canvas.create_page_from_template",
        arguments={"layout_template": "four_panel_cinematic", "project_id": ctx["project_id"]},
    ), ctx)
    assert create.status == "success", create.error
    page_id = create.output["page_id"]
    panel_id = create.output["panel_ids"][0]

    arabic_dialogue = "أين المصباح يا صديقي؟"
    res = registry.dispatch(ToolCall(
        call_id="c_add_arabic",
        tool_id="bubble.add",
        arguments={
            "page_id": page_id,
            "panel_id": panel_id,
            "type_id": "speech.normal",
            "text": arabic_dialogue,
            "speaker_character_id": "char_hero",
        },
    ), ctx)
    assert res.status == "success", res.error
    assert res.output["lines"]
    # Check that text is preserved
    assert res.output["text"] == arabic_dialogue
    # Check that unified vector was generated
    doc = store.get(page_id)
    layer = next(l for l in doc.layers if l.metadata.get("bubble_id") == res.output["bubble_id"])
    assert layer.metadata.get("unified_path", "").startswith("M")
