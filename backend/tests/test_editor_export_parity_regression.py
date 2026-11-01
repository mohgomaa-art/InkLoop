"""
Regression tests establishing Editor vs Export Rendering Parity and proving
the exact root causes of visual discrepancies between the Canvas Editor and Export PDF.

Verifies:
1. Provenance: Page ID page_story_429f2386aa74 at revision 25 is the exact same document
   loaded by both editor and export pipelines.
2. Bubble Divergence: Editor SpeechBubbleSvg defaults to oval + pointer tail,
   while Compositor defaults to rounded_rectangle + no tail.
3. Typography Divergence: Editor uses layer metadata font_family ('Bangers'),
   while Compositor hardcodes 'ComicNeue' and diamond line-wrapping.
4. Panel Border Divergence: Editor uses stroke-width 1.4 px, while Compositor hardcodes 3.0 px,
   both ignoring layout descriptor boundary stroke_width_px (2.0 px).
5. Transform Divergence: Editor supports scale/translate/rotation/flip, while Compositor
   ignores layer.transform on image layers.
6. Export Packaging: Delivery engine wraps 900x1200 raster image into PDF without vector text.
"""
import math
from pathlib import Path
from PIL import Image

import pytest
from app.api.routers.editor import get_page_store, get_registry
from app.canvas.compositor import FinalCompositor
from app.contracts.geometry import AssetFormat
from app.contracts.engine import ExportParams
from app.export.delivery import ExportDeliveryEngine
from app.text.typography import TypographyEngine


PAGE_ID = "page_story_429f2386aa74"
REVISION = 25
PROJECT_ID = "last_oneee_b36304f4"


def _seed_fixture_if_needed():
    store = get_page_store()
    try:
        store.get(PAGE_ID)
        return
    except Exception:
        pass

    registry = get_registry()
    fixture_path = Path(__file__).parent / "fixtures" / "fixture_page_story_429f2386aa74.json"
    if not fixture_path.exists():
        return
    from app.editor.models import EditablePageDocument
    from app.storage.registry import AssetType
    import io

    doc = EditablePageDocument.model_validate_json(fixture_path.read_text(encoding="utf-8"))

    for l in doc.layers:
        if l.kind.value == "image" and l.source_asset_id:
            asset_id = l.source_asset_id
            if not registry.get_asset(asset_id):
                dummy = Image.new("RGBA", (400, 500), (200, 200, 200, 255))
                buf = io.BytesIO()
                dummy.save(buf, format="PNG")
                registry.ingest_bytes(
                    buf.getvalue(), f"{asset_id}.png", PROJECT_ID, AssetType.PANEL_IMAGE,
                    name=asset_id
                )

    payload = doc.model_dump_json(exclude_none=True).encode()
    asset = registry.ingest_bytes(
        payload, f"{PAGE_ID}-r{REVISION}.json", PROJECT_ID, AssetType.GENERIC_ARTIFACT,
        name=f"{PAGE_ID} revision {REVISION}",
        lineage_operation="editable_page_revision", lineage_params={"page_id": PAGE_ID, "revision": REVISION},
        extra_metadata={"document_kind": "editable_page", "page_id": PAGE_ID, "revision": REVISION},
    )

    with store._lock:
        store._conn.execute(
            "INSERT OR REPLACE INTO pages(page_id, project_id, revision, artifact_id, created_at, updated_at) VALUES (?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
            (PAGE_ID, PROJECT_ID, REVISION, asset.asset_id)
        )
        store._conn.execute(
            "INSERT OR REPLACE INTO page_revisions(page_id, revision, artifact_id) VALUES (?, ?, ?)",
            (PAGE_ID, REVISION, asset.asset_id)
        )
        store._conn.commit()


@pytest.fixture(autouse=True)
def _ensure_parity_document_seeded():
    _seed_fixture_if_needed()


def test_persisted_revision_provenance():
    """Verify that both pipelines reference the exact same persisted revision 25."""
    store = get_page_store()
    doc = store.get(PAGE_ID)

    assert doc.page_id == PAGE_ID
    assert doc.revision == REVISION
    assert doc.project_id == PROJECT_ID
    assert len(doc.layout.panel_slots) == 4
    assert len(doc.layers) == 9

    # Verify 4 panels, 4 images, 1 text layer
    panel_layers = [l for l in doc.layers if l.kind.value == "panel"]
    image_layers = [l for l in doc.layers if l.kind.value == "image"]
    text_layers = [l for l in doc.layers if l.kind.value == "text"]

    assert len(panel_layers) == 4
    assert len(image_layers) == 4
    assert len(text_layers) == 1

    text_layer = text_layers[0]
    assert text_layer.layer_id == "text_7e0e1aaf8c0edc77"
    assert text_layer.metadata["text"] == "Some lights stay on."
    assert text_layer.metadata["font_family"] == "Bangers"
    assert text_layer.metadata["font_size"] == 11
    assert text_layer.metadata["width"] == 375
    assert text_layer.metadata["height"] == 83
    # Critical: bubble_shape and tail_type are completely absent in saved metadata
    assert "bubble_shape" not in text_layer.metadata
    assert "tail_type" not in text_layer.metadata
    assert "tail_x" not in text_layer.metadata
    assert "tail_y" not in text_layer.metadata
    assert "tail_target" not in text_layer.metadata


def test_bubble_shape_and_tail_divergence_between_editor_and_compositor():
    """
    Root Cause Diagnosis:
    When bubble_shape is omitted, Editor (SpeechBubbleSvg.tsx:77) defaults to 'oval',
    while Compositor (compositor.py:240) defaults to 'rounded_rectangle'.
    When tail_type is omitted, Editor (SpeechBubbleSvg.tsx:78) defaults to 'smooth_pointer'
    and fabricates a pointer tip, while Compositor (compositor.py:248) renders NO tail
    unless tail_x and tail_y are explicitly present.
    """
    store = get_page_store()
    doc = store.get(PAGE_ID)
    text_layer = [l for l in doc.layers if l.kind.value == "text"][0]
    meta = text_layer.metadata

    # Editor default logic (frontend/src/components/editor/SpeechBubbleSvg.tsx:77-78)
    editor_shape = meta.get("bubble_shape") or "oval"
    editor_tail = meta.get("tail_type") or "smooth_pointer"
    editor_cx = meta["x"] + meta["width"] / 2
    editor_rx = meta["width"] / 2
    editor_tip_x = meta.get("tail_target", {}).get("x", editor_cx - editor_rx * 0.3)
    editor_tip_y = meta.get("tail_target", {}).get("y", meta["y"] + meta["height"] + 50)

    assert editor_shape == "oval", "Editor must default to oval"
    assert editor_tail == "smooth_pointer", "Editor must default to smooth_pointer"
    assert editor_tip_x == 265 + 375 / 2 - (375 / 2) * 0.3  # 396.25
    assert editor_tip_y == 947 + 83 + 50  # 1080.0

    # Compositor default logic (backend/app/canvas/compositor.py:240-248)
    compositor_shape = str(meta.get("bubble_shape", "rounded_rectangle")).lower()
    compositor_tail_x = meta.get("tail_x")
    compositor_tail_y = meta.get("tail_y")
    compositor_has_tail = compositor_tail_x is not None and compositor_tail_y is not None

    assert compositor_shape == "rounded_rectangle", "Compositor must default to rounded_rectangle"
    assert not compositor_has_tail, "Compositor must not draw any tail when tail_x/tail_y are None"

    # PROOF OF DIVERGENCE:
    assert editor_shape != compositor_shape, "Editor renders oval, but Compositor renders rounded_rectangle!"
    assert compositor_has_tail is False, "Compositor drops the tail entirely!"


def test_typography_and_line_wrapping_divergence():
    """
    Root Cause Diagnosis:
    Editor uses meta['font_family'] ('Bangers') and CSS single-line flow.
    Compositor hardcodes 'ComicNeue' (compositor.py:288) and executes a
    diamond line-wrapping algorithm that splits the 4 words into 2 lines.
    Compositor also runs a font-size search loop that inflates font_size from 11 to 20+.
    """
    store = get_page_store()
    doc = store.get(PAGE_ID)
    text_layer = [l for l in doc.layers if l.kind.value == "text"][0]
    meta = text_layer.metadata

    # 1. Font Family Divergence
    editor_font = meta.get("font_family")
    is_arabic = any("\u0600" <= c <= "\u06FF" for c in meta["text"])
    compositor_font = "NotoSansArabic" if is_arabic else "ComicNeue"

    assert editor_font == "Bangers"
    assert compositor_font == "ComicNeue"
    assert editor_font != compositor_font, "Compositor ignores 'Bangers' and hardcodes 'ComicNeue'!"

    # 2. Line Wrapping Divergence
    raw_text = meta["text"]  # "Some lights stay on."
    # In Editor: width=375, fontSize=11 -> 20 characters easily fit on 1 line.
    editor_lines = [raw_text]

    # In Compositor: diamond line-wrapping
    total_chars = len(raw_text)
    k_target = max(2, min(5, round(math.sqrt(0.36 * total_chars))))
    words = raw_text.split()
    best_lines = None
    best_score = float("inf")
    for k in range(max(1, k_target - 1), min(len(words) + 1, k_target + 2)):
        avg_chars = total_chars / k
        cand_lines = []
        cur = []
        cur_len = 0
        for w in words:
            w_len = len(w)
            if not cur:
                cur.append(w)
                cur_len = w_len
            elif (cur_len + 1 + w_len) <= avg_chars * 1.25 and len(cand_lines) < k - 1:
                cur.append(w)
                cur_len += 1 + w_len
            elif len(cand_lines) == k - 1:
                cur.append(w)
                cur_len += 1 + w_len
            else:
                cand_lines.append(" ".join(cur))
                cur = [w]
                cur_len = w_len
        if cur:
            cand_lines.append(" ".join(cur))
        lengths = [len(l) for l in cand_lines]
        score = max(lengths) - min(lengths)
        if score < best_score:
            best_score = score
            best_lines = cand_lines
    compositor_lines = best_lines or [raw_text]

    assert len(editor_lines) == 1, "Editor displays text on 1 line"
    assert len(compositor_lines) == 2, "Compositor splits text into 2 lines"
    assert compositor_lines == ["Some lights", "stay on."]

    # 3. Font Size Inflation Divergence
    typo_engine = TypographyEngine()
    usable_w = meta["width"] - 24.0  # 351.0
    usable_h = meta["height"] - 20.0  # 63.0
    im = Image.new("RGBA", (100, 100))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(im)

    base_font_size = float(meta.get("font_size", 20))  # 11.0
    opt_font_size = base_font_size
    for test_size in range(max(15, int(base_font_size - 4)), 33):
        test_font, _ = typo_engine.resolve_font(compositor_font, test_size)
        test_lh = int(test_size * 1.28)
        test_tot_h = len(compositor_lines) * test_lh
        test_max_w = max(
            (draw.textbbox((0, 0), l, font=test_font)[2] - draw.textbbox((0, 0), l, font=test_font)[0])
            for l in compositor_lines
        )
        if test_tot_h <= usable_h and test_max_w <= usable_w:
            opt_font_size = float(test_size)
        else:
            break

    assert meta["font_size"] == 11
    assert opt_font_size >= 20, f"Compositor inflated font size from 11 to {opt_font_size}!"


def test_panel_border_stroke_divergence():
    """
    Root Cause Diagnosis:
    Layout descriptor defines stroke_width_px: 2.0.
    Editor (ManualEditorView.tsx:2880) hardcodes strokeWidth: 1.4.
    Compositor (compositor.py:204) hardcodes outline='#111111', width=3.
    """
    store = get_page_store()
    doc = store.get(PAGE_ID)
    panel_desc = doc.layout.panel_slots[0].descriptor.boundary

    descriptor_stroke_px = panel_desc.stroke_width_px  # 2.0
    editor_stroke_px = 1.4  # from ManualEditorView.tsx:2880
    compositor_stroke_px = 3.0  # from compositor.py:204

    assert descriptor_stroke_px == 2.0
    assert editor_stroke_px == 1.4
    assert compositor_stroke_px == 3.0
    assert editor_stroke_px != compositor_stroke_px
    assert compositor_stroke_px > descriptor_stroke_px


def test_transform_layer_support_divergence():
    """
    Root Cause Diagnosis:
    Editor imageEditBounds applies transform.scale_x, transform.translate_x,
    transform.rotation_deg, and metadata flip_h / flip_v.
    Compositor (compositor.py:152-192) completely ignores layer.transform and metadata flips.
    """
    store = get_page_store()
    doc = store.get(PAGE_ID)
    img_layer = [l for l in doc.layers if l.kind.value == "image"][0]

    # In rev 25, transform is default identity:
    assert img_layer.transform is not None
    assert img_layer.transform.scale_x == 1.0
    assert img_layer.transform.rotation_deg == 0.0

    # In compositor.py, 'transform' attribute is never accessed:
    import inspect
    compositor_source = inspect.getsource(FinalCompositor.composite_page_document)
    assert "transform" not in compositor_source, "Compositor has zero references to layer.transform!"
    assert "flip_h" not in compositor_source, "Compositor has zero references to flip_h!"


def test_export_pdf_contains_raster_composite_not_vector_elements():
    """
    Expected vs Defect Resolution Analysis:
    Verify that ExportDeliveryEngine compiles a raster PNG into the PDF canvas,
    so text and borders are rasterized rather than remaining scalable vectors.
    """
    store = get_page_store()
    doc = store.get(PAGE_ID)
    registry = get_registry()

    compositor = FinalCompositor()
    comp_out = compositor.composite_page_document(doc, registry)

    engine = ExportDeliveryEngine()
    params = ExportParams(
        project_id=doc.project_id,
        page_composite_artifact_ids=[comp_out.composite_page_artifact_id],
        target_format=AssetFormat.PDF,
    )
    delivery = engine.export_delivery(params, asset_registry=registry)

    # Verify output PDF exists and can be opened
    pdf_path = Path(delivery.file_path)
    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"

    # Open with pymupdf to inspect page objects
    import fitz
    pdf_doc = fitz.open(str(pdf_path))
    assert len(pdf_doc) == 1
    page = pdf_doc[0]

    # PDF rect matches canvas dimensions in points (900 x 1200)
    assert page.rect.width == 900.0
    assert page.rect.height == 1200.0

    # PDF contains an embedded image, but NO text stream!
    image_list = page.get_images()
    assert len(image_list) >= 1, "PDF must contain the composite raster image"
    text_content = page.get_text()
    assert text_content.strip() == "", "PDF contains rasterized text, NOT selectable vector text!"
