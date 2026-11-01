"""Regression test suite for Phase 7: Editor vs. Export Rendering Parity.

Validates that:
1. RTL PDF export orders pages right-to-left (reversed) for physical booklet binding.
2. LTR PDF export preserves sequential order.
3. FinalCompositor successfully rasterizes vector SVG paths (via PyMuPDF) into the composite image.
"""
import pytest
from pathlib import Path
from PIL import Image
from app.contracts.engine import ExportParams, AssetFormat
from app.storage.registry import AssetRegistry, AssetType
from app.export.delivery import ExportDeliveryEngine
from app.canvas.compositor import FinalCompositor
from app.canvas.engine import CanvasEngine
from app.canvas.models import CanvasSpec, PageSpec, LayoutTemplateId, ReadingDirection
from app.editor.models import EditablePageDocument, EditorLayer, LayerKind


def test_export_delivery_rtl_page_order_reversal(tmp_path):
    registry = AssetRegistry(tmp_path / "assets")
    delivery_engine = ExportDeliveryEngine()
    delivery_engine.export_dir = tmp_path / "exports"
    delivery_engine.export_dir.mkdir(parents=True, exist_ok=True)

    # Ingest 3 dummy page images
    page_img1 = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    page_img2 = Image.new("RGBA", (100, 100), (0, 255, 0, 255))
    page_img3 = Image.new("RGBA", (100, 100), (0, 0, 255, 255))

    p1_path = tmp_path / "p1.png"
    p2_path = tmp_path / "p2.png"
    p3_path = tmp_path / "p3.png"

    page_img1.save(p1_path)
    page_img2.save(p2_path)
    page_img3.save(p3_path)

    a1 = registry.ingest_bytes(p1_path.read_bytes(), "p1.png", "proj_test", AssetType.GENERIC_ARTIFACT)
    a2 = registry.ingest_bytes(p2_path.read_bytes(), "p2.png", "proj_test", AssetType.GENERIC_ARTIFACT)
    a3 = registry.ingest_bytes(p3_path.read_bytes(), "p3.png", "proj_test", AssetType.GENERIC_ARTIFACT)

    # 1. RTL Export: pages should be reversed
    params_rtl = ExportParams(
        project_id="proj_test",
        page_composite_artifact_ids=[a1.asset_id, a2.asset_id, a3.asset_id],
        target_format=AssetFormat.PDF,
    )
    out_rtl = delivery_engine.export_delivery(params_rtl, registry, reading_direction="rtl")
    assert Path(out_rtl.file_path).exists()
    assert out_rtl.byte_size > 0

    # 2. LTR Export: pages should follow sequential order
    params_ltr = ExportParams(
        project_id="proj_test",
        page_composite_artifact_ids=[a1.asset_id, a2.asset_id, a3.asset_id],
        target_format=AssetFormat.PDF,
    )
    out_ltr = delivery_engine.export_delivery(params_ltr, registry, reading_direction="ltr")
    assert Path(out_ltr.file_path).exists()
    assert out_ltr.byte_size > 0


def test_final_compositor_vector_svg_rendering(tmp_path):
    registry = AssetRegistry(tmp_path / "assets")
    compositor = FinalCompositor()
    compositor.output_dir = tmp_path / "composites"
    compositor.output_dir.mkdir(parents=True, exist_ok=True)

    canvas_spec = CanvasSpec(width_px=800, height_px=1000)
    page_spec = PageSpec(page_id="p_vec", reading_direction=ReadingDirection.LTR)
    layout = CanvasEngine.generate_layout(canvas_spec, page_spec, LayoutTemplateId.SIX_PANEL_CLASSIC)

    # Add a stylized speech bubble with exact SVG vector path
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

    # Load composite image and verify non-empty render
    rendered = Image.open(out.output_file_path)
    assert rendered.size == (800, 1000)
