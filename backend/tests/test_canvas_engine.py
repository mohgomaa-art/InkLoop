"""
InkLoop Canvas Generation Engine (E2) - Focused Test Suite.
Verifies domain models, geometry contracts, deterministic templates, spatial invariants,
polygon calculations, structural previews (SVG & Raster), error handling, and API routes.
"""
import pytest
from typing import List

from app.contracts.geometry import (
    Rect,
    Point,
    Size,
    rect_contains,
    rect_intersects,
    snap_to_pixel_grid,
)
from app.contracts.engine import CanvasGenerationParams, CanvasGenerationOutput
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    PanelSlot,
    GutterSpec,
    MarginSpec,
    BleedSpec,
    SafeAreaSpec,
    PageFormat,
    PageType,
    ReadingDirection,
    LayoutTemplateId,
    CanvasLayoutResult,
)
from app.canvas.errors import (
    CanvasError,
    InvalidDimensionError,
    OutOfBoundsLayoutError,
    UnintendedOverlapError,
    ImpossibleLayoutError,
    TemplateNotFoundError,
    AllocationLimitExceededError,
)
from app.canvas.geometry_utils import (
    shoelace_area,
    polygon_is_self_intersecting,
    polygons_intersect,
    polygon_bounding_box,
    snap_polygon_to_grid,
    polygon_is_within_rect,
)
from app.canvas.spacing import inspect_panel_spacing
from app.canvas.templates import get_template, list_templates
from app.canvas.engine import CanvasEngine
from app.canvas.previews.svg import SVGPreviewGenerator, SVGPreviewConfig
from app.canvas.previews.raster import RasterPreviewGenerator, RasterPreviewConfig

# ==============================================================================
# 1. Model Validation and Factory Tests
# ==============================================================================

def test_canvas_spec_defaults_and_factories():
    """Verifies that CanvasSpec standard preset constructors generate accurate dimensions and DPI."""
    # A4 standard
    a4 = CanvasSpec.create_a4(dpi=300.0)
    assert a4.page_format == PageFormat.A4
    assert a4.width_px == 2480.0
    assert a4.height_px == 3508.0
    assert a4.dpi == 300.0

    # B5 manga standard
    b5 = CanvasSpec.create_b5(dpi=300.0)
    assert b5.page_format == PageFormat.B5
    assert b5.width_px == 2150.0
    assert b5.height_px == 3035.0

    # US Comic standard
    us = CanvasSpec.create_us_comic(dpi=300.0)
    assert us.page_format == PageFormat.US_COMIC
    assert us.width_px == 1988.0
    assert us.height_px == 3056.0

    # Webtoon format
    webtoon = CanvasSpec.create_webtoon(width_px=800.0, height_px=5000.0)
    assert webtoon.page_format == PageFormat.WEBTOON_VERTICAL
    assert webtoon.width_px == 800.0
    assert webtoon.height_px == 5000.0

def test_canvas_spec_rejects_negative_or_zero_dimensions():
    """Verifies that zero or negative canvas dimensions are rejected."""
    with pytest.raises(Exception):
        CanvasSpec(width_px=0.0, height_px=3000.0)

    with pytest.raises(Exception):
        CanvasSpec(width_px=-100.0, height_px=3000.0)

    with pytest.raises(Exception):
        CanvasSpec(width_px=1000.0, height_px=-50.0)

def test_canvas_spec_allocation_safety_limits():
    """Verifies that pathological canvas sizes exceeding memory limits raise AllocationLimitExceededError."""
    # Exceeding width limit (20,000 px)
    with pytest.raises(AllocationLimitExceededError):
        CanvasSpec(width_px=25000.0, height_px=1000.0)

    # Exceeding total pixel limit (100,000,000 px)
    with pytest.raises(AllocationLimitExceededError):
        CanvasSpec(width_px=15000.0, height_px=15000.0)

def test_canvas_spec_rejects_impossible_margins_and_safe_area():
    """Verifies that margins or safe areas larger than canvas dimensions raise ImpossibleLayoutError."""
    # Horizontal margins exceeding width
    with pytest.raises(ImpossibleLayoutError):
        CanvasSpec(
            width_px=1000.0,
            height_px=1500.0,
            margins=MarginSpec(left=600.0, right=500.0, top=50.0, bottom=50.0)
        )

    # Vertical safe area insets exceeding height
    with pytest.raises(ImpossibleLayoutError):
        CanvasSpec(
            width_px=1000.0,
            height_px=1500.0,
            safe_area=SafeAreaSpec(left=50.0, right=50.0, top=800.0, bottom=800.0)
        )

# ==============================================================================
# 2. Polygon Geometry Utilities Tests
# ==============================================================================

def test_shoelace_area_and_bounding_box():
    """Verifies shoelace formula area calculation and minimal bounding box calculation."""
    # Simple right triangle: (0,0), (100, 0), (0, 50) -> Area = 100 * 50 / 2 = 2500
    tri = [Point(x=0.0, y=0.0), Point(x=100.0, y=0.0), Point(x=0.0, y=50.0)]
    assert shoelace_area(tri) == 2500.0

    bbox = polygon_bounding_box(tri)
    assert bbox.x == 0.0
    assert bbox.y == 0.0
    assert bbox.width == 100.0
    assert bbox.height == 50.0

def test_polygon_self_intersection_detection():
    """Verifies that self-intersecting 'figure-8' polygons are correctly detected."""
    # Valid convex rectangle
    rect_pts = [Point(x=0.0, y=0.0), Point(x=100.0, y=0.0), Point(x=100.0, y=100.0), Point(x=0.0, y=100.0)]
    assert not polygon_is_self_intersecting(rect_pts)

    # Self-intersecting figure-8 bowtie: (0,0) -> (100, 100) -> (100, 0) -> (0, 100)
    bowtie = [Point(x=0.0, y=0.0), Point(x=100.0, y=100.0), Point(x=100.0, y=0.0), Point(x=0.0, y=100.0)]
    assert polygon_is_self_intersecting(bowtie)

def test_polygons_intersect_detection():
    """Verifies overlap detection between polygonal panels."""
    poly_a = [Point(x=0.0, y=0.0), Point(x=100.0, y=0.0), Point(x=100.0, y=100.0), Point(x=0.0, y=100.0)]
    # Overlapping poly
    poly_b = [Point(x=50.0, y=50.0), Point(x=150.0, y=50.0), Point(x=150.0, y=150.0), Point(x=50.0, y=150.0)]
    assert polygons_intersect(poly_a, poly_b)

    # Disjoint poly
    poly_c = [Point(x=200.0, y=200.0), Point(x=300.0, y=200.0), Point(x=300.0, y=300.0), Point(x=200.0, y=300.0)]
    assert not polygons_intersect(poly_a, poly_c)

# ==============================================================================
# 3. Layout Template A: Manga/Manhwa Grid
# ==============================================================================

def test_manga_grid_layout_generation():
    """Verifies regular 2x3 manga grid generation with RTL reading order and containment."""
    cs = CanvasSpec.create_a4()
    ps = PageSpec(page_id="page_grid_01", reading_direction=ReadingDirection.RTL)

    result = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.MANGA_GRID, rows=2, cols=3)

    assert result.panel_count == 6
    assert result.template_id == LayoutTemplateId.MANGA_GRID
    assert result.reading_direction == ReadingDirection.RTL

    # In RTL, panel 1 should be top-right column
    p1 = result.get_panel(result.reading_order_panel_ids[0])
    p2 = result.get_panel(result.reading_order_panel_ids[1])
    assert p1.rect.left > p2.rect.left
    assert p1.rect.top == p2.rect.top

    # Check that all panels are contained within usable area
    for p in result.panel_slots:
        assert rect_contains(result.usable_box, p.rect)

    # Check pairwise non-overlapping
    for i in range(len(result.panel_slots)):
        for j in range(i + 1, len(result.panel_slots)):
            assert not rect_intersects(result.panel_slots[i].rect, result.panel_slots[j].rect)

def test_manga_grid_proportional_ratios():
    """Verifies grid layout with non-uniform custom row and column ratios."""
    cs = CanvasSpec.create_a4()
    ps = PageSpec(page_id="page_prop_01", reading_direction=ReadingDirection.LTR)

    # Row 1 is twice as tall as Row 2 (2:1 ratio); Col 2 is twice as wide as Col 1 (1:2 ratio)
    result = CanvasEngine.generate_layout(
        cs, ps, LayoutTemplateId.MANGA_GRID,
        rows=2, cols=2,
        row_ratios=[2.0, 1.0],
        col_ratios=[1.0, 2.0]
    )

    p_top_left = result.panel_slots[0]
    p_top_right = result.panel_slots[1]
    p_bot_left = result.panel_slots[2]

    # Row height ratio check (~2x)
    assert p_top_left.height > p_bot_left.height * 1.95
    # Col width ratio check (~2x)
    assert p_top_right.width > p_top_left.width * 1.95

# ==============================================================================
# 4. Layout Template B: Six-Panel Classic
# ==============================================================================

def test_six_panel_classic_template():
    """Verifies classic 6-panel layout proportions, reading order, and geometry."""
    cs = CanvasSpec.create_a4()
    ps = PageSpec(page_id="page_six_01", reading_direction=ReadingDirection.RTL)

    result = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.SIX_PANEL_CLASSIC)

    assert result.panel_count == 6
    assert result.reading_order_panel_ids == ["panel_01", "panel_02", "panel_03", "panel_04", "panel_05", "panel_06"]

    # Verify dramatic row height proportions (Middle action row > Top establishing row)
    p_top = result.get_panel("panel_01")
    p_mid = result.get_panel("panel_03")
    p_bot = result.get_panel("panel_05")

    assert p_mid.height > p_top.height
    assert p_bot.height > p_top.height

    # Verify containment in trim box
    for p in result.panel_slots:
        assert rect_contains(result.trim_box, p.rect)

# ==============================================================================
# 5. Layout Template C: Four-Koma (Yonkoma)
# ==============================================================================

def test_four_koma_vertical_strip():
    """Verifies 4-panel vertical strip layout with Ki-Sho-Ten-Ketsu IDs and vertical stacking."""
    cs = CanvasSpec.create_b5()
    ps = PageSpec(page_id="page_4koma_01")

    result = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.FOUR_KOMA)

    assert result.panel_count == 4
    expected_ids = ["panel_01_ki", "panel_02_sho", "panel_03_ten", "panel_04_ketsu"]
    assert result.reading_order_panel_ids == expected_ids

    # Each panel should span the entire usable width
    for p in result.panel_slots:
        assert p.rect.width == pytest.approx(result.usable_box.width, abs=1.0)

    # Strictly monotonic vertical descent
    for i in range(3):
        cur_p = result.panel_slots[i]
        next_p = result.panel_slots[i + 1]
        assert cur_p.rect.bottom < next_p.rect.top
        # Spacing should match vertical gutter exactly
        assert (next_p.rect.top - cur_p.rect.bottom) == pytest.approx(cs.gutters.vertical, abs=1.0)

# ==============================================================================
# 6. Layout Template D: Dynamic Shonen with Polygonal Cuts
# ==============================================================================

def test_dynamic_shonen_polygonal_panels_and_seed_reproducibility():
    """Verifies dynamic action layout with diagonal polygonal cuts, positive areas, and seed determinism."""
    cs = CanvasSpec.create_a4()
    ps = PageSpec(page_id="page_shonen_01", reading_direction=ReadingDirection.RTL)

    res_seed_42_a = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.DYNAMIC_SHONEN, seed=42)
    res_seed_42_b = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.DYNAMIC_SHONEN, seed=42)
    res_seed_99 = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.DYNAMIC_SHONEN, seed=99)

    # Determinism: identical seed produces identical geometry
    assert len(res_seed_42_a.panel_slots) == 4
    for i in range(4):
        p_a = res_seed_42_a.panel_slots[i]
        p_b = res_seed_42_b.panel_slots[i]
        assert p_a.rect.x == p_b.rect.x
        assert p_a.rect.y == p_b.rect.y
        assert p_a.rect.width == p_b.rect.width
        assert p_a.rect.height == p_b.rect.height
        if p_a.has_polygon:
            assert len(p_a.polygon) == len(p_b.polygon)
            for pt_a, pt_b in zip(p_a.polygon, p_b.polygon):
                assert pt_a.x == pt_b.x
                assert pt_a.y == pt_b.y

    # Different seed produces distinct dynamic cut coordinates
    p_cut_42 = res_seed_42_a.panel_slots[1]
    p_cut_99 = res_seed_99.panel_slots[1]
    assert p_cut_42.rect.x != p_cut_99.rect.x or p_cut_42.polygon[1].x != p_cut_99.polygon[1].x

    # Verify polygon integrity: positive area and non-self-intersecting
    for p in res_seed_42_a.panel_slots:
        if p.has_polygon:
            assert shoelace_area(p.polygon) > 1000.0
            assert not polygon_is_self_intersecting(p.polygon)

# ==============================================================================
# 7. Layout Template E: Vertical Webtoon
# ==============================================================================

def test_webtoon_vertical_continuous_scroll():
    """Verifies vertical webtoon layout with derived canvas height and pacing gaps."""
    cs = CanvasSpec.create_webtoon(width_px=800.0, height_px=1000.0)
    ps = PageSpec(page_id="page_webtoon_01")

    panel_heights = [500.0, 700.0, 450.0, 600.0]
    vertical_gaps = [80.0, 120.0, 80.0]

    result = CanvasEngine.generate_layout(
        cs, ps, LayoutTemplateId.WEBTOON_VERTICAL,
        panel_count=4,
        panel_heights=panel_heights,
        vertical_gaps=vertical_gaps,
        derive_canvas_height=True
    )

    assert result.panel_count == 4
    # Expected height = margin.top (80) + sum(heights) (2250) + sum(gaps) (280) + margin.bottom (80) = 2690 px
    expected_h = 80.0 + 2250.0 + 280.0 + 80.0
    assert result.canvas_spec.height_px == expected_h

    # Verify gaps between panels
    for i in range(3):
        cur_p = result.panel_slots[i]
        next_p = result.panel_slots[i + 1]
        gap = next_p.rect.top - cur_p.rect.bottom
        assert gap == pytest.approx(vertical_gaps[i], abs=1.0)

# ==============================================================================
# 8. Deterministic SVG Structural Preview Tests
# ==============================================================================

def test_svg_preview_generation_and_byte_stability():
    """Verifies that SVG preview produces valid, secure XML and is byte-stable across repeated calls."""
    cs = CanvasSpec.create_a4()
    ps = PageSpec(page_id="page_svg_test")

    result = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.MANGA_GRID, rows=2, cols=2)

    svg_1 = CanvasEngine.generate_svg_preview(result)
    svg_2 = CanvasEngine.generate_svg_preview(result)

    # Byte-level determinism
    assert svg_1 == svg_2
    assert "<svg" in svg_1
    assert "</svg>" in svg_1
    assert "viewBox=" in svg_1
    assert 'data-canvas-id="' in svg_1
    assert "panel_01_01" in svg_1

def test_svg_preview_injection_hygiene():
    """Verifies that malicious or user-crafted panel IDs or canvas IDs do not inject executable scripts."""
    cs = CanvasSpec.create_a4()
    ps = PageSpec(page_id="<script>alert('xss')</script>")

    result = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.FOUR_KOMA)
    result.canvas_id = 'canvas"><script>alert(1)</script>'

    svg = CanvasEngine.generate_svg_preview(result)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg or "canvas&quot;&gt;" in svg

# ==============================================================================
# 9. Raster Structural Preview Tests
# ==============================================================================

def test_raster_preview_generation():
    """Verifies that raster preview renders a valid PNG buffer matching dimensions."""
    cs = CanvasSpec.create_b5()
    ps = PageSpec(page_id="page_raster_test")

    result = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.SIX_PANEL_CLASSIC)

    # Render at 0.25 scale for speed
    config = RasterPreviewConfig(scale=0.25)
    png_bytes = CanvasEngine.generate_raster_preview(result, config)

    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 1000
    assert png_bytes[:4] == b"\x89PNG"

def test_raster_preview_allocation_limit_guard():
    """Verifies that attempting raster render on gigantic dimensions raises AllocationLimitExceededError."""
    # Create valid canvas spec but artificially set enormous dimensions for raster
    cs = CanvasSpec(width_px=15000.0, height_px=5000.0)
    ps = PageSpec(page_id="page_huge")
    result = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.FOUR_KOMA)

    # Trying to render at scale 2.0 (30,000 px width) must raise
    with pytest.raises(AllocationLimitExceededError):
        RasterPreviewGenerator.render_png_bytes(result, RasterPreviewConfig(scale=2.0))

# ==============================================================================
# 10. Boundary Conditions and Error Diagnostics
# ==============================================================================

def test_impossible_gutters_raise_actionable_error():
    """Verifies that gutters exceeding usable dimensions raise ImpossibleLayoutError with details."""
    cs = CanvasSpec(
        width_px=1000.0,
        height_px=1000.0,
        margins=MarginSpec.uniform(50.0),
        gutters=GutterSpec(horizontal=500.0, vertical=500.0)
    )
    ps = PageSpec(page_id="page_err")

    with pytest.raises(ImpossibleLayoutError) as exc_info:
        CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.MANGA_GRID, rows=3, cols=3)

    assert "gutters" in str(exc_info.value).lower()

def test_unknown_template_raises_template_not_found():
    """Verifies that requesting an unregistered template raises TemplateNotFoundError."""
    cs = CanvasSpec.create_a4()
    ps = PageSpec(page_id="page_unknown")

    with pytest.raises(TemplateNotFoundError) as exc_info:
        CanvasEngine.generate_layout(cs, ps, template_id="nonexistent_template_xyz")

    assert "nonexistent_template_xyz" in str(exc_info.value)

def test_engine_run_params_adapter():
    """Verifies that CanvasEngine.generate_from_params translates shared contract params losslessly."""
    params = CanvasGenerationParams(
        page_format="A4",
        width_px=2480.0,
        height_px=3508.0,
        dpi=300.0,
        layout_template="6_panel",
        reading_direction="rtl"
    )

    output: CanvasGenerationOutput = CanvasEngine.generate_from_params(params)
    assert len(output.panel_slots) == 6
    assert output.dimensions.width == 2480.0
    assert output.dimensions.height == 3508.0
    assert len(output.reading_order_panel_ids) == 6

# ==============================================================================
# 11. REST API Integration Tests
# ==============================================================================

def test_canvas_api_endpoints():
    """Verifies that FastAPI canvas endpoints return valid template catalogs, layouts, and SVG previews."""
    from fastapi.testclient import TestClient
    from app.api.server import app

    client = TestClient(app)

    # 1. GET /api/v1/canvas/templates
    resp_tpl = client.get("/api/v1/canvas/templates")
    assert resp_tpl.status_code == 200
    data = resp_tpl.json()
    assert "templates" in data
    assert data["count"] >= 5

    # 2. POST /api/v1/canvas/generate
    payload = {
        "page_format": "A4",
        "width_px": 2480.0,
        "height_px": 3508.0,
        "dpi": 300.0,
        "layout_template": "4_panel_grid",
        "reading_direction": "rtl"
    }
    resp_gen = client.post("/api/v1/canvas/generate", json=payload)
    assert resp_gen.status_code == 200
    gen_data = resp_gen.json()
    assert len(gen_data["panel_slots"]) == 4

    # 3. POST /api/v1/canvas/preview/svg
    resp_svg = client.post("/api/v1/canvas/preview/svg", json=payload)
    assert resp_svg.status_code == 200
    assert "image/svg+xml" in resp_svg.headers.get("content-type", "")
    assert "<svg" in resp_svg.text

# ==============================================================================
# 12. Full-Bleed and Intentional Overlap Boundary Tests
# ==============================================================================

def test_full_bleed_panel_geometry_and_boundaries():
    """Verifies that is_full_bleed=True permits panels to extend to bleed_box, but rejecting outer spill."""
    from app.canvas.templates.base import BaseLayoutTemplate

    class DummyTemplate(BaseLayoutTemplate):
        template_id = LayoutTemplateId.MANGA_GRID
        def generate(self, canvas_spec, page_spec, **params):
            pass

    t = DummyTemplate()
    cs = CanvasSpec(width_px=1000.0, height_px=1000.0, bleed=BleedSpec.uniform(35.0))
    ps = PageSpec(page_id="page_bleed")
    trim, bleed, safe, usable = t.compute_canonical_boxes(cs)

    # 1. Standard panel (is_full_bleed=False) extending into bleed area must FAIL
    spill_panel = PanelSlot(
        panel_id="panel_spill",
        reading_order=1,
        rect=Rect(x=-10.0, y=0.0, width=500.0, height=500.0),
        is_full_bleed=False
    )
    res_spill = CanvasLayoutResult(
        canvas_id="c1", canvas_spec=cs, page_spec=ps,
        template_id=LayoutTemplateId.MANGA_GRID,
        reading_direction=ReadingDirection.RTL,
        panel_slots=[spill_panel],
        trim_box=trim, bleed_box=bleed, safe_area_box=safe, usable_box=usable,
        reading_order_panel_ids=["panel_spill"]
    )
    with pytest.raises(OutOfBoundsLayoutError):
        t.validate_layout(res_spill, strict=True)

    # 2. Full-bleed panel (is_full_bleed=True) extending into bleed area (within bleed_box) must PASS
    bleed_ok_panel = PanelSlot(
        panel_id="panel_bleed_ok",
        reading_order=1,
        rect=Rect(x=-35.0, y=-35.0, width=500.0, height=500.0),
        is_full_bleed=True,
        bleed_edges=["left", "top"],
    )
    res_bleed_ok = CanvasLayoutResult(
        canvas_id="c2", canvas_spec=cs, page_spec=ps,
        template_id=LayoutTemplateId.MANGA_GRID,
        reading_direction=ReadingDirection.RTL,
        panel_slots=[bleed_ok_panel],
        trim_box=trim, bleed_box=bleed, safe_area_box=safe, usable_box=usable,
        reading_order_panel_ids=["panel_bleed_ok"]
    )
    diags = t.validate_layout(res_bleed_ok, strict=True)
    assert len(diags) == 0

    # A full-bleed flag and a large bleed box cannot authorize an undeclared edge.
    bleed_missing_edge = bleed_ok_panel.model_copy(update={"bleed_edges": ["left"]})
    res_missing_edge = res_bleed_ok.model_copy(update={"panel_slots": [bleed_missing_edge]})
    with pytest.raises(OutOfBoundsLayoutError, match="undeclared edge"):
        t.validate_layout(res_missing_edge, strict=True)

    # 3. Full-bleed panel extending BEYOND bleed_box must FAIL
    bleed_too_far = PanelSlot(
        panel_id="panel_too_far",
        reading_order=1,
        rect=Rect(x=-50.0, y=-35.0, width=500.0, height=500.0),
        is_full_bleed=True
    )
    res_too_far = CanvasLayoutResult(
        canvas_id="c3", canvas_spec=cs, page_spec=ps,
        template_id=LayoutTemplateId.MANGA_GRID,
        reading_direction=ReadingDirection.RTL,
        panel_slots=[bleed_too_far],
        trim_box=trim, bleed_box=bleed, safe_area_box=safe, usable_box=usable,
        reading_order_panel_ids=["panel_too_far"]
    )
    with pytest.raises(OutOfBoundsLayoutError):
        t.validate_layout(res_too_far, strict=True)

def test_intentional_overlap_requires_pair_reason_and_layer_order():
    """A global legacy flag alone cannot authorize every panel intersection."""
    from app.canvas.templates.base import BaseLayoutTemplate

    class DummyTemplate(BaseLayoutTemplate):
        template_id = LayoutTemplateId.MANGA_GRID
        def generate(self, canvas_spec, page_spec, **params):
            pass

    t = DummyTemplate()
    cs = CanvasSpec(width_px=1000.0, height_px=1000.0)
    ps = PageSpec(page_id="page_overlap")
    trim, bleed, safe, usable = t.compute_canonical_boxes(cs)

    p1 = PanelSlot(
        panel_id="panel_01", reading_order=1,
        rect=Rect(x=100.0, y=100.0, width=300.0, height=300.0),
        is_intentional_overlap=False
    )
    p2 = PanelSlot(
        panel_id="panel_02", reading_order=2,
        rect=Rect(x=200.0, y=200.0, width=300.0, height=300.0),  # Intersects p1!
        is_intentional_overlap=False
    )

    # Unintended overlap -> must raise UnintendedOverlapError
    res_fail = CanvasLayoutResult(
        canvas_id="c_fail", canvas_spec=cs, page_spec=ps,
        template_id=LayoutTemplateId.MANGA_GRID,
        reading_direction=ReadingDirection.RTL,
        panel_slots=[p1, p2],
        trim_box=trim, bleed_box=bleed, safe_area_box=safe, usable_box=usable,
        reading_order_panel_ids=["panel_01", "panel_02"]
    )
    with pytest.raises(UnintendedOverlapError):
        t.validate_layout(res_fail, strict=True)

    # The legacy blanket flag alone must still fail.
    p2_legacy_flag = p2.model_copy(update={"is_intentional_overlap": True})
    res_legacy = res_fail.model_copy(update={"panel_slots": [p1, p2_legacy_flag]})
    with pytest.raises(UnintendedOverlapError):
        t.validate_layout(res_legacy, strict=True)

    # A pair-specific declaration, rationale, and distinct layer order passes.
    p2_intentional = p2.model_copy(update={
        "is_intentional_overlap": True,
        "intentional_overlap_with": ["panel_01"],
        "overlap_reason": "Inset impact panel breaks into the establishing panel.",
        "z_index": 1,
    })
    res_pass = CanvasLayoutResult(
        canvas_id="c_pass", canvas_spec=cs, page_spec=ps,
        template_id=LayoutTemplateId.MANGA_GRID,
        reading_direction=ReadingDirection.RTL,
        panel_slots=[p1, p2_intentional],
        trim_box=trim, bleed_box=bleed, safe_area_box=safe, usable_box=usable,
        reading_order_panel_ids=["panel_01", "panel_02"]
    )
    diags = t.validate_layout(res_pass, strict=True)
    assert len(diags) == 0

    # Even an explicit pair requires deterministic stacking order.
    p2_same_layer = p2_intentional.model_copy(update={"z_index": p1.z_index})
    res_same_layer = res_pass.model_copy(update={"panel_slots": [p1, p2_same_layer]})
    with pytest.raises(UnintendedOverlapError, match="distinct z_index"):
        t.validate_layout(res_same_layer, strict=True)


def test_mixed_polygon_rectangle_overlap_uses_actual_polygon_not_bbox():
    from app.canvas.templates.base import BaseLayoutTemplate
    from app.canvas.geometry_utils import shoelace_area

    class DummyTemplate(BaseLayoutTemplate):
        template_id = LayoutTemplateId.MANGA_GRID
        def generate(self, canvas_spec, page_spec, **params):
            pass

    t = DummyTemplate()
    cs = CanvasSpec(width_px=1000.0, height_px=1000.0)
    ps = PageSpec(page_id="page_mixed_shape")
    trim, bleed, safe, usable = t.compute_canonical_boxes(cs)
    triangle = [Point(x=0, y=0), Point(x=100, y=0), Point(x=0, y=100)]
    p1 = PanelSlot(
        panel_id="panel_triangle", reading_order=1,
        rect=Rect(x=0, y=0, width=100, height=100), polygon=triangle,
    )
    p2 = PanelSlot(
        panel_id="panel_rect", reading_order=2,
        rect=Rect(x=80, y=80, width=10, height=10),
    )
    assert shoelace_area(triangle) > 0
    result = CanvasLayoutResult(
        canvas_id="canvas_mixed_shape", canvas_spec=cs, page_spec=ps,
        template_id=LayoutTemplateId.MANGA_GRID,
        reading_direction=ReadingDirection.RTL,
        panel_slots=[p1, p2], trim_box=trim, bleed_box=bleed,
        safe_area_box=safe, usable_box=usable,
        reading_order_panel_ids=["panel_triangle", "panel_rect"],
    )
    assert t.validate_layout(result, strict=True) == []


def test_three_panel_hero_template_generation():
    """Verifies that ThreePanelHeroTemplate produces 3 valid non-overlapping panels with a wide hero panel."""
    cs = CanvasSpec.create_b5()
    ps = PageSpec(page_id="test_hero", reading_direction=ReadingDirection.RTL)
    result = CanvasEngine.generate_layout(
        canvas_spec=cs,
        page_spec=ps,
        template_id=LayoutTemplateId.THREE_PANEL_HERO,
    )
    assert result.panel_count == 3
    assert len(result.diagnostics) == 0
    p3 = result.get_panel("panel_03")
    assert p3 is not None
    assert p3.rect.width == result.usable_box.width


def test_three_panel_slanted_template_generation():
    """Verifies that ThreePanelSlantedTemplate generates 3 trapezoidal panels with perspective slanted gutters."""
    cs = CanvasSpec.create_b5()
    ps = PageSpec(page_id="test_slanted", reading_direction=ReadingDirection.RTL)
    result = CanvasEngine.generate_layout(
        canvas_spec=cs,
        page_spec=ps,
        template_id=LayoutTemplateId.THREE_PANEL_SLANTED,
    )
    assert result.panel_count == 3
    assert len(result.diagnostics) == 0
    for p in result.panel_slots:
        assert p.has_polygon
        assert len(p.polygon) == 4


def test_five_panel_action_template_generation():
    """Verifies that FivePanelActionTemplate produces 5 dynamic panels matching Image 5."""
    cs = CanvasSpec.create_b5()
    ps = PageSpec(page_id="test_action5", reading_direction=ReadingDirection.RTL)
    result = CanvasEngine.generate_layout(
        canvas_spec=cs,
        page_spec=ps,
        template_id=LayoutTemplateId.FIVE_PANEL_ACTION,
    )
    assert result.panel_count == 5
    assert len(result.diagnostics) == 0


def test_dynamic_shonen_peak_gutter_generation():
    """Verifies that DynamicShonenTemplate with peak_v bottom gutter produces exact Image 1 layout."""
    cs = CanvasSpec.create_b5()
    ps = PageSpec(page_id="test_peak", reading_direction=ReadingDirection.RTL)
    result = CanvasEngine.generate_layout(
        canvas_spec=cs,
        page_spec=ps,
        template_id=LayoutTemplateId.DYNAMIC_SHONEN,
        bottom_gutter_style="peak_v",
    )
    assert result.panel_count == 4
    assert len(result.diagnostics) == 0
    p4 = result.get_panel("panel_04")
    assert p4 is not None
    assert p4.has_polygon


def test_all_sixteen_templates_generate_and_validate():
    """Exhaustively verifies that all 16 layout templates generate valid, non-overlapping layouts."""
    cs = CanvasSpec.create_b5()
    ps = PageSpec(page_id="test_all_16", reading_direction=ReadingDirection.RTL)
    
    for tid in LayoutTemplateId:
        result = CanvasEngine.generate_layout(
            canvas_spec=cs,
            page_spec=ps,
            template_id=tid,
        )
        assert result.panel_count > 0, f"Template {tid.value} generated 0 panels"
        assert len(result.diagnostics) == 0, f"Template {tid.value} failed validation: {result.diagnostics}"
        for panel in result.panel_slots:
            assert panel.rect.width > 0
            assert panel.rect.height > 0
            if panel.has_polygon:
                assert len(panel.polygon) >= 3


def test_canvas_router_resolution_not_fake():
    """Verifies that resolve_template_id accurately resolves all templates without falling back to manga_grid."""
    from app.canvas.templates import resolve_template_id
    
    assert resolve_template_id("three_panel_hero") == LayoutTemplateId.THREE_PANEL_HERO
    assert resolve_template_id("three_panel_slanted") == LayoutTemplateId.THREE_PANEL_SLANTED
    assert resolve_template_id("five_panel_action") == LayoutTemplateId.FIVE_PANEL_ACTION
    assert resolve_template_id("four_panel_cinematic") == LayoutTemplateId.FOUR_PANEL_CINEMATIC
    assert resolve_template_id("diagonal_slash_battle") == LayoutTemplateId.DIAGONAL_SLASH_BATTLE
    assert resolve_template_id("shonen_climax_spread") == LayoutTemplateId.SHONEN_CLIMAX_SPREAD
    assert resolve_template_id("nine_panel_grid") == LayoutTemplateId.NINE_PANEL_GRID
    assert resolve_template_id("two_panel_dramatic_spread") == LayoutTemplateId.TWO_PANEL_DRAMATIC_SPREAD
    assert resolve_template_id("seven_panel_action_burst") == LayoutTemplateId.SEVEN_PANEL_ACTION_BURST
    assert resolve_template_id("eight_panel_manhwa") == LayoutTemplateId.EIGHT_PANEL_MANHWA
    assert resolve_template_id("three_tier_action_slant") == LayoutTemplateId.THREE_TIER_ACTION_SLANT


def test_spacing_inspector_measures_actual_gaps_and_trim_clearance():
    slots = [
        PanelSlot(panel_id="p1", reading_order=1, rect=Rect(x=30, y=30, width=100, height=100)),
        PanelSlot(panel_id="p2", reading_order=2, rect=Rect(x=140, y=30, width=100, height=100)),
    ]

    result = inspect_panel_spacing(
        slots,
        trim_box=Rect(x=0, y=0, width=270, height=270),
        configured_margins_px={"top": 30, "right": 30, "bottom": 30, "left": 30},
    )

    assert result["minimum_edge_gap_px"] == 10.0
    assert result["overlapping_panel_pairs"] == []
    assert result["margin_clearance_valid"] is True
    assert result["panels"][0]["measured_margins_px"] == {"top": 30.0, "right": 140.0, "bottom": 140.0, "left": 30.0}



