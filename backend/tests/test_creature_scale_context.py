"""
Unit & regression tests for universal character-scale preservation and morphology propagation.
Verifies that context_builder.py dynamically compiles character scale, proportion targets,
and solo/multi-character grounding without character-name hardcoding.
"""
import pytest
from app.schemas import CharacterSpec, AttributeCheck, SceneSpec
from app.project.canon import CharacterDefinition
from app.context_builder import (
    _normalize_character_spec,
    _compile_scale_directives,
    build_scene_generation_prompt,
)
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


def _make_dummy_panel_plan(
    panel_id: str = "p1",
    shot_type: ShotType = ShotType.WIDE,
    subject_scale: FramingScale = FramingScale.FULL_SHOT,
    event: str = "A character stands in the room.",
) -> PanelPlan:
    return PanelPlan(
        panel_id=panel_id,
        beat_id="beat_01",
        scene_id="scene_01",
        page_number=1,
        reading_order_index=1,
        narrative_function=NarrativeFunction.ACTION_CONTINUATION,
        story_event=event,
        reader_takeaway=event,
        character_ids=["c1"],
        shot_type=shot_type,
        subject_scale=subject_scale,
        camera_angle=CameraAngle.EYE_LEVEL,
        camera_position=CameraPosition.THREE_QUARTER,
        composition_type=CompositionType.TWO_SHOT_BALANCED,
        emotional_intent="Neutral progression",
        visual_focus=event,
        transition_role=PanelTransitionType.ACTION_TO_ACTION,
        text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
    )


def test_character_spec_normalization_and_morphology_propagation():
    """Verifies that structured morphology, height, and proportions normalize cleanly from Canon & dicts."""
    char_dict = {
        "character_id": "test_creature_1",
        "name": "Bloop",
        "entity_kind": "creature",
        "physical_height_cm": 25.0,
        "proportion_constraints": {
            "head_ratio": 0.60,
            "body_ratio": 0.40,
            "description": "chibi mascot design: oversized spherical head",
        },
        "morphology": "Chibi mascot body plan: large spherical head (60%), tiny body (40%).",
        "attributes": [
            {"id": "attr_1", "text": "white fluffy fur", "required": True}
        ],
        "visual_invariants": ["black dot eyes"],
        "restrictions": ["no human proportions"],
    }

    spec = _normalize_character_spec(char_dict, "test_creature_1")
    assert spec.id == "test_creature_1"
    assert spec.name == "Bloop"
    assert spec.entity_kind == "creature"
    assert spec.physical_height_cm == 25.0
    assert spec.proportion_constraints == char_dict["proportion_constraints"]
    assert "Chibi mascot" in spec.morphology

    # Canon definition conversion
    canon_def = CharacterDefinition(
        character_id="test_creature_2",
        name="Sprout",
        entity_kind="miniature creature",
        physical_height_cm=30.0,
        proportion_constraints={"head_ratio": 0.55, "body_ratio": 0.45},
        morphology="Small plant-like creature with bulbous head.",
        attributes=[AttributeCheck(id="c_leaf", text="leaf on head", required=True)],
        visual_invariants=["green hue"],
        restrictions=["no flowers"],
    )
    spec_from_canon = canon_def.to_character_spec()
    assert spec_from_canon.physical_height_cm == 30.0
    assert spec_from_canon.proportion_constraints["head_ratio"] == 0.55
    assert "plant-like" in spec_from_canon.morphology


def test_multi_character_relative_scale_directives_dynamic_ratio():
    """Verifies dynamic relative scale calculation between a small creature and a human without hardcoding."""
    creature = CharacterSpec(
        id="c_small",
        name="Pip",
        entity_kind="creature",
        physical_height_cm=25.0,
        attributes=[],
    )
    human = CharacterSpec(
        id="c_tall",
        name="Tariq",
        entity_kind="human",
        physical_height_cm=175.0,
        attributes=[],
    )

    directives = _compile_scale_directives([creature, human])
    assert len(directives) == 2
    d = directives[0]
    # Ratio 175 / 25 = 7.0 -> 1:7
    assert "1:7" in d
    assert "Pip (height: 25 cm)" in d
    assert "Tariq (height: 175 cm)" in d
    assert "lower shin or ankle height" in d
    assert "Tariq visibly towers over Pip" in d
    assert "Style separation" in directives[1]


def test_multi_character_scale_with_unsized_human():
    """Verifies that an unsized human is treated as a standard human benchmark against a sized small creature."""
    creature = CharacterSpec(
        id="c_small",
        name="Pip",
        entity_kind="creature",
        physical_height_cm=25.0,
        attributes=[],
    )
    human_unsized = CharacterSpec(
        id="c_human",
        name="Gomaa",
        entity_kind="unspecified being",
        physical_height_cm=None,
        visual_invariants=["young adult human male appearance with light-medium skin"],
        attributes=[],
    )

    directives = _compile_scale_directives([creature, human_unsized])
    assert len(directives) == 2
    d = directives[0]
    assert "1:7 scale against an adult human (Gomaa)" in d
    assert "Pip (height: 25 cm)" in d
    assert "lower shin or ankle height" in d
    assert "Style separation" in directives[1]


def test_multi_character_scale_no_dimensions_invented():
    """Verifies that two characters without explicit measurements generate NO scale directives."""
    h1 = CharacterSpec(
        id="c_h1",
        name="Nour",
        entity_kind="human",
        physical_height_cm=None,
        attributes=[],
    )
    h2 = CharacterSpec(
        id="c_h2",
        name="Clara",
        entity_kind="human",
        physical_height_cm=None,
        attributes=[],
    )

    directives = _compile_scale_directives([h1, h2])
    assert len(directives) == 0


def test_solo_creature_environmental_scale_grounding():
    """Verifies that solo miniature creatures receive environmental scale grounding in wide/full shots."""
    creature = CharacterSpec(
        id="c_creature",
        name="Muse",
        entity_kind="creature",
        physical_height_cm=25.0,
        attributes=[],
    )
    plan_full = _make_dummy_panel_plan(shot_type=ShotType.WIDE, subject_scale=FramingScale.FULL_SHOT)

    directives = _compile_scale_directives([creature], panel_plan=plan_full)
    assert len(directives) == 1
    d = directives[0]
    assert "Environmental scale grounding for solo miniature subject" in d
    assert "Muse is strictly 25 cm tall" in d
    assert "diminutive relative to surrounding environmental features" in d
    assert "full_shot" in d or "wide" in d


def test_solo_human_does_not_receive_miniature_grounding():
    """Verifies that solo adult humans do NOT receive miniature scale grounding."""
    human = CharacterSpec(
        id="c_human",
        name="Gomaa",
        entity_kind="human",
        physical_height_cm=None,
        attributes=[],
    )
    plan_full = _make_dummy_panel_plan(shot_type=ShotType.WIDE, subject_scale=FramingScale.FULL_SHOT)

    directives = _compile_scale_directives([human], panel_plan=plan_full)
    assert len(directives) == 0


def test_solo_creature_close_up_no_environmental_grounding():
    """Verifies that macro or close-up framing does NOT receive wide floor grounding."""
    creature = CharacterSpec(
        id="c_creature",
        name="Muse",
        entity_kind="creature",
        physical_height_cm=25.0,
        attributes=[],
    )
    plan_cu = _make_dummy_panel_plan(shot_type=ShotType.CLOSE_UP, subject_scale=FramingScale.CLOSE_UP)

    directives = _compile_scale_directives([creature], panel_plan=plan_cu)
    assert len(directives) == 0


def test_universal_giant_creature_scale():
    """Verifies universal scaling handles giant non-human creatures (e.g. 300 cm titan)."""
    titan = CharacterSpec(
        id="c_titan",
        name="Goliath",
        entity_kind="monster",
        physical_height_cm=300.0,
        attributes=[],
    )
    human = CharacterSpec(
        id="c_scout",
        name="Scout",
        entity_kind="human",
        physical_height_cm=150.0,
        attributes=[],
    )

    directives = _compile_scale_directives([titan, human])
    assert len(directives) == 1
    d = directives[0]
    assert "Scale relationship: Scout (height: 150 cm) stands at approximately 1:2 the height of Goliath (height: 300 cm)" in d
    assert "waist or hip height" in d
    assert "Goliath visibly towers over Scout" in d


def test_build_scene_generation_prompt_incorporates_morphology_and_proportions():
    """Verifies that build_scene_generation_prompt embeds morphology, proportion targets, and height."""
    char = CharacterSpec(
        id="c_mascot",
        name="Koko",
        entity_kind="mascot creature",
        physical_height_cm=25.0,
        proportion_constraints={"head_ratio": 0.60, "body_ratio": 0.40},
        morphology="Chibi body plan with oversized spherical head.",
        attributes=[
            AttributeCheck(id="eyes", text="black dot eyes", required=True),
        ],
        visual_invariants=["fluffy fur"],
        restrictions=["no long legs"],
    )

    scene = SceneSpec(
        scene_id="s1",
        scene_index=0,
        title="Solo mascot introduction",
        shot_type="wide",
        action="Koko waves warmly.",
        character_ids=["c_mascot"],
        panel_plan=_make_dummy_panel_plan(event="Koko waves warmly."),
    )

    prompt = build_scene_generation_prompt(
        line_and_tone="Clean line art with screentone.",
        scene=scene,
        character_specs=[char],
        visual_invariants=[],
        prohibited_deviations=[],
    )

    assert "body morphology: Chibi body plan with oversized spherical head." in prompt
    assert "proportional balance: 60% head to 40% body ratio matching canonical reference" in prompt
    assert "Reference fidelity: Anatomy, silhouette, body proportions, and visual features must strictly follow the canonical reference image without stylization" in prompt
    assert "physical height: strictly 25 cm tall" in prompt
    assert "Environmental scale grounding for solo miniature subject" in prompt


def test_human_adult_proportions_and_anti_caricature_guard_in_full_shot():
    """Verifies that human characters in full/wide shots receive authentic 7.5-8 head proportions and anti-dwarf guards."""
    human = CharacterSpec(
        id="c_human",
        name="Gomaa",
        entity_kind="human",
        physical_height_cm=175.0,
        morphology="Authentic adult male human anatomy: natural 7.5 to 8 head-to-body proportion, slender natural neck, long legs",
        attributes=[
            AttributeCheck(id="face", text="curly black hair and glasses", required=True),
        ],
        visual_invariants=["young adult human male appearance"],
        restrictions=["no caricature distortion"],
    )
    creature = CharacterSpec(
        id="c_creature",
        name="Muse",
        entity_kind="creature",
        physical_height_cm=25.0,
        morphology="Plush creature body plan",
        attributes=[],
        visual_invariants=["fluffy fur"],
        restrictions=[],
    )

    scene = SceneSpec(
        scene_id="s_walk",
        scene_index=5,
        title="Walking together",
        shot_type="wide",
        action="Gomaa and Muse walk together.",
        character_ids=["c_human", "c_creature"],
        panel_plan=_make_dummy_panel_plan(
            shot_type=ShotType.WIDE,
            subject_scale=FramingScale.FULL_SHOT,
            event="Gomaa and Muse walk together.",
        ),
    )

    prompt = build_scene_generation_prompt(
        line_and_tone="Hand-painted digital gouache.",
        scene=scene,
        character_specs=[human, creature],
        visual_invariants=[],
        prohibited_deviations=[],
    )

    # Human proportion & anatomy invariants
    assert "7.5 to 8 head-to-body proportion" in prompt or "strictly 7.5 to 8 heads tall" in prompt
    assert "slender natural neck" in prompt
    assert "elongated legs" in prompt
    assert "strictly zero oversized head, zero compressed torso, and zero squat or dwarf distortion" in prompt
    # Negative anti-dwarf / anti-caricature rules
    assert "squat body" in prompt
    assert "caricature proportions" in prompt
    assert "chibi or dwarf anatomy" in prompt
