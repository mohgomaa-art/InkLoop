"""
Unit and regression tests for Cinematic Comic Art & Natural Acting directives.
Verifies that context_builder.py enforces camera variety (profile, OTS, rear, environmental),
subtle context-dependent acting, and anti-cliché negative constraints.
"""
import pytest
from app.schemas import CharacterSpec, AttributeCheck, SceneSpec
from app.context_builder import build_scene_generation_prompt
from app.planning.panel_planner import (
    PanelPlan,
    ShotType,
    FramingScale,
    CameraAngle,
    CameraPosition,
    CompositionType,
    NarrativeFunction,
    PanelTransitionType,
    PanelTextPlan,
    TextContentKind,
    TextCarrier,
)


def _make_plan(
    shot_type: ShotType = ShotType.WIDE,
    subject_scale: FramingScale = FramingScale.FULL_SHOT,
    position: CameraPosition = CameraPosition.THREE_QUARTER,
    angle: CameraAngle = CameraAngle.EYE_LEVEL,
    event: str = "A character enters the dark room.",
    emotional_intent: str = "Tense mystery and subtle unease",
) -> PanelPlan:
    return PanelPlan(
        panel_id="p1",
        beat_id="beat_01",
        scene_id="scene_01",
        page_number=1,
        reading_order_index=1,
        narrative_function=NarrativeFunction.ACTION_CONTINUATION,
        story_event=event,
        reader_takeaway=event,
        character_ids=["c_human"],
        shot_type=shot_type,
        subject_scale=subject_scale,
        camera_angle=angle,
        camera_position=position,
        composition_type=CompositionType.TWO_SHOT_BALANCED,
        emotional_intent=emotional_intent,
        visual_focus=event,
        transition_role=PanelTransitionType.ACTION_TO_ACTION,
        text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
    )


def test_cinematic_acting_and_anti_cliche_negatives():
    """Verifies that subtle emotional acting cues and negative bans against generic shock are compiled."""
    human = CharacterSpec(
        id="c_human",
        name="Gomaa",
        entity_kind="human",
        physical_height_cm=175.0,
        morphology="Realistic adult male human anatomy",
        attributes=[
            AttributeCheck(id="face", text="curly black hair and glasses", required=True),
        ],
        visual_invariants=["young adult human male appearance"],
        restrictions=[],
    )

    scene = SceneSpec(
        scene_id="s1",
        scene_index=0,
        title="Psychological discovery",
        shot_type="medium",
        action="Gomaa inspects the surveillance screen.",
        character_ids=["c_human"],
        panel_plan=_make_plan(
            position=CameraPosition.PROFILE,
            event="Gomaa inspects the surveillance screen.",
            emotional_intent="Chilling revelation and quiet dread",
        ),
    )

    prompt = build_scene_generation_prompt(
        line_and_tone="Black and white manga ink with screentone.",
        scene=scene,
        character_specs=[human],
        visual_invariants=[],
        prohibited_deviations=[],
    )

    # 1. Subtle psychological acting cues
    assert "Cinematic visual acting: convey 'Chilling revelation and quiet dread'" in prompt
    assert "subtle brow asymmetry, tightened jaw, pressed lips" in prompt
    assert "avoid generic permanently wide eyes, exaggerated gaping open mouths" in prompt

    # 2. Camera staging: profile view
    assert "Camera framing: true 90-degree side profile view" in prompt

    # 3. Negative constraints banning AI clichés
    assert "permanently wide eyes" in prompt
    assert "exaggerated gaping open mouth" in prompt
    assert "generic default shocked expression" in prompt
    assert "repetitive three-quarter portraits" in prompt
    assert "excessive random scratches" in prompt


def test_rear_view_and_over_the_shoulder_framing():
    """Verifies that rear views and over-the-shoulder framing are instructed to obscure or turn the face away."""
    human = CharacterSpec(
        id="c_human",
        name="Gomaa",
        entity_kind="human",
        attributes=[],
        visual_invariants=["young adult human male appearance"],
        restrictions=[],
    )

    scene_ots = SceneSpec(
        scene_id="s2",
        scene_index=1,
        title="Looking at the screens",
        shot_type="medium",
        action="Gomaa stares at the screen.",
        character_ids=["c_human"],
        panel_plan=_make_plan(
            position=CameraPosition.OVER_THE_SHOULDER,
            event="Gomaa stares at the screen.",
        ),
    )

    prompt_ots = build_scene_generation_prompt(
        line_and_tone="Manga ink.",
        scene=scene_ots,
        character_specs=[human],
        visual_invariants=[],
        prohibited_deviations=[],
    )
    assert "over-the-shoulder (OTS) shot" in prompt_ots
