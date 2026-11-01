from pathlib import Path
import pytest

from app.agent.production import load_relevant_workflow_skills
from app.agent.registry import CapabilityRegistry
from app.context_builder import build_scene_generation_prompt
from app.schemas import CharacterSpec, AttributeCheck, SceneSpec
from app.planning.panel_planner import PanelPlan, NarrativeFunction, ShotType, FramingScale, CameraAngle, CameraPosition, CompositionType, PanelTextPlan, TextContentKind, TextCarrier
from app.verification.performance_verifier import (
    CharacterPerformanceEvaluator,
    PerformanceVerdict,
    PerformanceQualityAssessment,
)


SKILLS_DIR = Path(__file__).parents[1] / "app" / "agent" / "skills"
PERF_SKILL_DIR = SKILLS_DIR / "natural-character-performance"


def test_natural_character_performance_skill_files_and_references_exist():
    skill_file = PERF_SKILL_DIR / "SKILL.md"
    assert skill_file.is_file(), "natural-character-performance/SKILL.md must exist."
    content = skill_file.read_text(encoding="utf-8")
    assert "name: natural-character-performance" in content
    assert "# Natural Character Performance" in content
    assert "generation.generate_image" in content

    refs_dir = PERF_SKILL_DIR / "references"
    assert refs_dir.is_dir(), "natural-character-performance/references/ directory must exist."
    for expected_ref in (
        "eye_gaze_direction.md",
        "facial_expression_mechanics.md",
        "body_language_staging.md",
        "meta_muse_prompting.md",
        "performance_verification.md",
    ):
        ref_path = refs_dir / expected_ref
        assert ref_path.is_file(), f"Reference file {expected_ref} must exist."
        ref_text = ref_path.read_text(encoding="utf-8")
        assert len(ref_text) > 300, f"Reference file {expected_ref} must have substantive content."


def test_natural_character_performance_skill_triggers():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}

    queries = [
        "How do I prevent crossed eyes and fix character eye gaze in image generation?",
        "Improve character acting and facial expression subtlety for this close-up.",
        "Ensure body language and posture match the character's emotion.",
        "Generate natural performance without vacant stares or frozen grins.",
    ]
    for q in queries:
        result = load_relevant_workflow_skills(q, callable_ids)
        assert "# Natural Character Performance" in result, f"Query '{q}' should trigger natural-character-performance."


def test_natural_character_performance_skill_does_not_trigger_on_unrelated_queries():
    registry = CapabilityRegistry()
    callable_ids = {tool.tool_id for tool in registry.list_tools(callable_only=True)}

    unrelated_queries = [
        "How do I place bubbles in the top corner of the canvas?",
        "Outline a 4-act plot structure for a thriller.",
        "Reshape panel 3 to a diagonal cut.",
    ]
    for q in unrelated_queries:
        result = load_relevant_workflow_skills(q, callable_ids)
        assert "# Natural Character Performance" not in result, f"Query '{q}' should NOT trigger natural-character-performance."


def test_context_builder_incorporates_performance_and_optical_alignment():
    char = CharacterSpec(
        id="char_gomaa",
        name="Gomaa",
        attributes=[
            AttributeCheck(id="hair", text="black curly hair", required=True),
            AttributeCheck(id="glasses", text="dark tortoiseshell glasses", required=True),
        ],
        visual_invariants=["freckles across nose bridge", "dark ribbed turtleneck"],
    )
    plan = PanelPlan(
        panel_id="p1",
        beat_id="b1",
        scene_id="s1",
        reading_order_index=1,
        narrative_function=NarrativeFunction.REVEAL,
        story_event="Gomaa discovers a hidden optical lens inside the lantern housing.",
        reader_takeaway="A miniature lens is concealed within the mechanism.",
        character_ids=["char_gomaa"],
        environment="workshop table under warm tungsten lamp",
        shot_type=ShotType.CLOSE_UP,
        subject_scale=FramingScale.CLOSE_UP,
        camera_angle=CameraAngle.HIGH_ANGLE,
        camera_position=CameraPosition.THREE_QUARTER,
        composition_type=CompositionType.OFF_CENTER_REVEAL,
        emotional_intent="subtle, intense curiosity with quiet wonder",
        visual_focus="the brass lens held between tweezers",
        text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
    )
    scene = SceneSpec(
        scene_id="s1",
        scene_index=0,
        title="Lens Discovery",
        shot_type="close_up",
        action=plan.story_event,
        character_ids=["char_gomaa"],
        panel_plan=plan,
    )

    prompt = build_scene_generation_prompt(
        line_and_tone="Clean inked line art with fine screentone shading",
        scene=scene,
        character_specs=[char],
        visual_invariants=["black curly hair", "dark tortoiseshell glasses"],
        prohibited_deviations=["formal ties"],
    )

    # 1. Performance and emotional acting cue
    assert "subtle, intense curiosity with quiet wonder" in prompt
    assert "natural restraint" in prompt

    # 2. Optical alignment & gaze target
    assert "the brass lens held between tweezers" in prompt
    assert "converge accurately" in prompt

    # 3. Posture-face congruence
    assert "Posture-face congruence" in prompt

    # 4. Anti-defect negative quality guards
    assert "crossed eyes" in prompt
    assert "divergent pupils" in prompt
    assert "wandering gaze" in prompt
    assert "blank stare" in prompt


def test_character_performance_evaluator_verdicts():
    evaluator = CharacterPerformanceEvaluator()

    # 1. Complete Pass
    assessment_pass = evaluator.evaluate(b"fake_image_bytes", is_simulated=True)
    assert assessment_pass.verdict == PerformanceVerdict.PASS
    assert assessment_pass.overall_score >= 0.80
    assert len(assessment_pass.discrepancies) == 0

    # 2. Critical Eye Alignment Failure -> FAIL
    assessment_fail_eye = evaluator.evaluate(
        b"fake_image_bytes",
        is_simulated=True,
        evaluation_overrides={"eye_alignment_pass": False},
    )
    assert assessment_fail_eye.verdict == PerformanceVerdict.FAIL
    assert any("misalignment" in d for d in assessment_fail_eye.discrepancies)

    # 3. Minor Discrepancy -> NEEDS_REVIEW
    assessment_review = evaluator.evaluate(
        b"fake_image_bytes",
        is_simulated=True,
        evaluation_overrides={"style_pass": False},
    )
    assert assessment_review.verdict == PerformanceVerdict.NEEDS_REVIEW
    assert any("Style deviation" in d for d in assessment_review.discrepancies)

    # 4. Not Run
    assessment_not_run = evaluator.evaluate(None, is_simulated=False)
    assert assessment_not_run.verdict == PerformanceVerdict.NOT_RUN


def test_eight_expression_character_performance_benchmark():
    """
    Evaluates 8 distinct character performance scenarios:
    1. Neutral attentive expression
    2. Focused gaze toward an object
    3. Looking toward another character
    4. Subtle concern
    5. Restrained happiness
    6. Natural surprise
    7. Different head orientations (profile / three-quarters)
    8. Non-human creature (Muse) with non-human anatomical visual language
    """
    evaluator = CharacterPerformanceEvaluator()

    scenarios = [
        {"name": "neutral_attentive", "focus": "listening to instructions", "emotion": "calm, attentive focus"},
        {"name": "focused_gaze", "focus": "soldering iron tip", "emotion": "deep mechanical concentration"},
        {"name": "peer_gaze", "focus": "companion character across the table", "emotion": "warm, direct engagement"},
        {"name": "subtle_concern", "focus": "flickering lantern filament", "emotion": "quiet worry and alert caution"},
        {"name": "restrained_happiness", "focus": "repaired clockwork mechanism", "emotion": "soft, earned relief with subtle smile"},
        {"name": "natural_surprise", "focus": "sudden glowing light map", "emotion": "breathless awe with slightly parted lips"},
        {"name": "profile_orientation", "focus": "distant skyline", "emotion": "pensive contemplation in sharp silhouette"},
        {"name": "non_human_creature", "focus": "glowing paper star", "emotion": "curious head tilt and peaceful contentment"},
    ]

    for scenario in scenarios:
        plan = PanelPlan(
            panel_id="p_bench",
            beat_id="b_bench",
            scene_id="s_bench",
            reading_order_index=1,
            narrative_function=NarrativeFunction.ACTION_CONTINUATION,
            story_event=f"Character acts with {scenario['emotion']}",
            reader_takeaway=scenario['emotion'],
            character_ids=["char_gomaa"] if scenario["name"] != "non_human_creature" else ["char_muse"],
            environment="benchmarking studio",
            shot_type=ShotType.CLOSE_UP,
            subject_scale=FramingScale.CLOSE_UP,
            camera_angle=CameraAngle.EYE_LEVEL,
            camera_position=CameraPosition.THREE_QUARTER if scenario["name"] != "profile_orientation" else CameraPosition.PROFILE,
            composition_type=CompositionType.CENTERED,
            emotional_intent=scenario["emotion"],
            visual_focus=scenario["focus"],
            text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
        )

        assessment = evaluator.evaluate(b"benchmark_pixels", panel_plan=plan, is_simulated=True)
        assert assessment.verdict == PerformanceVerdict.PASS, f"Scenario {scenario['name']} should pass evaluation."
        assert assessment.overall_score >= 0.85
        assert assessment.dimensions["gaze_coherence"].passed is True
        assert assessment.dimensions["emotional_restraint"].passed is True
