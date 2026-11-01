"""
InkLoop Image-Canvas Integration Engine (E3) - Comprehensive Test Suite.
Verifies fitting modes (CONTAIN, COVER, STRETCH), aspect-ratio preservation, anchor cropping,
polygonal alpha masking, full-bleed envelopes, resampling, error handling, and page integration.
"""
import io
import pytest
from PIL import Image, ImageDraw

from app.contracts.geometry import (
    Rect,
    Point,
    Size,
    FitMode,
    Transform2D,
)
from app.contracts.engine import ImageCanvasIntegrationParams, ImageCanvasIntegrationOutput
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    PanelSlot,
    LayoutTemplateId,
    ReadingDirection,
)
from app.canvas.engine import CanvasEngine
from app.image_canvas.models import (
    PlacementSpec,
    PlacedPanelLayer,
    PageIntegrationResult,
    ResamplingFilter,
)
from app.image_canvas.errors import (
    PlacementError,
    InvalidPlacementGeometryError,
    AssetResolutionError,
    UnsupportedImageFormatError,
    AllocationLimitExceededError,
    AspectRatioDistortionError,
)
from app.image_canvas.fitter import (
    compute_placement_transform,
    compute_source_crop_rect,
)
from app.image_canvas.raster_ops import (
    load_source_image,
    apply_placement_raster,
    apply_polygon_mask,
    encode_png_bytes,
)
from app.image_canvas.engine import ImageCanvasIntegrationEngine

# Helper to create synthetic in-memory PNG images with identifiable color patterns
def create_test_image_bytes(width: int, height: int, color=(255, 100, 50, 255)) -> bytes:
    img = Image.new("RGBA", (width, height), color)
    draw = ImageDraw.Draw(img)
    # Draw simple gradient/corner dots to allow testing anchor crops
    draw.rectangle([0, 0, 10, 10], fill=(255, 255, 255, 255))  # Top-Left white mark
    draw.rectangle([width - 10, height - 10, width, height], fill=(0, 0, 0, 255))  # Bottom-Right black mark
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ==============================================================================
# 1. Mathematical Transform & Crop Tests
# ==============================================================================

def test_cover_fit_aspect_preservation_and_crop():
    """Verifies that COVER mode scales uniformly to completely cover the slot and crops excess."""
    # 1000x2000 portrait source into 1000x1000 square slot
    source_size = Size(width=1000.0, height=2000.0)
    target_rect = Rect(x=100.0, y=100.0, width=1000.0, height=1000.0)

    transform, placed_rect, is_clipped = compute_placement_transform(
        source_size, target_rect, mode=FitMode.COVER, anchor=Point(x=0.5, y=0.5)
    )

    # Scale should be 1.0 (1000/1000), not 0.5 (1000/2000)
    assert transform.scale_x == 1.0
    assert transform.scale_y == 1.0
    assert is_clipped is True
    assert placed_rect.width == 1000.0
    assert placed_rect.height == 1000.0

    # Source crop rect should be 1000x1000 centered vertically
    crop_rect = compute_source_crop_rect(source_size, target_rect, anchor=Point(x=0.5, y=0.5))
    assert crop_rect.width == 1000.0
    assert crop_rect.height == 1000.0
    assert crop_rect.x == 0.0
    assert crop_rect.y == 500.0  # Center cropped from 2000 px height

def test_contain_fit_aspect_preservation_and_letterbox():
    """Verifies that CONTAIN mode scales uniformly so image fits entirely without clipping."""
    # 2000x1000 landscape source into 1000x1000 square slot
    source_size = Size(width=2000.0, height=1000.0)
    target_rect = Rect(x=100.0, y=100.0, width=1000.0, height=1000.0)

    transform, placed_rect, is_clipped = compute_placement_transform(
        source_size, target_rect, mode=FitMode.CONTAIN, anchor=Point(x=0.5, y=0.5)
    )

    # Scale should be 0.5 (1000/2000)
    assert transform.scale_x == 0.5
    assert transform.scale_y == 0.5
    assert is_clipped is False
    # Placed dimensions: 1000x500 centered vertically in target_rect
    assert placed_rect.width == 1000.0
    assert placed_rect.height == 500.0
    assert placed_rect.x == 100.0
    assert placed_rect.y == 350.0  # 100 + (1000 - 500)*0.5

def test_stretch_mode_distorts_dimensions():
    """Verifies that STRETCH mode maps source directly to target slot dimensions without crop."""
    source_size = Size(width=1000.0, height=2000.0)
    target_rect = Rect(x=0.0, y=0.0, width=500.0, height=500.0)

    transform, placed_rect, is_clipped = compute_placement_transform(
        source_size, target_rect, mode=FitMode.STRETCH
    )
    assert transform.scale_x == 0.5
    assert transform.scale_y == 0.25
    assert is_clipped is False
    assert placed_rect.width == 500.0
    assert placed_rect.height == 500.0

# ==============================================================================
# 2. Anchor Point Alignment Tests
# ==============================================================================

def test_anchor_offsets_in_cover_mode():
    """Verifies that anchor controls whether top, center, or bottom of image is kept during COVER crop."""
    source_size = Size(width=1000.0, height=3000.0)
    target_rect = Rect(x=0.0, y=0.0, width=1000.0, height=1000.0)

    # Top anchor (0.0): keep top 1000 px
    crop_top = compute_source_crop_rect(source_size, target_rect, anchor=Point(x=0.5, y=0.0))
    assert crop_top.y == 0.0

    # Center anchor (0.5): keep middle 1000 px
    crop_mid = compute_source_crop_rect(source_size, target_rect, anchor=Point(x=0.5, y=0.5))
    assert crop_mid.y == 1000.0

    # Bottom anchor (1.0): keep bottom 1000 px
    crop_bot = compute_source_crop_rect(source_size, target_rect, anchor=Point(x=0.5, y=1.0))
    assert crop_bot.y == 2000.0

def test_invalid_anchor_range_rejected():
    """Verifies that anchor coordinates outside [0.0, 1.0] are rejected by PlacementSpec validation."""
    with pytest.raises(InvalidPlacementGeometryError):
        PlacementSpec(target_panel_id="panel_01", anchor=Point(x=1.5, y=0.5))

def test_panel_placement_rejects_non_aspect_preserving_modes_and_scale():
    with pytest.raises(InvalidPlacementGeometryError, match="preserve its source aspect ratio"):
        PlacementSpec(target_panel_id="panel_01", fit_mode=FitMode.STRETCH)

    with pytest.raises(InvalidPlacementGeometryError, match="preserve its source aspect ratio"):
        PlacementSpec(target_panel_id="panel_01", fit_mode=FitMode.MANUAL)

    with pytest.raises(InvalidPlacementGeometryError, match="preserve aspect ratio"):
        PlacementSpec(
            target_panel_id="panel_01",
            manual_transform=Transform2D(scale_x=1.2, scale_y=0.8),
        )

    with pytest.raises(InvalidPlacementGeometryError):
        PlacementSpec(target_panel_id="panel_01", anchor=Point(x=0.5, y=-0.1))

# ==============================================================================
# 3. Raster Placement & Resampling Tests
# ==============================================================================

def test_raster_placement_dimensions_match_target_exactly():
    """Verifies that placed raster output matches target slot dimensions exactly to the pixel."""
    src_bytes = create_test_image_bytes(800, 600)
    slot = PanelSlot(
        panel_id="panel_01",
        reading_order=1,
        rect=Rect(x=100.0, y=120.0, width=450.0, height=700.0)
    )

    spec = PlacementSpec(
        target_panel_id="panel_01",
        source_image_bytes=src_bytes,
        fit_mode=FitMode.COVER,
        resampling=ResamplingFilter.LANCZOS
    )

    layer = ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec)

    assert layer.placed_rect.width == 450.0
    assert layer.placed_rect.height == 700.0
    assert layer.is_clipped is True

    # Inspect resulting PNG image buffer
    out_img = Image.open(io.BytesIO(layer.output_image_bytes))
    assert out_img.size == (450, 700)
    assert out_img.mode == "RGBA"

def test_manual_translation_reveals_source_pixels_outside_initial_cover_crop():
    """E3 transforms the full fitted source before applying the panel crop."""
    source = Image.new("RGBA", (200, 100))
    for x in range(200):
        color = (230, 20, 20, 255) if x < 100 else (20, 30, 230, 255)
        for y in range(100):
            source.putpixel((x, y), color)
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")
    slot = PanelSlot(
        panel_id="panel_full_bounds",
        reading_order=1,
        rect=Rect(x=0, y=0, width=100, height=100),
    )

    layer = ImageCanvasIntegrationEngine.place_artwork_in_slot(
        slot,
        PlacementSpec(
            target_panel_id=slot.panel_id,
            source_image_bytes=buffer.getvalue(),
            fit_mode=FitMode.COVER,
            manual_transform=Transform2D(translate_x=25),
        ),
    )
    output = Image.open(io.BytesIO(layer.output_image_bytes)).convert("RGBA")

    assert output.size == (100, 100)
    assert output.getpixel((10, 50))[0] > 200  # previously cropped-away left source is visible
    assert output.getpixel((90, 50))[2] > 200

def test_contain_placement_with_transparent_letterbox():
    """Verifies that CONTAIN mode produces exact slot dimensions with transparent padding."""
    src_bytes = create_test_image_bytes(1000, 500, color=(0, 200, 100, 255))
    slot = PanelSlot(
        panel_id="panel_02",
        reading_order=1,
        rect=Rect(x=0.0, y=0.0, width=500.0, height=500.0)
    )

    spec = PlacementSpec(
        target_panel_id="panel_02",
        source_image_bytes=src_bytes,
        fit_mode=FitMode.CONTAIN,
        background_color=None  # Transparent padding
    )

    layer = ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec)
    out_img = Image.open(io.BytesIO(layer.output_image_bytes))

    assert out_img.size == (500, 500)
    # Middle of image (250, 250) should be opaque artwork
    assert out_img.getpixel((250, 250))[3] == 255
    # Top letterbox area (250, 50) should be transparent (alpha = 0)
    assert out_img.getpixel((250, 50))[3] == 0

# ==============================================================================
# 4. Polygonal Panel Alpha Clipping Tests
# ==============================================================================

def test_polygonal_clipping_alpha_mask():
    """Verifies that dynamic action polygonal slots mask pixels outside the polygon to alpha=0."""
    src_bytes = create_test_image_bytes(500, 500, color=(200, 50, 50, 255))

    # Right triangle panel slot in PAGE space: (100, 100) -> (300, 100) -> (100, 300)
    poly = [
        Point(x=100.0, y=100.0),
        Point(x=300.0, y=100.0),
        Point(x=100.0, y=300.0),
    ]
    slot = PanelSlot(
        panel_id="panel_poly",
        reading_order=1,
        rect=Rect(x=100.0, y=100.0, width=200.0, height=200.0),
        polygon=poly
    )

    spec = PlacementSpec(
        target_panel_id="panel_poly",
        source_image_bytes=src_bytes,
        fit_mode=FitMode.COVER,
        clip_to_polygon=True
    )

    layer = ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec)
    assert layer.has_polygon_mask is True

    out_img = Image.open(io.BytesIO(layer.output_image_bytes))
    assert out_img.size == (200, 200)

    # Point near top-left inside triangle (local 20, 20) -> should be opaque (alpha 255)
    assert out_img.getpixel((20, 20))[3] == 255
    # Point near bottom-right outside triangle (local 180, 180) -> should be transparent (alpha 0)
    assert out_img.getpixel((180, 180))[3] == 0

# ==============================================================================
# 5. Full-Bleed Placement Tests
# ==============================================================================

def test_full_bleed_placement_expansion():
    """Verifies that is_full_bleed panel expands target slot to outer bleed boundary when allow_bleed=True."""
    src_bytes = create_test_image_bytes(1000, 1000)
    app_bleed = app_bleed_fixture()
    cs = CanvasSpec(width_px=1000.0, height_px=1000.0, bleed=app_bleed)

    slot = PanelSlot(
        panel_id="panel_bleed",
        reading_order=1,
        rect=Rect(x=0.0, y=0.0, width=500.0, height=500.0),
        is_full_bleed=True
    )

    spec = PlacementSpec(
        target_panel_id="panel_bleed",
        source_image_bytes=src_bytes,
        allow_bleed=True
    )

    layer = ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec, canvas_spec=cs)

    # Slot width expands by left + right bleed (35 + 35 = 70 px)
    assert layer.target_slot_rect.width == 570.0
    assert layer.target_slot_rect.height == 570.0

def app_bleed_fixture():
    from app.canvas.models import BleedSpec
    return BleedSpec.uniform(35.0)

# ==============================================================================
# 6. Error Handling & Validation Tests
# ==============================================================================

def test_missing_or_empty_source_image_rejected():
    """Verifies that missing or zero-length source image inputs raise AssetResolutionError."""
    slot = PanelSlot(panel_id="p1", reading_order=1, rect=Rect(x=0.0, y=0.0, width=100.0, height=100.0))
    spec = PlacementSpec(target_panel_id="p1")  # No bytes, path, or artifact ID

    with pytest.raises(AssetResolutionError):
        ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec)

    # Corrupt/empty bytes
    spec_corrupt = PlacementSpec(target_panel_id="p1", source_image_bytes=b"not_an_image")
    with pytest.raises(UnsupportedImageFormatError):
        ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec_corrupt)

def test_pathological_image_dimensions_rejected():
    """Verifies that attempting placement with gigantic images raises AllocationLimitExceededError."""
    # Create valid header but claim 25,000 px dimensions
    with pytest.raises(AllocationLimitExceededError):
        from app.image_canvas.raster_ops import load_source_image
        huge_img = Image.new("RGBA", (25000, 100), (0, 0, 0, 0))
        buf = io.BytesIO()
        huge_img.save(buf, format="PNG")
        load_source_image(buf.getvalue())

# ==============================================================================
# 7. Whole-Page Integration & Determinism Tests
# ==============================================================================

def test_integrate_page_across_layout():
    """Verifies end-to-end integration of multiple artworks into a multi-panel CanvasLayoutResult."""
    cs = CanvasSpec.create_a4()
    ps = PageSpec(page_id="page_full_integration", reading_direction=ReadingDirection.RTL)
    layout = CanvasEngine.generate_layout(cs, ps, LayoutTemplateId.SIX_PANEL_CLASSIC)

    # Prepare source images for all 6 panels
    src_bytes = create_test_image_bytes(600, 600)
    placements = {
        pid: PlacementSpec(target_panel_id=pid, source_image_bytes=src_bytes, fit_mode=FitMode.COVER)
        for pid in layout.reading_order_panel_ids
    }

    page_result: PageIntegrationResult = ImageCanvasIntegrationEngine.integrate_page(layout, placements)

    assert page_result.is_fully_placed is True
    assert page_result.total_panels == 6
    assert page_result.placed_panels == 6
    assert len(page_result.unplaced_panels) == 0

    # Every layer should match its target panel slot dimensions
    for pid in layout.reading_order_panel_ids:
        layer = page_result.get_layer(pid)
        assert layer is not None
        slot = layout.get_panel(pid)
        assert layer.placed_rect.width == slot.rect.width
        assert layer.placed_rect.height == slot.rect.height

def test_placement_determinism_output_hashes():
    """Verifies that calling placement twice on identical inputs produces identical SHA-256 output hashes."""
    src_bytes = create_test_image_bytes(500, 500)
    slot = PanelSlot(panel_id="p_det", reading_order=1, rect=Rect(x=0.0, y=0.0, width=300.0, height=400.0))
    spec = PlacementSpec(target_panel_id="p_det", source_image_bytes=src_bytes)

    layer_1 = ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec)
    layer_2 = ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec)

    assert layer_1.output_content_hash == layer_2.output_content_hash
    assert layer_1.output_image_bytes == layer_2.output_image_bytes

def test_engine_run_request_and_response_adapter():
    """Verifies compatibility with shared ImageCanvasIntegrationParams and ImageCanvasIntegrationOutput."""
    src_bytes = create_test_image_bytes(800, 800)

    # Test via direct place_artwork_in_slot adapting to ImageCanvasIntegrationOutput
    slot = PanelSlot(panel_id="panel_test", reading_order=1, rect=Rect(x=50.0, y=50.0, width=400.0, height=400.0))
    spec = PlacementSpec(target_panel_id="panel_test", source_image_bytes=src_bytes)
    layer = ImageCanvasIntegrationEngine.place_artwork_in_slot(slot, spec)

    out: ImageCanvasIntegrationOutput = layer.to_engine_output()
    assert out.panel_layer_artifact_id == layer.layer_id
    assert out.placed_rect.width == 400.0
    assert out.placed_rect.height == 400.0
    assert out.fit_mode_applied == FitMode.COVER
