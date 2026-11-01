import pytest
from types import SimpleNamespace
from app.agent.registry import CapabilityRegistry, ToolError
from app.agent.story_to_canvas import StoryToCanvasWorkflow
from app.agent.schemas import ToolCall
from app.editor.models import LayerKind
from app.editor.store import PageDocumentStore
from app.storage.registry import AssetRegistry
from app.canvas.models import CanvasSpec, PageSpec, LayoutTemplateId
from app.canvas.engine import CanvasEngine
from app.editor.models import EditablePageDocument


@pytest.fixture
def test_setup(tmp_path):
    registry = CapabilityRegistry.get_instance()
    asset_reg = AssetRegistry(tmp_path / "assets.db", tmp_path / "artifacts")
    doc_store = PageDocumentStore(tmp_path / "pages.db", asset_reg)
    
    # Create test canvas page
    canvas = CanvasSpec.create_a4(dpi=96.0)
    layout = CanvasEngine.generate_layout(canvas, PageSpec(page_id="page_test_routing"), LayoutTemplateId.SIX_PANEL_CLASSIC)
    doc = EditablePageDocument(page_id="page_test_routing", project_id="proj_test", layout=layout)
    doc_store.create(doc)

    # Monkey-patch _editor_page on registry to use doc_store
    def mock_editor_page(page_id, ctx):
        d = doc_store.get(page_id)
        return doc_store, d

    def mock_save_editor_page(store, document, expected_revision):
        return store.save(document.page_id, expected_revision, document)

    orig_editor_page = registry._editor_page
    orig_save_editor_page = registry._save_editor_page

    registry._editor_page = mock_editor_page
    registry._save_editor_page = mock_save_editor_page

    yield registry, doc_store, doc

    registry._editor_page = orig_editor_page
    registry._save_editor_page = orig_save_editor_page


def test_canvas_add_speech_bubble_rejects_caption(test_setup):
    """canvas.add_speech_bubble rejects carrier='caption' or narration type_id."""
    registry, doc_store, doc = test_setup
    ctx = {"project_id": "proj_test"}

    # 1. Reject via schema validation when carrier is 'caption'
    call = ToolCall(
        call_id="call_test_caption",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": "page_test_routing",
            "expected_revision": doc.revision,
            "panel_id": doc.layout.panel_slots[0].panel_id,
            "text": "The GPS found a house that isn't there.",
            "carrier": "caption",
        },
    )
    res = registry.dispatch(call, ctx)
    assert res.status == "failed"
    assert res.error_code == "ERR_SCHEMA_VALIDATION_FAILED"
    assert "'caption' is not one of ['speech_bubble', 'thought_bubble']" in res.error

    # 2. Reject via schema validation if type_id is narration.box
    call_narration = ToolCall(
        call_id="call_test_narration",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": "page_test_routing",
            "expected_revision": doc.revision,
            "panel_id": doc.layout.panel_slots[0].panel_id,
            "text": "The GPS found a house that isn't there.",
            "type_id": "narration.box",
            "carrier": "speech_bubble",
        },
    )
    res_narration = registry.dispatch(call_narration, ctx)
    assert res_narration.status == "failed"
    assert res_narration.error_code == "ERR_SCHEMA_VALIDATION_FAILED"
    assert "'narration.box' is not one of" in res_narration.error


def test_editor_add_text_layer_places_caption_box(test_setup):
    """editor.add_text_layer places a rounded rectangle caption box with tail_type='none'."""
    registry, doc_store, doc = test_setup
    ctx = {"project_id": "proj_test"}
    panel_id = doc.layout.panel_slots[0].panel_id

    call = ToolCall(
        call_id="call_test_editor_text",
        tool_id="editor.add_text_layer",
        arguments={
            "page_id": "page_test_routing",
            "expected_revision": doc.revision,
            "panel_id": panel_id,
            "text": "The GPS found a house that isn't there.",
            "type_id": "narration.box",
            "reading_order": 1,
            "font_family": "Comic Neue",
            "font_size": 18,
            "align": "left",
        },
    )
    res = registry.dispatch(call, ctx)
    assert res.status == "success"
    assert res.output.get("revision") == doc.revision + 1

    # Verify persisted layer metadata
    updated_doc = doc_store.get("page_test_routing")
    text_layer = next((l for l in updated_doc.layers if l.kind == LayerKind.TEXT and l.panel_id == panel_id), None)
    assert text_layer is not None
    assert text_layer.metadata["text"] == "The GPS found a house that isn't there."
    assert text_layer.metadata["type_id"] == "narration.box"
    assert text_layer.metadata["tail_type"] == "none"
    assert text_layer.metadata["bubble_shape"] == "rounded_rectangle"
    assert text_layer.metadata["carrier"] == "caption"
    assert text_layer.metadata["reading_order"] == 1


def test_story_to_canvas_workflow_routes_five_panel_narration():
    """Verify that a 5-panel narration story routes exclusively to editor.add_text_layer with no schema errors."""
    workflow = object.__new__(StoryToCanvasWorkflow)
    dispatched_calls = []

    def mock_dispatch(call, ctx=None):
        dispatched_calls.append(call)
        return SimpleNamespace(status="success", output={"layer_id": f"layer_{call.arguments.get('panel_id')}", "revision": call.arguments.get("expected_revision", 1) + 1}, error=None)

    workflow._dispatch = mock_dispatch
    workflow._saved_character_anchor = lambda doc, pid, cid: None
    workflow._checkpoint = lambda job, stage: None

    mock_doc = SimpleNamespace(
        revision=1,
        layers=[],
        layout=SimpleNamespace(get_panel=lambda pid: SimpleNamespace(rect=SimpleNamespace(x=0, y=0, width=400, height=300))),
    )
    workflow._page_document = lambda pid: mock_doc

    panels = {
        f"page_01_panel_{i:02d}": SimpleNamespace(
            panel_id=f"page_01_panel_{i:02d}",
            page_number=1,
            character_ids=["char_mvx35t33"],
            status="pending",
            error=None,
            text_layer_ids=[],
        )
        for i in range(1, 6)
    }
    page = SimpleNamespace(page_number=1, page_id="page_story_test", revision=1, verification={})
    job = SimpleNamespace(
        job_id="job_test_narration",
        pages=[page],
        panels=panels,
        errors=[],
        assumptions=[],
    )

    narrations = [
        "The GPS found a house that isn't there.",
        "Every photo knew him.",
        "My own voice called my name.",
        "Every night, every age, I arrived.",
        "She was behind me. She wasn't.",
    ]
    plans = {
        f"page_01_panel_{i:02d}": {
            "panel_id": f"page_01_panel_{i:02d}",
            "script_lines": [
                {
                    "line_id": f"page_01_beat_{i:02d}_line_1",
                    "type_id": "narration.box",
                    "speaker_character_id": None,
                    "text": narrations[i - 1],
                    "reading_order": 1,
                    "kind": "narration",
                    "carrier": "caption",
                }
            ],
        }
        for i in range(1, 6)
    }

    workflow._place_text(job, plans)

    # All 5 calls must be editor.add_text_layer, zero canvas.add_speech_bubble
    assert len(dispatched_calls) == 5
    for idx, call in enumerate(dispatched_calls, start=1):
        assert call.tool_id == "editor.add_text_layer"
        assert call.arguments["text"] == narrations[idx - 1]
        assert call.arguments["type_id"] == "narration.box"
        assert call.arguments["reading_order"] == 1
        assert "carrier" not in call.arguments
        assert "bubble_shape" not in call.arguments

    # Zero errors recorded
    assert job.errors == []
    for p in panels.values():
        assert p.status != "needs_attention"


def test_story_to_canvas_workflow_mixed_content_routing():
    """Verify semantic distinction: spoken dialogue -> speech_bubble, thought -> thought_bubble, narration -> caption."""
    workflow = object.__new__(StoryToCanvasWorkflow)
    dispatched_calls = []

    def mock_dispatch(call, ctx=None):
        dispatched_calls.append(call)
        return SimpleNamespace(status="success", output={"layer_id": f"layer_{call.arguments.get('panel_id')}", "revision": call.arguments.get("expected_revision", 1) + 1}, error=None)

    workflow._dispatch = mock_dispatch
    workflow._saved_character_anchor = lambda doc, pid, cid: {"x": 100, "y": 100}
    workflow._checkpoint = lambda job, stage: None

    mock_doc = SimpleNamespace(
        revision=1,
        layers=[],
        layout=SimpleNamespace(get_panel=lambda pid: SimpleNamespace(rect=SimpleNamespace(x=0, y=0, width=400, height=300))),
    )
    workflow._page_document = lambda pid: mock_doc

    panels = {
        "p_dialogue": SimpleNamespace(panel_id="p_dialogue", page_number=1, character_ids=["char_hero"], status="pending", error=None, text_layer_ids=[]),
        "p_thought": SimpleNamespace(panel_id="p_thought", page_number=1, character_ids=["char_hero"], status="pending", error=None, text_layer_ids=[]),
        "p_narration": SimpleNamespace(panel_id="p_narration", page_number=1, character_ids=["char_hero"], status="pending", error=None, text_layer_ids=[]),
        "p_silent": SimpleNamespace(panel_id="p_silent", page_number=1, character_ids=["char_hero"], status="pending", error=None, text_layer_ids=[]),
    }
    page = SimpleNamespace(page_number=1, page_id="page_story_mixed", revision=1, verification={})
    job = SimpleNamespace(
        job_id="job_mixed",
        pages=[page],
        panels=panels,
        errors=[],
        assumptions=[],
    )

    plans = {
        "p_dialogue": {
            "panel_id": "p_dialogue",
            "script_lines": [{
                "text": "Who is in this house?",
                "carrier": "speech_bubble",
                "kind": "spoken_dialogue",
                "speaker_character_id": "char_hero",
            }],
        },
        "p_thought": {
            "panel_id": "p_thought",
            "script_lines": [{
                "text": "This voice sounds like me.",
                "carrier": "thought_bubble",
                "kind": "internal_thought",
                "speaker_character_id": "char_hero",
            }],
        },
        "p_narration": {
            "panel_id": "p_narration",
            "script_lines": [{
                "text": "The rain beat against the wooden walls.",
                "carrier": "caption",
                "kind": "narration",
                "type_id": "narration.box",
            }],
        },
        "p_silent": {
            "panel_id": "p_silent",
            "script_lines": [],
        },
    }

    workflow._place_text(job, plans)

    assert len(dispatched_calls) == 3

    # 1. Dialogue
    c_diag = next(c for c in dispatched_calls if c.arguments["panel_id"] == "p_dialogue")
    assert c_diag.tool_id == "canvas.add_speech_bubble"
    assert c_diag.arguments["carrier"] == "speech_bubble"
    assert c_diag.arguments["speaker_character_id"] == "char_hero"

    # 2. Thought
    c_thought = next(c for c in dispatched_calls if c.arguments["panel_id"] == "p_thought")
    assert c_thought.tool_id == "canvas.add_speech_bubble"
    assert c_thought.arguments["carrier"] == "thought_bubble"
    assert c_thought.arguments["speaker_character_id"] == "char_hero"

    # 3. Narration
    c_narr = next(c for c in dispatched_calls if c.arguments["panel_id"] == "p_narration")
    assert c_narr.tool_id == "editor.add_text_layer"
    assert c_narr.arguments["type_id"] == "narration.box"
    assert "speaker_character_id" not in c_narr.arguments
    assert "carrier" not in c_narr.arguments
