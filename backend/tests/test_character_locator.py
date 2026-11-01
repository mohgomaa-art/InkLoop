"""
Unit tests for Character Locator & Non-Occluding Speech Bubble Placement.
"""
from PIL import Image, ImageDraw
import io
import pytest

from app.contracts.geometry import Rect, Point, Transform2D
from app.canvas.character_locator import locate_character_in_panel, calculate_safe_bubble_placement


def _create_synthetic_character_image(width=600, height=800, char_box=(150, 100, 300, 500)) -> bytes:
    """Creates a synthetic PNG image with a distinct figure drawn at char_box."""
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    x, y, w, h = char_box
    # Draw body and head
    draw.ellipse([x + w * 0.25, y, x + w * 0.75, y + h * 0.3], fill=(220, 180, 150), outline=(20, 20, 20), width=3)
    draw.rectangle([x, y + h * 0.28, x + w, y + h], fill=(30, 40, 70), outline=(20, 20, 20), width=3)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def test_locate_character_fallback():
    panel_rect = Rect(x=50, y=50, width=400, height=600)
    char_rect = locate_character_in_panel(None, panel_rect)
    assert char_rect.x >= panel_rect.x
    assert char_rect.right <= panel_rect.right
    assert char_rect.y >= panel_rect.y
    assert char_rect.bottom <= panel_rect.bottom


def test_locate_character_from_image():
    panel_rect = Rect(x=100, y=100, width=500, height=700)
    img_bytes = _create_synthetic_character_image(width=500, height=700, char_box=(100, 150, 250, 450))
    char_rect = locate_character_in_panel(img_bytes, panel_rect)
    assert char_rect.width > 50
    assert char_rect.height > 100
    assert panel_rect.x <= char_rect.x <= panel_rect.right
    assert panel_rect.y <= char_rect.y <= panel_rect.bottom


def test_character_bounds_follow_contain_fit_and_image_rotation(monkeypatch):
    import app.canvas.character_locator as locator

    image = Image.new("RGB", (100, 100), color=(240, 240, 240))
    output = io.BytesIO()
    image.save(output, format="PNG")
    monkeypatch.setattr(locator, "_detect_focal_subject_normalized", lambda *_args: {
        "x": 0.25, "y": 0.375, "width": 0.50, "height": 0.25,
    })
    panel = Rect(x=20, y=40, width=200, height=100)

    bounds = locate_character_in_panel(
        output.getvalue(), panel, fit_mode="contain",
        transform=Transform2D(rotation_deg=90),
    )

    assert bounds.width == pytest.approx(25.0, abs=0.1)
    assert bounds.height == pytest.approx(50.0, abs=0.1)
    assert bounds.center.x == pytest.approx(panel.center.x, abs=0.1)
    assert bounds.center.y == pytest.approx(panel.center.y, abs=0.1)


def test_agent_detection_does_not_invent_center_subject_when_art_is_missing():
    panel_rect = Rect(x=40, y=30, width=400, height=600)
    assert locate_character_in_panel(None, panel_rect, allow_fallback=False) is None


def test_safe_placement_rejects_unknown_bounds_and_never_falls_back_over_subject():
    panel = Rect(x=0, y=0, width=240, height=240)
    with pytest.raises(ValueError, match="Character bounds are required"):
        calculate_safe_bubble_placement(panel, 120, 80, None)

    full_panel_subject = Rect(x=0, y=0, width=240, height=240)
    with pytest.raises(ValueError, match="No clear space remains"):
        calculate_safe_bubble_placement(panel, 120, 80, full_panel_subject)


def test_safe_placement_avoids_existing_bubble_obstacles():
    panel = Rect(x=0, y=0, width=500, height=800)
    subject = Rect(x=170, y=230, width=160, height=300)
    obstacle = Rect(x=130, y=120, width=240, height=100)
    position, _tail = calculate_safe_bubble_placement(panel, 220, 90, subject, obstacles=[obstacle])
    candidate = Rect(x=position.x, y=position.y, width=220, height=90)
    assert candidate.x >= obstacle.right or candidate.right <= obstacle.x or candidate.y >= obstacle.bottom or candidate.bottom <= obstacle.y
    assert candidate.x >= subject.right or candidate.right <= subject.x or candidate.y >= subject.bottom or candidate.bottom <= subject.y


def test_safe_bubble_placement_above_character():
    """When character is positioned in the lower-half of panel, bubble MUST be placed ABOVE."""
    panel_rect = Rect(x=50, y=50, width=400, height=600)
    # Character starts at y=250, so headroom = 200px (plenty for 100px bubble)
    char_bounds = Rect(x=120, y=250, width=160, height=300)
    bubble_w, bubble_h = 200.0, 90.0

    pos, tail = calculate_safe_bubble_placement(panel_rect, bubble_w, bubble_h, char_bounds)

    # Bubble must be strictly ABOVE character top edge
    assert pos.y + bubble_h <= char_bounds.y + 5.0
    assert pos.y >= panel_rect.y
    # Tail must point downwards towards character's head
    assert tail.y >= pos.y + bubble_h
    assert tail.y <= char_bounds.bottom


def test_safe_bubble_placement_under_character():
    """When character is positioned near the top of panel, bubble MUST be placed UNDER."""
    panel_rect = Rect(x=50, y=50, width=400, height=600)
    # Character starts at y=60 (almost top of panel, no headroom)
    char_bounds = Rect(x=120, y=60, width=160, height=280)
    bubble_w, bubble_h = 200.0, 90.0

    pos, tail = calculate_safe_bubble_placement(panel_rect, bubble_w, bubble_h, char_bounds)

    # Bubble must be placed UNDER character bottom edge
    assert pos.y >= char_bounds.bottom - 5.0
    assert pos.y + bubble_h <= panel_rect.bottom + 5.0
    # Tail must point upwards towards character
    assert tail.y <= pos.y + 15.0


def test_safe_bubble_placement_flank_when_tall_character():
    """When character fills full vertical height but sits on the left side, bubble places on the right flank."""
    panel_rect = Rect(x=50, y=50, width=500, height=500)
    # Character fills vertical height, but only left 150px
    char_bounds = Rect(x=60, y=55, width=150, height=480)
    bubble_w, bubble_h = 200.0, 100.0

    pos, tail = calculate_safe_bubble_placement(panel_rect, bubble_w, bubble_h, char_bounds)

    # Bubble must be placed to the RIGHT of character
    assert pos.x >= char_bounds.right - 5.0
    assert pos.x + bubble_w <= panel_rect.right + 5.0


def test_agent_safe_bubble_placement_uses_clear_flank_when_top_and_bottom_are_blocked():
    panel_rect = Rect(x=50, y=50, width=500, height=500)
    char_bounds = Rect(x=60, y=55, width=150, height=480)

    pos, tail = calculate_safe_bubble_placement(panel_rect, 200, 100, char_bounds)
    assert pos.x >= char_bounds.right
    # Tail must terminate outside the character silhouette to avoid piercing the face (AUDIT-BUB-03 / Phase 5)
    is_outside = (
        tail.x < char_bounds.x
        or tail.x > char_bounds.right
        or tail.y < char_bounds.y
        or tail.y > char_bounds.bottom
    )
    assert is_outside, f"Tail {tail} pierced character bounds {char_bounds}"
    # Tail must point towards the speaker within reasonable proximity for attribution
    assert abs(tail.x - char_bounds.right) <= 30.0
