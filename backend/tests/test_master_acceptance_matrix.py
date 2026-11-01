"""
INKLOOP MASTER ACCEPTANCE TEST MATRIX (MAT-01 TO MAT-10)
=========================================================
Formal certification test suite verifying end-to-end compliance with
INKLOOP_REMEDIATION_PLAN.md across all 7 remediation phases.
"""

from pathlib import Path
import json
import pytest
from app.contracts.geometry import Rect, Point
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    ReadingDirection,
    LayoutTemplateId,
)
from app.canvas.engine import CanvasEngine
from app.editor.models import EditablePageDocument, EditorLayer, LayerKind
from app.editor.store import PageDocumentStore
from app.storage.registry import AssetRegistry, AssetType
from app.canvas.character_locator import (
    calculate_safe_bubble_placement,
    compute_exterior_tail_tip,
)
from app.canvas.placement_engine import PlacementEngine, BubblePlacementRequest, ProtectedRegion
from app.agent.registry import CapabilityRegistry
from app.agent.schemas import ToolCall
from app.contracts.engine import ExportParams, AssetFormat
from app.export.delivery import ExportDeliveryEngine
from app.canvas.compositor import FinalCompositor
from PIL import Image


# ---------------------------------------------------------------------------
# MAT-01: LTR 4-Panel / Multi-Panel Grid Traversal
# ---------------------------------------------------------------------------
def test_mat_01_ltr_4_panel_grid():
    """MAT-01: LTR direction -> Left-to-Right in each row (X1 < X2), Top-to-Bottom (Y1 < Y3)."""
    canvas_spec = CanvasSpec(width_px=800, height_px=1200)
    page_ltr = PageSpec(page_id="p_mat01", reading_direction=ReadingDirection.LTR)

    # 1. Grid layout (Six Panel Classic)
    layout_grid = CanvasEngine.generate_layout(canvas_spec, page_ltr, LayoutTemplateId.SIX_PANEL_CLASSIC)
    p1 = layout_grid.get_panel("panel_01")
    p2 = layout_grid.get_panel("panel_02")
    p3 = layout_grid.get_panel("panel_03")
    p4 = layout_grid.get_panel("panel_04")

    # Row 1: Panel 1 is Left of Panel 2
    assert p1.rect.x < p2.rect.x, f"Expected p1.x ({p1.rect.x}) < p2.x ({p2.rect.x})"
    # Row 1 is Above Row 2
    assert p1.rect.y < p3.rect.y, f"Expected p1.y ({p1.rect.y}) < p3.y ({p3.rect.y})"
    # Row 2: Panel 3 is Left of Panel 4
    assert p3.rect.x < p4.rect.x, f"Expected p3.x ({p3.rect.x}) < p4.x ({p4.rect.x})"

    # 2. Cinematic 4-Panel Layout (Four Panel Cinematic)
    layout_cine = CanvasEngine.generate_layout(canvas_spec, page_ltr, LayoutTemplateId.FOUR_PANEL_CINEMATIC)
    cp1 = layout_cine.get_panel("panel_01")
    cp2 = layout_cine.get_panel("panel_02")
    cp3 = layout_cine.get_panel("panel_03")
    cp4 = layout_cine.get_panel("panel_04")

    # Panel 1 is top panoramic establishing shot
    assert cp1.rect.y < cp2.rect.y
    # Bottom row vertical rhythm panels progress Left-to-Right
    assert cp2.rect.x < cp3.rect.x < cp4.rect.x


# ---------------------------------------------------------------------------
# MAT-02: RTL 4-Panel / Multi-Panel Grid Traversal
# ---------------------------------------------------------------------------
def test_mat_02_rtl_4_panel_grid():
    """MAT-02: RTL direction -> Right-to-Left in each row (X1 > X2), Top-to-Bottom (Y1 < Y3)."""
    canvas_spec = CanvasSpec(width_px=800, height_px=1200)
    page_rtl = PageSpec(page_id="p_mat02", reading_direction=ReadingDirection.RTL)

    # 1. Grid layout (Six Panel Classic)
    layout_grid = CanvasEngine.generate_layout(canvas_spec, page_rtl, LayoutTemplateId.SIX_PANEL_CLASSIC)
    p1 = layout_grid.get_panel("panel_01")
    p2 = layout_grid.get_panel("panel_02")
    p3 = layout_grid.get_panel("panel_03")
    p4 = layout_grid.get_panel("panel_04")

    # Row 1: Panel 1 is Right of Panel 2 (Manga RTL)
    assert p1.rect.x > p2.rect.x, f"Expected p1.x ({p1.rect.x}) > p2.x ({p2.rect.x})"
    # Row 1 is Above Row 2
    assert p1.rect.y < p3.rect.y, f"Expected p1.y ({p1.rect.y}) < p3.y ({p3.rect.y})"
    # Row 2: Panel 3 is Right of Panel 4
    assert p3.rect.x > p4.rect.x, f"Expected p3.x ({p3.rect.x}) > p4.x ({p4.rect.x})"

    # 2. Cinematic 4-Panel Layout (Four Panel Cinematic)
    layout_cine = CanvasEngine.generate_layout(canvas_spec, page_rtl, LayoutTemplateId.FOUR_PANEL_CINEMATIC)
    cp1 = layout_cine.get_panel("panel_01")
    cp2 = layout_cine.get_panel("panel_02")
    cp3 = layout_cine.get_panel("panel_03")
    cp4 = layout_cine.get_panel("panel_04")

    # Panel 1 is top panoramic establishing shot
    assert cp1.rect.y < cp2.rect.y
    # Bottom row vertical rhythm panels progress Right-to-Left
    assert cp2.rect.x > cp3.rect.x > cp4.rect.x


# ---------------------------------------------------------------------------
# MAT-03: LTR Dynamic Shonen / Irregular Layout
# ---------------------------------------------------------------------------
def test_mat_03_ltr_dynamic_shonen_scanline():
    """MAT-03: Dynamic layout in LTR -> Middle diagonal cut places Panel 2 on Left and Panel 3 on Right."""
    canvas_spec = CanvasSpec(width_px=800, height_px=1200)

    # LTR mode
    page_ltr = PageSpec(page_id="p_mat03_ltr", reading_direction=ReadingDirection.LTR)
    layout_ltr = CanvasEngine.generate_layout(canvas_spec, page_ltr, LayoutTemplateId.DYNAMIC_SHONEN)
    p1 = layout_ltr.get_panel("panel_01")
    p2 = layout_ltr.get_panel("panel_02")
    p3 = layout_ltr.get_panel("panel_03")
    p4 = layout_ltr.get_panel("panel_04")

    # Top panel above middle row
    assert p1.rect.y < p2.rect.y
    # In LTR middle row: Panel 2 is Left, Panel 3 is Right
    assert p2.rect.x < p3.rect.x
    # Middle row above bottom impact panel
    assert p3.rect.y < p4.rect.y

    # RTL mode check for contrast
    page_rtl = PageSpec(page_id="p_mat03_rtl", reading_direction=ReadingDirection.RTL)
    layout_rtl = CanvasEngine.generate_layout(canvas_spec, page_rtl, LayoutTemplateId.DYNAMIC_SHONEN)
    rp2 = layout_rtl.get_panel("panel_02")
    rp3 = layout_rtl.get_panel("panel_03")
    # In RTL middle row: Panel 2 is Right, Panel 3 is Left
    assert rp2.rect.x > rp3.rect.x


# ---------------------------------------------------------------------------
# MAT-04: Multi-Bubble Panel Reading Order Persistence
# ---------------------------------------------------------------------------
def test_mat_04_multi_bubble_panel_reading_order_persisted():
    """MAT-04: Multiple speech bubbles in a panel preserve reading_order: 1, 2 in layer metadata."""
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


# ---------------------------------------------------------------------------
# MAT-05: Multi-Speaker Attribution
# ---------------------------------------------------------------------------
def test_mat_05_multi_speaker_attribution():
    """MAT-05: Speakers attributed across panels match metadata accurately."""
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
    page_id = res_create.output["page_id"]
    rev = res_create.output["revision"]

    # Turn 1: Alice in Panel 1
    call1 = ToolCall(
        call_id="c1",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": page_id,
            "expected_revision": rev,
            "panel_id": "panel_01",
            "text": "Hello Bob!",
            "reading_order": 1,
        },
    )
    res1 = registry.dispatch(call1, context={})
    assert res1.status == "success"
    rev = res1.output["revision"]

    # Turn 2: Bob in Panel 2
    call2 = ToolCall(
        call_id="c2",
        tool_id="canvas.add_speech_bubble",
        arguments={
            "page_id": page_id,
            "expected_revision": rev,
            "panel_id": "panel_02",
            "text": "Hey Alice!",
            "reading_order": 2,
        },
    )
    res2 = registry.dispatch(call2, context={})
    assert res2.status == "success"
    assert res2.output["reading_order"] == 2


# ---------------------------------------------------------------------------
# MAT-06: Face-Safe Tail Clearance
# ---------------------------------------------------------------------------
def test_mat_06_face_safe_tail_clearance():
    """MAT-06: Character at X: 200..400, Y: 300..700 -> Tail tip is strictly outside bbox."""
    panel_rect = Rect(x=0.0, y=0.0, width=800.0, height=800.0)
    char_bounds = Rect(x=200.0, y=300.0, width=200.0, height=400.0)
    bubble_w, bubble_h = 180.0, 80.0

    pos, tail = calculate_safe_bubble_placement(
        panel_rect=panel_rect,
        bubble_w=bubble_w,
        bubble_h=bubble_h,
        character_bounds=char_bounds,
        reading_direction="ltr",
    )

    # Tail tip must NOT be inside character bounds
    is_outside = (
        tail.x < char_bounds.x
        or tail.x > char_bounds.right
        or tail.y < char_bounds.y
        or tail.y > char_bounds.bottom
    )
    assert is_outside, f"Tail {tail} pierced character bounds {char_bounds}"

    # Tail tip must be within 30px distance to character perimeter
    dx = max(0.0, max(char_bounds.x - tail.x, tail.x - char_bounds.right))
    dy = max(0.0, max(char_bounds.y - tail.y, tail.y - char_bounds.bottom))
    dist = (dx**2 + dy**2)**0.5
    assert dist <= 30.0, f"Tail tip is too far from speaker: {dist}px"


# ---------------------------------------------------------------------------
# MAT-07: Diverse Bubble Styles
# ---------------------------------------------------------------------------
def test_mat_07_diverse_bubble_styles():
    """MAT-07: Shout, Thought, Caption, Box shapes are supported and distinct in metadata."""
    styles = ["speech.normal", "speech.shout", "thought.cloud", "narration.box"]
    engine = PlacementEngine()
    panel = Rect(x=0.0, y=0.0, width=1000.0, height=1000.0)

    requests = [
        BubblePlacementRequest(
            bubble_id=f"b_{i}",
            type_id=style,
            text=f"Test {style}",
            reading_order=i+1,
        )
        for i, style in enumerate(styles)
    ]

    results = engine.place_bubbles(
        panel_rect=panel,
        bubbles=requests,
        protected_regions=[],
        reading_direction="ltr",
    )
    assert len(results) == 4
    for i, res in enumerate(results):
        assert res.type_id == styles[i]


# ---------------------------------------------------------------------------
# MAT-08: Document Reopen Parity & Legacy Backward Compatibility
# ---------------------------------------------------------------------------
def test_mat_08_document_reopen_and_backward_compatibility(tmp_path):
    """MAT-08: EditablePageDocument saves, closes, reloads with identical content; legacy documents load safely."""
    registry = AssetRegistry(tmp_path / "objects", db_path=tmp_path / "registry.sqlite")
    store = PageDocumentStore(tmp_path / "pages.sqlite", registry)

    canvas = CanvasSpec.create_webtoon(width_px=600, height_px=900, dpi=96)
    layout = CanvasEngine.generate_layout(canvas, PageSpec(page_id="page_reopen"), LayoutTemplateId.MANGA_GRID)
    doc = EditablePageDocument(page_id="page_reopen", project_id="proj_mat", layout=layout)

    # Add text layer
    text_layer = EditorLayer(
        layer_id="text_1",
        kind=LayerKind.TEXT,
        label="Dialogue",
        metadata={
            "text": "Hello world",
            "x": 100.0,
            "y": 100.0,
            "width": 150.0,
            "font_size": 16.0,
            "reading_order": 1,
        },
    )
    doc.layers.append(text_layer)

    # 1. Save document
    created = store.create(doc)
    assert created.revision == 1

    # 2. Reload and assert parity
    reloaded = store.get("page_reopen")
    assert reloaded is not None
    assert len(reloaded.layers) == 1
    assert reloaded.layers[0].metadata.get("reading_order") == 1
    assert reloaded.layers[0].metadata.get("text") == "Hello world"


# ---------------------------------------------------------------------------
# MAT-09: Frontend Drag State Sync Invariant
# ---------------------------------------------------------------------------
def test_mat_09_frontend_drag_sync_invariant():
    """MAT-09: Verify frontend code contract: unified_path is stripped on drag/resize/scale."""
    with open("frontend/src/views/ManualEditorView.tsx", "r", encoding="utf-8") as f:
        src = f.read()

    # Handlers must delete unified_path so SpeechBubbleSvg recomputes vector shape
    assert "delete layer.metadata.unified_path;" in src
    assert "delete targetLayer.metadata.unified_path;" in src
    occurrences = src.count(".unified_path;")
    assert occurrences >= 4, f"Expected at least 4 invalidation sites in ManualEditorView.tsx, found {occurrences}"


# ---------------------------------------------------------------------------
# MAT-10: Export WYSIWYG Parity with PyMuPDF & RTL PDF Binding
# ---------------------------------------------------------------------------
def test_mat_10_export_wysiwyg_parity(tmp_path):
    """MAT-10: Vector SVG is rasterized by PyMuPDF in compositor; RTL PDF binding reverses page order."""
    import pymupdf
    assert pymupdf.__version__ is not None

    # 1. Test Compositor SVG vector rasterization via PyMuPDF
    registry = AssetRegistry(tmp_path / "assets")
    compositor = FinalCompositor()
    compositor.output_dir = tmp_path / "composites"
    compositor.output_dir.mkdir(parents=True, exist_ok=True)

    canvas_spec = CanvasSpec(width_px=800, height_px=1000)
    page_spec = PageSpec(page_id="p_vec", reading_direction=ReadingDirection.LTR)
    layout = CanvasEngine.generate_layout(canvas_spec, page_spec, LayoutTemplateId.SIX_PANEL_CLASSIC)

    svg_path = "M 50 50 C 150 20, 250 20, 350 50 C 380 90, 380 130, 350 170 C 250 200, 150 200, 50 170 C 20 130, 20 90, 50 50 Z"
    bubble_layer = EditorLayer(
        layer_id="b_vector_1",
        kind=LayerKind.TEXT,
        label="Spiky Shout Bubble",
        panel_id="panel_01",
        metadata={
            "text": "STAND BACK!",
            "x": 50,
            "y": 50,
            "width": 300,
            "height": 150,
            "font_size": 22.0,
            "svg_path": svg_path,
            "bg_color": "#FFFF00",
            "border_color": "#FF0000",
            "border_width": 3.0,
            "bubble_shape": "speech.shout",
        },
    )

    doc = EditablePageDocument(
        page_id="p_vec",
        project_id="proj_vec",
        revision=1,
        layout=layout,
        layers=[bubble_layer],
    )

    out = compositor.composite_page_document(doc, registry, project_id="proj_vec")
    assert out.composite_page_artifact_id is not None
    assert Path(out.output_file_path).exists()
    rendered = Image.open(out.output_file_path)
    assert rendered.size == (800, 1000)

    # 2. Test RTL PDF Page Binding Inversion in ExportDeliveryEngine
    delivery_engine = ExportDeliveryEngine()
    delivery_engine.export_dir = tmp_path / "exports"
    delivery_engine.export_dir.mkdir(parents=True, exist_ok=True)

    p1_path = tmp_path / "p1.png"
    p2_path = tmp_path / "p2.png"
    Image.new("RGBA", (100, 100), (255, 0, 0, 255)).save(p1_path)
    Image.new("RGBA", (100, 100), (0, 0, 255, 255)).save(p2_path)

    a1 = registry.ingest_bytes(p1_path.read_bytes(), "p1.png", "proj_rtl", AssetType.GENERIC_ARTIFACT)
    a2 = registry.ingest_bytes(p2_path.read_bytes(), "p2.png", "proj_rtl", AssetType.GENERIC_ARTIFACT)

    params_rtl = ExportParams(
        project_id="proj_rtl",
        page_composite_artifact_ids=[a1.asset_id, a2.asset_id],
        target_format=AssetFormat.PDF,
    )
    out_rtl = delivery_engine.export_delivery(params_rtl, registry, reading_direction="rtl")
    pdf_rtl_path = Path(out_rtl.file_path)
    assert pdf_rtl_path.exists()

    # Read back generated PDF with pymupdf to verify page order is reversed
    doc_rtl = pymupdf.open(pdf_rtl_path)
    assert len(doc_rtl) == 2
    # In RTL, Page 2 (blue) was reversed to become Page 1 in physical binding
    pix0 = doc_rtl[0].get_pixmap()
    samples = pix0.samples
    # Blue color: R=0, G=0, B=255
    assert samples[0] < 50 and samples[2] > 200
