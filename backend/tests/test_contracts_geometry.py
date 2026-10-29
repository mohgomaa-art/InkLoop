"""
Unit tests for InkLoop Canonical Geometry and Coordinate Conventions.
Verifies spatial models, half-open boundary intervals, conversions, and edge cases.
"""
import math
import pytest
from app.contracts.geometry import (
    Point,
    Size,
    Rect,
    Transform2D,
    FitMode,
    CoordinateSpace,
    mm_to_px,
    px_to_mm,
    pt_to_px,
    px_to_pt,
    rect_contains,
    rect_intersects,
    rect_intersection,
    rect_union,
    snap_to_pixel_grid,
    panel_to_page,
    page_to_panel,
    normalize_point,
    denormalize_point,
    normalize_rect,
    denormalize_rect,
    calculate_fit_transform,
    validate_panel_in_canvas,
)
from app.contracts.errors import InvalidGeometryError, OutOfBoundsError
from app.schemas import BoundingBox

# --- Model Validation & Invalid Boundary Tests ---

def test_point_valid():
    p = Point(x=10.5, y=20.25)
    assert p.x == 10.5
    assert p.y == 20.25

def test_point_non_finite_rejected():
    with pytest.raises(InvalidGeometryError):
        Point(x=float("nan"), y=10.0)
    with pytest.raises(InvalidGeometryError):
        Point(x=10.0, y=float("inf"))

def test_size_valid():
    s = Size(width=1920.0, height=1080.0)
    assert s.width == 1920.0
    assert s.height == 1080.0
    assert pytest.approx(s.aspect_ratio, 0.001) == 16.0 / 9.0

def test_size_zero_or_negative_rejected():
    with pytest.raises(InvalidGeometryError):
        Size(width=0.0, height=100.0)
    with pytest.raises(InvalidGeometryError):
        Size(width=100.0, height=-5.0)

def test_rect_valid():
    r = Rect(x=50.0, y=100.0, width=400.0, height=300.0)
    assert r.left == 50.0
    assert r.top == 100.0
    assert r.right == 450.0
    assert r.bottom == 400.0
    assert r.center == Point(x=250.0, y=250.0)
    assert pytest.approx(r.aspect_ratio, 0.001) == 400.0 / 300.0

def test_rect_zero_or_negative_rejected():
    with pytest.raises(InvalidGeometryError):
        Rect(x=0.0, y=0.0, width=-10.0, height=50.0)
    with pytest.raises(InvalidGeometryError):
        Rect(x=0.0, y=0.0, width=50.0, height=0.0)

# --- Half-Open Boundary & Intersection Tests ---

def test_rect_half_open_sharing_edge_does_not_intersect():
    """Adjacent panels sharing an edge [0, 100) and [100, 200) must NOT intersect."""
    panel_a = Rect(x=0.0, y=0.0, width=100.0, height=100.0)
    panel_b = Rect(x=100.0, y=0.0, width=100.0, height=100.0)
    assert rect_intersects(panel_a, panel_b) is False
    assert rect_intersection(panel_a, panel_b) is None

def test_rect_half_open_sharing_corner_does_not_intersect():
    panel_a = Rect(x=0.0, y=0.0, width=100.0, height=100.0)
    panel_c = Rect(x=100.0, y=100.0, width=100.0, height=100.0)
    assert rect_intersects(panel_a, panel_c) is False
    assert rect_intersection(panel_a, panel_c) is None

def test_rect_overlapping_intersection():
    panel_a = Rect(x=50.0, y=50.0, width=100.0, height=100.0)  # [50, 150) x [50, 150)
    panel_b = Rect(x=100.0, y=80.0, width=100.0, height=100.0) # [100, 200) x [80, 180)
    assert rect_intersects(panel_a, panel_b) is True
    inter = rect_intersection(panel_a, panel_b)
    assert inter is not None
    assert inter.x == 100.0
    assert inter.y == 80.0
    assert inter.width == 50.0   # 150 - 100
    assert inter.height == 70.0  # 150 - 80

def test_rect_union():
    a = Rect(x=10.0, y=20.0, width=50.0, height=50.0)
    b = Rect(x=100.0, y=80.0, width=20.0, height=20.0)
    u = rect_union(a, b)
    assert u.x == 10.0
    assert u.y == 20.0
    assert u.width == 110.0  # 120 - 10
    assert u.height == 80.0  # 100 - 20

def test_rect_contains():
    outer = Rect(x=0.0, y=0.0, width=1000.0, height=1000.0)
    inner = Rect(x=100.0, y=100.0, width=200.0, height=200.0)
    overflow = Rect(x=900.0, y=900.0, width=200.0, height=200.0)

    assert rect_contains(outer, inner) is True
    assert rect_contains(outer, outer) is True
    assert rect_contains(outer, overflow) is False

# --- Unit Conversion Tests ---

def test_unit_conversions():
    # 1 inch = 25.4 mm = 300 px at 300 DPI
    assert pytest.approx(mm_to_px(25.4, 300.0), 0.001) == 300.0
    assert pytest.approx(px_to_mm(300.0, 300.0), 0.001) == 25.4
    # 72 pt = 1 inch = 300 px at 300 DPI
    assert pytest.approx(pt_to_px(72.0, 300.0), 0.001) == 300.0
    assert pytest.approx(px_to_pt(300.0, 300.0), 0.001) == 72.0

# --- Coordinate Space Transformations ---

def test_panel_page_coordinate_reversibility():
    panel_rect = Rect(x=200.0, y=350.0, width=600.0, height=400.0)
    local_pt = Point(x=50.0, y=75.0)

    page_pt = panel_to_page(local_pt, panel_rect)
    assert page_pt == Point(x=250.0, y=425.0)

    reversed_pt = page_to_panel(page_pt, panel_rect)
    assert reversed_pt == local_pt

def test_normalize_denormalize_reversibility():
    container = Rect(x=100.0, y=200.0, width=800.0, height=600.0)
    pt = Point(x=500.0, y=500.0)

    norm = normalize_point(pt, container)
    assert norm.x == (500.0 - 100.0) / 800.0  # 0.5
    assert norm.y == (500.0 - 200.0) / 600.0  # 0.5

    denorm = denormalize_point(norm, container)
    assert pytest.approx(denorm.x, 0.001) == pt.x
    assert pytest.approx(denorm.y, 0.001) == pt.y

def test_normalize_rect_reversibility():
    container = Rect(x=0.0, y=0.0, width=1000.0, height=2000.0)
    r = Rect(x=250.0, y=500.0, width=500.0, height=1000.0)

    norm_r = normalize_rect(r, container)
    assert norm_r.x == 0.25
    assert norm_r.y == 0.25
    assert norm_r.width == 0.5
    assert norm_r.height == 0.5

    denorm_r = denormalize_rect(norm_r, container)
    assert denorm_r == r

# --- FitMode Transformation Tests ---

def test_calculate_fit_contain():
    # Landscape 1920x1080 into square 500x500
    source = Size(width=1920.0, height=1080.0)
    target = Rect(x=100.0, y=100.0, width=500.0, height=500.0)

    t = calculate_fit_transform(source, target, FitMode.CONTAIN, anchor=Point(x=0.5, y=0.5))
    expected_scale = 500.0 / 1920.0  # ~0.2604
    assert pytest.approx(t.scale_x, 0.001) == expected_scale
    assert pytest.approx(t.scale_y, 0.001) == expected_scale
    assert pytest.approx(t.translate_x, 0.001) == target.x  # fits width exactly, tx ~ 100
    expected_rendered_h = 1080.0 * expected_scale  # 281.25
    expected_ty = 100.0 + (500.0 - expected_rendered_h) * 0.5
    assert pytest.approx(t.translate_y, 0.001) == expected_ty

def test_calculate_fit_cover():
    # Landscape 1920x1080 into square 500x500
    source = Size(width=1920.0, height=1080.0)
    target = Rect(x=0.0, y=0.0, width=500.0, height=500.0)

    t = calculate_fit_transform(source, target, FitMode.COVER, anchor=Point(x=0.5, y=0.5))
    expected_scale = 500.0 / 1080.0  # ~0.4629
    assert pytest.approx(t.scale_x, 0.001) == expected_scale
    assert pytest.approx(t.scale_y, 0.001) == expected_scale
    expected_rendered_w = 1920.0 * expected_scale  # ~888.88
    expected_tx = (500.0 - expected_rendered_w) * 0.5
    assert pytest.approx(t.translate_x, 0.001) == expected_tx
    assert t.translate_y == 0.0

# --- Boundary Validation & Snapping Tests ---

def test_validate_panel_in_canvas_strict():
    canvas = Rect(x=0.0, y=0.0, width=2480.0, height=3508.0)
    panel_valid = Rect(x=100.0, y=100.0, width=1000.0, height=800.0)
    validate_panel_in_canvas(panel_valid, canvas)  # Should not raise

    panel_overflow = Rect(x=2000.0, y=100.0, width=600.0, height=800.0)  # right edge at 2600 > 2480
    with pytest.raises(OutOfBoundsError):
        validate_panel_in_canvas(panel_overflow, canvas, allow_bleed=False)

def test_validate_panel_with_bleed_margin():
    canvas = Rect(x=0.0, y=0.0, width=2480.0, height=3508.0)
    bleed_panel = Rect(x=-30.0, y=100.0, width=1000.0, height=800.0)

    # Fails without bleed
    with pytest.raises(OutOfBoundsError):
        validate_panel_in_canvas(bleed_panel, canvas, allow_bleed=False)

    # Passes with 35px bleed allowance
    validate_panel_in_canvas(bleed_panel, canvas, allow_bleed=True, bleed_margin_px=35.0)

def test_snap_to_pixel_grid():
    subpixel_rect = Rect(x=10.4, y=20.6, width=100.2, height=199.8)
    snapped = snap_to_pixel_grid(subpixel_rect)
    assert snapped.x == 10.0
    assert snapped.y == 21.0
    assert snapped.width == 100.0
    assert snapped.height == 200.0

def test_bounding_box_rect_bridge():
    bbox = BoundingBox(x=81.0, y=71.0, width=1156.0, height=1848.0, label="person", confidence=0.99)
    rect = bbox.to_rect()
    assert isinstance(rect, Rect)
    assert rect.x == 81.0
    assert rect.y == 71.0
    assert rect.width == 1156.0
    assert rect.height == 1848.0

    restored_bbox = BoundingBox.from_rect(rect, label="character", confidence=1.0)
    assert restored_bbox.x == 81.0
    assert restored_bbox.label == "character"
