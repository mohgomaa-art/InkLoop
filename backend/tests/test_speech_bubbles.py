"""
Unit tests for InkLoop Expressive Speech Bubble Engine & Story Stylist.
Verifies mathematical geometry, tail solvers, degenerate bounds invariants,
and autonomous story-to-bubble routing.
"""
import pytest
from app.contracts.geometry import Rect, Point
from app.contracts.engine import SpeechBubbleParams
from app.canvas.bubble_models import BubbleShape, TailType, BubbleAccent
from app.canvas.bubble_stylist import recommend_bubble_style
from app.canvas.speech_bubble import SpeechBubbleEngine


def test_bubble_stylist_routing():
    """Verifies that story context routes to the correct expressive bubble."""
    # 1. Thought
    rec = recommend_bubble_style(emotional_intent="Deep thought and contemplation", carrier="thought_bubble")
    assert rec.shape == BubbleShape.THOUGHT_CLOUD
    assert rec.tail_type == TailType.BUBBLE_CHAIN

    # 2. Whisper
    rec = recommend_bubble_style(emotional_intent="A quiet secret", delivery="whisper")
    assert rec.shape == BubbleShape.WHISPER_CLOUD_SOFT
    assert rec.tail_type == TailType.WHISPER_DASHED
    assert "5 4" in rec.stroke_dash

    # 3. Shout
    rec = recommend_bubble_style(emotional_intent="Furious shout", delivery="shout")
    assert rec.shape == BubbleShape.SHOUT_BURST
    assert rec.tail_type == TailType.LIGHTNING_BOLT
    assert rec.halftone_shadow is True

    # 4. Energy Blast / Superpower
    rec = recommend_bubble_style(emotional_intent="Unleashing divine power and energy blast", sfx_category="energy")
    assert rec.shape == BubbleShape.EXPLOSIVE_BLAST
    assert rec.tail_type == TailType.LIGHTNING_BOLT
    assert rec.accent == BubbleAccent.SPEEDLINE_NEEDLES

    # 5. Fear / Shivering
    rec = recommend_bubble_style(emotional_intent="Trembling with terrifying fear")
    assert rec.shape == BubbleShape.FEAR_TREMBLE
    assert rec.accent == BubbleAccent.SWEAT_DROP


def test_bubble_style_uses_story_event_and_dialogue_delivery_cues():
    shout = recommend_bubble_style(
        emotional_intent="urgent alarm",
        story_event="A character shouts during a battle strike.",
        dialogue_text="WATCH OUT!!",
        carrier="speech_bubble",
    )
    whisper = recommend_bubble_style(
        emotional_intent="secretive",
        story_event="Muse whispers while hiding from the guards.",
        dialogue_text="Stay here...",
        carrier="speech_bubble",
    )
    fear = recommend_bubble_style(
        emotional_intent="nervous and afraid",
        story_event="The creature trembles.",
        dialogue_text="P-please wait",
        carrier="speech_bubble",
    )
    calm = recommend_bubble_style(
        emotional_intent="calm reassurance",
        story_event="A nearby explosion happens, but the speaker stays calm.",
        dialogue_text="We are safe.",
        carrier="speech_bubble",
    )

    assert shout.shape == BubbleShape.SHOUT_BURST
    assert shout.tail_type == TailType.LIGHTNING_BOLT
    assert whisper.shape == BubbleShape.WHISPER_CLOUD_SOFT
    assert whisper.tail_type == TailType.WHISPER_DASHED
    assert fear.shape == BubbleShape.FEAR_TREMBLE
    assert calm.shape == BubbleShape.OVAL


def test_bubble_style_changes_with_story_emotion_and_action_context():
    curious = recommend_bubble_style(
        emotional_intent="curious wonder",
        narrative_function="dialogue",
        delivery="questioning",
        carrier="speech_bubble",
        action_context="the character notices a strange moving shadow",
    )
    shocked = recommend_bubble_style(
        emotional_intent="startled confusion",
        narrative_function="reaction",
        carrier="speech_bubble",
    )
    calm = recommend_bubble_style(
        emotional_intent="gentle hope",
        delivery="calm",
        carrier="speech_bubble",
    )
    whispered = recommend_bubble_style(
        carrier="speech_bubble",
        action_context="Muse whispers a warning under her breath",
    )
    assert curious.shape == BubbleShape.SCALLOPED_FLOWER
    assert shocked.shape == BubbleShape.SPLAT_SURPRISE
    assert calm.shape == BubbleShape.OVAL
    assert whispered.tail_type == TailType.WHISPER_DASHED
    assert len({curious.shape, shocked.shape, calm.shape}) == 3

    # 6. Affection / Love
    rec = recommend_bubble_style(emotional_intent="Sweet affection and blushing smile")
    assert rec.shape == BubbleShape.AFFECTION_HEART
    assert rec.accent == BubbleAccent.SPARKLES

    # 7. Slime / Disgust
    rec = recommend_bubble_style(emotional_intent="Gross sticky slime splat")
    assert rec.shape == BubbleShape.SPLAT_SURPRISE

    # 8. Comms / Robotic
    rec = recommend_bubble_style(emotional_intent="AI voice broadcast over intercom", delivery="robotic")
    assert rec.shape == BubbleShape.ELECTRIC_ROBOTIC
    assert rec.tail_type == TailType.LIGHTNING_BOLT

    # 9. Narration
    rec = recommend_bubble_style(emotional_intent="Dramatic time jump", carrier="narration_box")
    assert rec.shape in (BubbleShape.TILTED_BANNER, BubbleShape.ROUNDED_RECTANGLE)
    assert rec.tail_type == TailType.NONE

    # 10. Radio broadcast / Comms
    rec = recommend_bubble_style(emotional_intent="Radio comms from dispatch")
    assert rec.shape == BubbleShape.RADIO_BROADCAST_ZIGZAG
    assert rec.tail_type == TailType.ZIGZAG_ANTENNA
    assert rec.accent == BubbleAccent.ELECTRIC_SPARKS

    # 11. Dark Aura / Villain / Inverted mode
    rec = recommend_bubble_style(emotional_intent="Sinister cursed demon incantation")
    assert rec.shape == BubbleShape.DARK_AURA_GHOST
    assert rec.inverted_dark_mode is True
    assert rec.fill_color == "#111111"

    # 12. Icicle Frost
    rec = recommend_bubble_style(emotional_intent="Freezing cold murderous glare")
    assert rec.shape == BubbleShape.ICICLE_FROST

    # 13. Droplet Tear
    rec = recommend_bubble_style(emotional_intent="Weeping with grief and tears")
    assert rec.shape == BubbleShape.DROPLET_TEAR_SAD
    assert rec.accent == BubbleAccent.SWEAT_DROP


def test_speech_bubble_engine_all_shapes_geometry():
    """Verifies that all 11+ shapes produce valid, non-empty closed SVG paths without NaN."""
    engine = SpeechBubbleEngine()
    test_bounds = Rect(x=100.0, y=150.0, width=280.0, height=140.0)

    for shape in BubbleShape:
        if shape == BubbleShape.NONE:
            continue
        geo = engine.generate_vector_geometry(
            bounds=test_bounds,
            shape=shape,
            tail_type=TailType.SMOOTH_POINTER,
            tail_target=Point(x=150.0, y=360.0),
        )
        assert geo.bubble_path is not None
        assert len(geo.bubble_path) > 10
        assert "nan" not in geo.bubble_path.lower()
        assert "inf" not in geo.bubble_path.lower()
        assert geo.bubble_path.startswith("M ")
        assert geo.bubble_path.endswith("Z")
        assert geo.bounds.width >= 40.0
        assert geo.bounds.height >= 30.0


def test_organic_oval_is_stable_per_bubble_id_and_distinct_between_bubbles():
    engine = SpeechBubbleEngine()
    bounds = Rect(x=100.0, y=150.0, width=280.0, height=140.0)
    first = engine.generate_vector_geometry(bounds=bounds, shape=BubbleShape.OVAL, organic_seed="bubble_one")
    first_again = engine.generate_vector_geometry(bounds=bounds, shape=BubbleShape.OVAL, organic_seed="bubble_one")
    second = engine.generate_vector_geometry(bounds=bounds, shape=BubbleShape.OVAL, organic_seed="bubble_two")

    assert first.bubble_path == first_again.bubble_path
    assert first.bubble_path != second.bubble_path


def test_speech_bubble_engine_all_tail_types():
    """Verifies tail path generation across tail types."""
    engine = SpeechBubbleEngine()
    test_bounds = Rect(x=50.0, y=50.0, width=200.0, height=100.0)
    target = Point(x=120.0, y=220.0)

    # 1. Smooth Pointer
    geo_smooth = engine.generate_vector_geometry(bounds=test_bounds, tail_type=TailType.SMOOTH_POINTER, tail_target=target)
    assert geo_smooth.tail_path is not None
    assert "nan" not in geo_smooth.tail_path.lower()

    # 2. Lightning Bolt
    geo_lightning = engine.generate_vector_geometry(bounds=test_bounds, tail_type=TailType.LIGHTNING_BOLT, tail_target=target)
    assert geo_lightning.tail_path is not None
    assert "nan" not in geo_lightning.tail_path.lower()

    # 3. Bubble Chain
    geo_chain = engine.generate_vector_geometry(bounds=test_bounds, tail_type=TailType.BUBBLE_CHAIN, tail_target=target)
    assert len(geo_chain.tail_chain_circles) == 3
    for cx, cy, rad in geo_chain.tail_chain_circles:
        assert rad > 0
        assert 50.0 <= cx <= 200.0

    # 4. None
    geo_none = engine.generate_vector_geometry(bounds=test_bounds, tail_type=TailType.NONE)
    assert geo_none.tail_path is None

    # 5. Dual Pointer (Chorus)
    geo_dual = engine.generate_vector_geometry(bounds=test_bounds, tail_type=TailType.DUAL_POINTER, tail_target=target)
    assert geo_dual.tail_path is not None
    assert geo_dual.secondary_tail_path is not None

    # 6. Off Screen Pointer
    geo_offscreen = engine.generate_vector_geometry(bounds=test_bounds, tail_type=TailType.OFF_SCREEN_POINTER, tail_target=Point(x=-50.0, y=100.0))
    assert geo_offscreen.tail_path is not None

    # 7. Curved Hook
    geo_hook = engine.generate_vector_geometry(bounds=test_bounds, tail_type=TailType.CURVED_HOOK_TAIL, tail_target=target)
    assert geo_hook.tail_path is not None

    # 8. Zigzag Antenna
    geo_antenna = engine.generate_vector_geometry(bounds=test_bounds, tail_type=TailType.ZIGZAG_ANTENNA, tail_target=target)
    assert geo_antenna.tail_path is not None


def test_speech_bubble_complex_paths_and_accents():
    """Verifies 3D ribbon folds, double borders, and procedural manga accents."""
    engine = SpeechBubbleEngine()
    test_bounds = Rect(x=50.0, y=50.0, width=200.0, height=80.0)

    # 1. 3D Folded Ribbon has fold paths
    geo_ribbon = engine.generate_vector_geometry(bounds=test_bounds, shape=BubbleShape.FOLDED_RIBBON_3D)
    assert len(geo_ribbon.ribbon_fold_paths) >= 2

    # 2. Double border impact has inner stroke path
    geo_double = engine.generate_vector_geometry(bounds=test_bounds, shape=BubbleShape.DOUBLE_BORDER_IMPACT)
    assert geo_double.double_stroke_path is not None
    assert geo_double.double_stroke_path.startswith("M ")

    # 3. Accents
    for accent in (BubbleAccent.ANGER_VEIN_CROSS, BubbleAccent.SHOCK_MARKS, BubbleAccent.HEART_FLUTTER, BubbleAccent.ELECTRIC_SPARKS, BubbleAccent.DIZZINESS_SWIRL):
        geo_accent = engine.generate_vector_geometry(bounds=test_bounds, shape=BubbleShape.OVAL, accent=accent)
        assert len(geo_accent.accent_paths) >= 1
        for p in geo_accent.accent_paths:
            assert "nan" not in p.lower()
            assert p.startswith("M ")


def test_speech_bubble_engine_defensive_clamp():
    """Invariants: very small bounds must clamp cleanly up to minimum readable sizes."""
    engine = SpeechBubbleEngine()
    small_bounds = Rect(x=0.0, y=0.0, width=5.0, height=5.0)
    geo = engine.generate_vector_geometry(bounds=small_bounds, shape=BubbleShape.OVAL)
    assert geo.bounds.width >= 40.0
    assert geo.bounds.height >= 30.0
    assert "nan" not in geo.bubble_path.lower()


def test_speech_bubble_place_bubble():
    """Verifies end-to-end placement and raster generation."""
    engine = SpeechBubbleEngine()
    params = SpeechBubbleParams(
        text_block_artifact_id="text_123",
        lettering_layer_artifact_id="layer_456",
        measured_text_bounds=Rect(x=0.0, y=0.0, width=150.0, height=40.0),
        panel_slot_rect=Rect(x=20.0, y=20.0, width=400.0, height=500.0),
        bubble_shape="shout_burst",
        tail_target=Point(x=180.0, y=420.0),
    )
    output = engine.place_speech_bubble(params)
    assert output.bubble_bounds.width > 150.0
    assert output.tail_anchor is not None
    assert output.bubble_layer_artifact_id.startswith("bubble_")


def test_bubble_api_endpoints():
    """Verifies REST endpoints for bubble style recommendation and geometry calculation."""
    from fastapi.testclient import TestClient
    from app.api.server import create_app

    client = TestClient(create_app())

    # 1. Recommendation endpoint
    res_rec = client.post(
        "/api/v1/canvas/bubbles/recommend",
        json={"emotional_intent": "Furious battle shout", "delivery": "shout"},
    )
    assert res_rec.status_code == 200
    data_rec = res_rec.json()
    assert data_rec["shape"] == "shout_burst"
    assert data_rec["tail_type"] == "lightning_bolt"
    assert data_rec["halftone_shadow"] is True

    # 2. Geometry calculation endpoint
    res_geo = client.post(
        "/api/v1/canvas/bubbles/geometry",
        json={
            "shape": "thought_cloud",
            "tail_type": "bubble_chain",
            "bounds": {"x": 50, "y": 50, "width": 200, "height": 100},
            "tail_target": {"x": 100, "y": 250},
        },
    )
    assert res_geo.status_code == 200
    data_geo = res_geo.json()
    assert "bubble_path" in data_geo
    assert len(data_geo["tail_chain_circles"]) == 3

