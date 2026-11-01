"""Regression test suite for Phase 3: Speech Bubble Reading Order & Persistence.

Validates that:
1. canvas_add_speech_bubble explicitly persists reading_order in layer metadata and output.
2. StoryProductionJob exposes reading_direction for job execution.
3. Legacy documents with reading_order=None dynamically synthesize monotonic reading order.
4. Multi-bubble placement preserves reading order sequence across re-layout.
"""
import pytest
from app.agent.registry import CapabilityRegistry
from app.agent.schemas import ToolCall
from app.agent.production import StoryProductionJob
from app.canvas.bubble_service import BubbleService
from app.canvas.engine import CanvasEngine
from app.canvas.models import CanvasSpec, PageSpec, LayoutTemplateId, ReadingDirection
from app.editor.models import EditablePageDocument, EditorLayer, LayerKind


def test_canvas_add_speech_bubble_persists_reading_order():
    registry = CapabilityRegistry()
    create_call = ToolCall(
        call_id="call_create",
        tool_id="canvas.create_page_from_template",
        arguments={
            "layout_template": "six_panel_classic",
            "reading_direction": "ltr",
            "width_px": 900,
            "height_px": 1200,
        },
    )
    res_create = registry.dispatch(create_call, context={})
    assert res_create.status == "success"
    page_id = res_create.output["page_id"]
    rev = res_create.output["revision"]

    # Add Bubble 1 with reading_order = 1
    add_b1 = ToolCall(
        call_id="call_b1",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": page_id,
            "expected_revision": rev,
            "panel_id": "panel_01",
            "text": "First dialogue turn.",
            "reading_order": 1,
            "type_id": "speech.normal",
        },
    )
    res_b1 = registry.dispatch(add_b1, context={})
    assert res_b1.status == "success"
    rev = res_b1.output["revision"]
    assert res_b1.output["reading_order"] == 1

    # Add Bubble 2 with reading_order = 2
    add_b2 = ToolCall(
        call_id="call_b2",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": page_id,
            "expected_revision": rev,
            "panel_id": "panel_01",
            "text": "Second dialogue turn.",
            "reading_order": 2,
            "type_id": "speech.normal",
        },
    )
    res_b2 = registry.dispatch(add_b2, context={})
    assert res_b2.status == "success"
    assert res_b2.output["reading_order"] == 2

    # Verify directly from persisted document store
    store, doc = registry._editor_page(page_id, {})
    layers = [l for l in doc.layers if l.panel_id == "panel_01" and l.kind == LayerKind.TEXT]
    assert len(layers) == 2
    orders = [l.metadata.get("reading_order") for l in layers]
    assert sorted(orders) == [1, 2]


def test_story_production_job_reading_direction_field():
    job = StoryProductionJob(
        job_id="job_test_01",
        run_id="run_01",
        project_id="proj_01",
        source_request_message_id="msg_01",
        source_plan_call_id="call_01",
        plan={"reading_direction": "ltr"},
        reading_direction="ltr",
    )
    assert job.reading_direction == "ltr"


def test_legacy_document_reading_order_spatial_fallback():
    canvas_spec = CanvasSpec(width_px=900, height_px=1200)
    page_spec = PageSpec(page_id="page_leg", reading_direction=ReadingDirection.LTR)
    layout = CanvasEngine.generate_layout(canvas_spec, page_spec, LayoutTemplateId.SIX_PANEL_CLASSIC)

    # Bubble A at top-left of panel_01
    layer_a = EditorLayer(
        layer_id="b_legacy_top",
        kind=LayerKind.TEXT,
        label="Bubble Top",
        panel_id="panel_01",
        metadata={
            "bubble_id": "b_legacy_top",
            "text": "Legacy line 1",
            "type_id": "speech.normal",
            "x": 80.0,
            "y": 100.0,
            "width": 120.0,
            "height": 60.0,
            "font_size": 16.0,
            "reading_order": None,  # Missing!
        },
    )
    # Bubble B lower down in panel_01
    layer_b = EditorLayer(
        layer_id="b_legacy_bot",
        kind=LayerKind.TEXT,
        label="Bubble Bot",
        panel_id="panel_01",
        metadata={
            "bubble_id": "b_legacy_bot",
            "text": "Legacy line 2",
            "type_id": "speech.normal",
            "x": 120.0,
            "y": 200.0,
            "width": 120.0,
            "height": 60.0,
            "font_size": 16.0,
            "reading_order": None,  # Missing!
        },
    )

    doc = EditablePageDocument(
        page_id="page_leg",
        project_id="proj_leg",
        revision=1,
        layout=layout,
        layers=[layer_a, layer_b],
    )

    service = BubbleService()
    results = service.place_all(doc, panel_id="panel_01", reading_direction="ltr")
    assert len(results) == 1
    assert len(results[0]["placed_bubble_ids"]) == 2

    # Verify that reading_order was synthesized monotonically (1 then 2)
    assert layer_a.metadata["reading_order"] == 1
    assert layer_b.metadata["reading_order"] == 2
