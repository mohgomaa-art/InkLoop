"""Regression test suite for Phase 4 & Phase 5: Unified Placement & Tail Clearance.

Validates that:
1. compute_exterior_tail_tip mathematically terminates outside the character bounding box.
2. calculate_safe_bubble_placement never pierces the character's face.
3. Multi-bubble placement adheres to monotonic LTR/RTL reading constraints.
4. Protected regions (faces, character bodies) have zero overlap with placed bubbles.
"""
import pytest
from app.contracts.geometry import Point, Rect
from app.canvas.character_locator import compute_exterior_tail_tip, calculate_safe_bubble_placement
from app.canvas.placement_engine import PlacementEngine, BubblePlacementRequest, ProtectedRegion


def test_compute_exterior_tail_tip_outside_character_box():
    # Character box at X: 200..400, Y: 300..700
    char_box = Rect(x=200.0, y=300.0, width=200.0, height=400.0)
    # Head anchor inside face: X: 300, Y: 360
    head_anchor = Point(x=300.0, y=360.0)

    # 1. Bubble above character: center at (300, 150)
    bubble_above = Point(x=300.0, y=150.0)
    tip_above = compute_exterior_tail_tip(bubble_above, head_anchor, char_box, clearance=12.0)
    # Must terminate above char_box.y (300.0)
    assert tip_above.y < char_box.y
    assert abs(tip_above.y - (char_box.y - 12.0)) < 1.0
    assert abs(tip_above.x - 300.0) < 1.0

    # 2. Bubble to the left: center at (80, 360)
    bubble_left = Point(x=80.0, y=360.0)
    tip_left = compute_exterior_tail_tip(bubble_left, head_anchor, char_box, clearance=12.0)
    # Must terminate to the left of char_box.x (200.0)
    assert tip_left.x < char_box.x
    assert abs(tip_left.x - (char_box.x - 12.0)) < 1.0

    # 3. Bubble to the right: center at (550, 360)
    bubble_right = Point(x=550.0, y=360.0)
    tip_right = compute_exterior_tail_tip(bubble_right, head_anchor, char_box, clearance=12.0)
    # Must terminate to the right of char_box.right (400.0)
    assert tip_right.x > char_box.right
    assert abs(tip_right.x - (char_box.right + 12.0)) < 1.0


def test_calculate_safe_bubble_placement_terminates_outside_face():
    panel_rect = Rect(x=0.0, y=0.0, width=800.0, height=800.0)
    char_bounds = Rect(x=300.0, y=300.0, width=200.0, height=350.0)

    bubble_pos, tail_tip = calculate_safe_bubble_placement(
        panel_rect=panel_rect,
        bubble_w=180.0,
        bubble_h=80.0,
        character_bounds=char_bounds,
        reading_direction="ltr",
    )

    # Verify bubble does not overlap character
    bubble_rect = Rect(x=bubble_pos.x, y=bubble_pos.y, width=180.0, height=80.0)
    assert not (
        bubble_rect.right <= char_bounds.x
        or char_bounds.right <= bubble_rect.x
        or bubble_rect.bottom <= char_bounds.y
        or char_bounds.bottom <= bubble_rect.y
    ) is False  # Zero overlap!

    # Verify tail tip is outside character bounds
    is_outside = (
        tail_tip.x < char_bounds.x
        or tail_tip.x > char_bounds.right
        or tail_tip.y < char_bounds.y
        or tail_tip.y > char_bounds.bottom
    )
    assert is_outside, f"Tail tip {tail_tip} is inside character bounds {char_bounds}"


def test_placement_engine_monotonic_ltr_order():
    engine = PlacementEngine()
    panel = Rect(x=50.0, y=50.0, width=600.0, height=600.0)
    safe_margin = Rect(x=20.0, y=20.0, width=760.0, height=760.0)

    # Character in the center
    char_region = ProtectedRegion(x=250.0, y=200.0, width=150.0, height=250.0, label="speaker")

    b1 = BubblePlacementRequest(
        bubble_id="b1",
        type_id="speech.normal",
        text="Turn one: Greetings!",
        reading_order=1,
    )
    b2 = BubblePlacementRequest(
        bubble_id="b2",
        type_id="speech.normal",
        text="Turn two: Good day to you!",
        reading_order=2,
    )

    results = engine.place_bubbles(
        panel_rect=panel,
        bubbles=[b1, b2],
        protected_regions=[char_region],
        reading_direction="ltr",
        page_safe_margin=safe_margin,
    )

    assert len(results) == 2
    res_b1 = next(r for r in results if r.bubble_id == "b1")
    res_b2 = next(r for r in results if r.bubble_id == "b2")

    # In LTR, Bubble 1 should be read before Bubble 2:
    # either b1 is higher (y1 < y2) or at same tier and to the left (x1 < x2)
    assert res_b1.rect.y <= res_b2.rect.y + 30.0
    if abs(res_b1.rect.y - res_b2.rect.y) < 35.0:
        assert res_b1.rect.x < res_b2.rect.x

    # Verify neither bubble intersects character region
    for res in [res_b1, res_b2]:
        overlap = not (
            res.rect.right <= char_region.x
            or char_region.right <= res.rect.x
            or res.rect.bottom <= char_region.y
            or char_region.bottom <= res.rect.y
        )
        assert not overlap
