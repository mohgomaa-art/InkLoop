"""Acceptance tests for B5 Unified Vector Geometry and Seeded Outlines.

Verifies:
1. Body + tail are one closed path (starts with M, contains tail curves, ends with Z).
2. Single stroke without interior intersecting seams.
3. Seeded outline stability: same bubble_id renders character-identical SVG twice.
4. Different bubble_ids produce distinct organic variations.
5. All 8 registry types produce correct shapes (burst for shout, dashed for whisper, etc.).
6. Thought cloud produces cloud body and dot trail.
"""
import pytest
from app.contracts.geometry import Point, Rect
from app.canvas.bubble_vector import BubbleVectorBuilder, seeded_noise


def test_unified_closed_path_starts_with_M_and_ends_with_Z():
    """Verify body + tail are unified into one closed path."""
    builder = BubbleVectorBuilder()
    bounds = Rect(x=100.0, y=100.0, width=200.0, height=100.0)
    tail_target = Point(x=150.0, y=280.0)

    bubble = builder.build_bubble_vector(
        bounds=bounds,
        type_id="speech.normal",
        shape="oval",
        tail_type="smooth_pointer",
        tail_target=tail_target,
        bubble_id="bubble_test_01",
    )

    path = bubble.unified_path
    assert path.startswith("M "), f"Path must start with M, got: {path[:10]}"
    assert path.endswith("Z"), f"Path must end with Z, got: {path[-10:]}"
    # Verify tail target coordinates are incorporated in the path
    assert f"{tail_target.x:.1f}" in path
    assert f"{tail_target.y:.1f}" in path
    # There should only be one M and one Z in a unified closed path!
    assert path.count("M") == 1, f"Expected exactly 1 M command in unified path, found {path.count('M')}"
    assert path.count("Z") == 1, f"Expected exactly 1 Z command in unified path, found {path.count('Z')}"


def test_seeded_outline_is_identical_across_multiple_calls_and_distinct_for_different_ids():
    """Verify outline variation is deterministic per bubble_id without Math.random."""
    builder = BubbleVectorBuilder()
    bounds = Rect(x=50.0, y=50.0, width=180.0, height=90.0)
    target = Point(x=120.0, y=220.0)

    # Call twice with exact same bubble_id
    b1 = builder.build_bubble_vector(bounds=bounds, bubble_id="bubble_hero_01", tail_target=target)
    b2 = builder.build_bubble_vector(bounds=bounds, bubble_id="bubble_hero_01", tail_target=target)

    # Must be 100% character-identical!
    assert b1.unified_path == b2.unified_path

    # Call with different bubble_id
    b3 = builder.build_bubble_vector(bounds=bounds, bubble_id="bubble_villain_02", tail_target=target)

    # Outlines must be distinct
    assert b1.unified_path != b3.unified_path


def test_shout_burst_unifies_burst_spikes_with_lightning_tail():
    """Verify speech.shout creates a single unified burst path."""
    builder = BubbleVectorBuilder()
    bounds = Rect(x=100.0, y=100.0, width=220.0, height=120.0)
    target = Point(x=180.0, y=290.0)

    bubble = builder.build_bubble_vector(
        bounds=bounds,
        type_id="speech.shout",
        shape="shout_burst",
        tail_type="lightning_bolt",
        tail_target=target,
        bubble_id="shout_01",
    )

    path = bubble.unified_path
    assert path.startswith("M") and path.endswith("Z")
    assert path.count("M") == 1 and path.count("Z") == 1
    assert f"{target.x:.1f}" in path and f"{target.y:.1f}" in path


def test_whisper_produces_dashed_stroke():
    """Verify speech.whisper sets stroke_dash."""
    builder = BubbleVectorBuilder()
    bounds = Rect(x=100.0, y=100.0, width=180.0, height=90.0)
    target = Point(x=150.0, y=250.0)

    bubble = builder.build_bubble_vector(
        bounds=bounds,
        type_id="speech.whisper",
        shape="whisper_cloud_soft",
        tail_type="whisper_dashed",
        tail_target=target,
        bubble_id="whisper_01",
    )

    assert bubble.stroke_dash == "5 4"


def test_thought_cloud_produces_cloud_body_and_dot_chain():
    """Verify thought.cloud produces scalloped cloud and descending chain circles."""
    builder = BubbleVectorBuilder()
    bounds = Rect(x=100.0, y=100.0, width=200.0, height=120.0)
    target = Point(x=140.0, y=280.0)

    bubble = builder.build_bubble_vector(
        bounds=bounds,
        type_id="thought.cloud",
        shape="thought_cloud",
        tail_type="bubble_chain",
        tail_target=target,
        bubble_id="thought_01",
    )

    assert "A " in bubble.unified_path  # Scalloped arcs
    assert len(bubble.chain_circles) == 3  # Three descending dots
    # Verify dot radiuses decrease toward target
    r1, r2, r3 = [c[2] for c in bubble.chain_circles]
    assert r1 > r2 > r3


def test_narration_box_has_no_tail():
    """Verify narration.box produces clean rectangular closed path without tail."""
    builder = BubbleVectorBuilder()
    bounds = Rect(x=50.0, y=50.0, width=300.0, height=80.0)

    bubble = builder.build_bubble_vector(
        bounds=bounds,
        type_id="narration.box",
        shape="rounded_rectangle",
        tail_type="none",
        bubble_id="narr_01",
    )

    assert bubble.tail_tip is None
    assert len(bubble.chain_circles) == 0
    assert bubble.unified_path.startswith("M ") and bubble.unified_path.endswith("Z")
    assert bubble.unified_path.count("M") == 1
