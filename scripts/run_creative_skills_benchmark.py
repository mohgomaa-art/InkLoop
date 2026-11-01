"""
InkLoop Creative Skills Real-Generation Benchmark.
Executes controlled live generations comparing baseline vs skill-assisted prompts
using identical references, model, and seed configurations.
"""
from __future__ import annotations

import io
import json
import time
from pathlib import Path
from PIL import Image

from app.config import InkLoopConfig, PROJECT_ROOT
from app.image_adapter import MetaImageGenerationAdapter, GenerationRequest, ReferenceImagePayload
from app.context_builder import build_scene_generation_prompt
from app.schemas import CharacterSpec, AttributeCheck, SceneSpec
from app.planning.panel_planner import (
    PanelPlan, NarrativeFunction, ShotType, FramingScale, CameraAngle, CameraPosition, CompositionType, PanelTextPlan, TextContentKind, TextCarrier
)
from app.verification.performance_verifier import analyze_panel_pixels, CharacterPerformanceEvaluator, PerformanceVerdict


OUTPUT_DIR = PROJECT_ROOT / "runs" / "creative_skills_benchmark"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REF_IMAGE_PATH = PROJECT_ROOT / "runs" / "m0_visual" / "reference" / "nour_reference.png"


def run_benchmark():
    config = InkLoopConfig.load()
    adapter = MetaImageGenerationAdapter(config)
    evaluator = CharacterPerformanceEvaluator()

    ref_bytes = REF_IMAGE_PATH.read_bytes() if REF_IMAGE_PATH.exists() else None
    ref_payload = [
        ReferenceImagePayload(
            asset_id="ref_nour",
            image_bytes=ref_bytes,
            mime_type="image/png",
            role="character_reference",
            character_id="nour",
            weight=1.0,
            notes="Canonical Nour appearance anchor",
        )
    ] if ref_bytes else []

    nour_spec = CharacterSpec(
        id="nour",
        name="Nour",
        attributes=[
            AttributeCheck(id="glasses", text="round wireframe glasses", required=True),
            AttributeCheck(id="hair", text="dark curly hair", required=True),
            AttributeCheck(id="scarf", text="green knitted scarf", required=True),
        ],
        visual_invariants=["round wireframe glasses", "dark curly hair", "freckles across nose bridge", "green knitted scarf"],
        restrictions=["no formal suits", "no modern gadgets"],
    )

    style_rules = "Comic Book panel illustration, Black-and-White Manga Ink with Screentone, clean line art with fine screentone shading."

    benchmark_definitions = [
        {
            "id": "01_neutral_attentive",
            "name": "Neutral attentive expression",
            "baseline_prompt": (
                f"{style_rules} Nour standing in a workshop looking neutral and attentive. "
                "Character has dark curly hair, round wireframe glasses, green scarf, freckles. Artwork only."
            ),
            "plan": PanelPlan(
                panel_id="p1", beat_id="b1", scene_id="s1", reading_order_index=1,
                narrative_function=NarrativeFunction.ESTABLISHING,
                story_event="Nour pauses at the workshop entrance, listening attentively for approaching footsteps.",
                reader_takeaway="Nour is on guard and observant in the workshop.",
                character_ids=["nour"],
                environment="workshop doorway under dim hanging lantern",
                shot_type=ShotType.CLOSE_UP,
                subject_scale=FramingScale.MEDIUM_CLOSE_UP,
                camera_angle=CameraAngle.EYE_LEVEL,
                camera_position=CameraPosition.THREE_QUARTER,
                composition_type=CompositionType.CENTERED,
                emotional_intent="calm, alert attention with quiet readiness",
                visual_focus="the workshop doorway threshold",
                text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
            ),
            "action": "Nour pauses at the workshop entrance, listening attentively for approaching footsteps.",
        },
        {
            "id": "02_focused_gaze_object",
            "name": "Focused gaze toward an object",
            "baseline_prompt": (
                f"{style_rules} Nour looking at a small brass key on a workbench holding tweezers. "
                "Character has dark curly hair, round wireframe glasses, green scarf. Artwork only."
            ),
            "plan": PanelPlan(
                panel_id="p2", beat_id="b2", scene_id="s2", reading_order_index=1,
                narrative_function=NarrativeFunction.ACTION_CONTINUATION,
                story_event="Nour bends close over the workbench, holding tweezers to inspect the notched teeth of a miniature brass key.",
                reader_takeaway="Nour scrutinizes the intricate mechanism of the key.",
                character_ids=["nour"],
                environment="cluttered watchmaker workbench under directed magnifying lamp",
                shot_type=ShotType.CLOSE_UP,
                subject_scale=FramingScale.CLOSE_UP,
                camera_angle=CameraAngle.HIGH_ANGLE,
                camera_position=CameraPosition.THREE_QUARTER,
                composition_type=CompositionType.CENTERED,
                emotional_intent="deep mechanical concentration and intense focus",
                visual_focus="the notched teeth of the miniature brass key",
                text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
            ),
            "action": "Nour bends close over the workbench, inspecting the key with precision tweezers.",
        },
        {
            "id": "03_looking_toward_character",
            "name": "Looking toward another character",
            "baseline_prompt": (
                f"{style_rules} Nour sitting at a table talking to an elder craftsman across the table. "
                "Nour has dark curly hair, glasses, green scarf. Artwork only."
            ),
            "plan": PanelPlan(
                panel_id="p3", beat_id="b3", scene_id="s3", reading_order_index=1,
                narrative_function=NarrativeFunction.REACTION,
                story_event="Nour turns toward Master Tariq sitting across the low table, engaged in serious conversation.",
                reader_takeaway="Nour listens intently to Master Tariq's urgent warning.",
                character_ids=["nour"],
                environment="tea room corner with wooden table",
                shot_type=ShotType.MEDIUM,
                subject_scale=FramingScale.MEDIUM_SHOT,
                camera_angle=CameraAngle.EYE_LEVEL,
                camera_position=CameraPosition.OVER_THE_SHOULDER,
                composition_type=CompositionType.TWO_SHOT_BALANCED,
                emotional_intent="attentive, engaged respect and serious focus",
                visual_focus="the steaming ceramic teacups between them",
                text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
            ),
            "action": "Nour faces Master Tariq across the table, speaking and maintaining direct conversational eye contact.",
        },
        {
            "id": "04_subtle_concern",
            "name": "Subtle concern",
            "baseline_prompt": (
                f"{style_rules} Nour looking concerned and worried, noticing water seeping into the cellar. "
                "Character has dark curly hair, glasses, green scarf. Artwork only."
            ),
            "plan": PanelPlan(
                panel_id="p4", beat_id="b4", scene_id="s4", reading_order_index=1,
                narrative_function=NarrativeFunction.ACTION_PREPARATION,
                story_event="Nour freezes on the cellar steps, noticing dark water creeping beneath the door.",
                reader_takeaway="Nour realizes the lower chamber is flooding.",
                character_ids=["nour"],
                environment="stone cellar stairway with damp masonry walls",
                shot_type=ShotType.CLOSE_UP,
                subject_scale=FramingScale.MEDIUM_CLOSE_UP,
                camera_angle=CameraAngle.LOW_ANGLE,
                camera_position=CameraPosition.THREE_QUARTER,
                composition_type=CompositionType.OFF_CENTER_REVEAL,
                emotional_intent="subtle apprehension and guarded caution",
                visual_focus="dark water seeping under the doorframe",
                text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
            ),
            "action": "Nour stops mid-step, head lowered with eyes darting down to the rising water seam, shoulders tensed.",
        },
        {
            "id": "05_restrained_happiness",
            "name": "Restrained happiness",
            "baseline_prompt": (
                f"{style_rules} Nour smiling and happy seeing a green light flashing on the radio. "
                "Character has dark curly hair, round glasses, green scarf. Artwork only."
            ),
            "plan": PanelPlan(
                panel_id="p5", beat_id="b5", scene_id="s5", reading_order_index=1,
                narrative_function=NarrativeFunction.AFTERMATH,
                story_event="Nour sees the receiver bulb blink green, realizing the rescue frequency has been received.",
                reader_takeaway="The signal came through; they are saved.",
                character_ids=["nour"],
                environment="radio transceiver alcove in the attic",
                shot_type=ShotType.CLOSE_UP,
                subject_scale=FramingScale.CLOSE_UP,
                camera_angle=CameraAngle.EYE_LEVEL,
                camera_position=CameraPosition.THREE_QUARTER,
                composition_type=CompositionType.CENTERED,
                emotional_intent="soft, earned relief with quiet, genuine happiness",
                visual_focus="the small green vacuum tube glowing on the transceiver",
                text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
            ),
            "action": "Nour exhales with shoulders softening, lips curling into a gentle, authentic smile of relief.",
        },
        {
            "id": "06_natural_surprise",
            "name": "Natural surprise",
            "baseline_prompt": (
                f"{style_rules} Nour surprised with wide open eyes looking at a secret compartment opening. "
                "Character has curly hair, round glasses, green scarf. Artwork only."
            ),
            "plan": PanelPlan(
                panel_id="p6", beat_id="b6", scene_id="s6", reading_order_index=1,
                narrative_function=NarrativeFunction.REVEAL,
                story_event="A false panel in the clock snaps open, revealing a hidden compartment.",
                reader_takeaway="A sudden unexpected discovery shocks Nour.",
                character_ids=["nour"],
                environment="study room table with dismantled clock",
                shot_type=ShotType.CLOSE_UP,
                subject_scale=FramingScale.CLOSE_UP,
                camera_angle=CameraAngle.EYE_LEVEL,
                camera_position=CameraPosition.THREE_QUARTER,
                composition_type=CompositionType.OFF_CENTER_REVEAL,
                emotional_intent="arrested surprise and breath-catching wonder without comical gaping",
                visual_focus="the brass latch springing outward",
                text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
            ),
            "action": "Nour recoils slightly with breath catching, eyelids parting naturally in startlement as fingers hover.",
        },
        {
            "id": "07_profile_orientation",
            "name": "Profile and three-quarter view",
            "baseline_prompt": (
                f"{style_rules} Profile side view of Nour looking across the rooftops into the distance. "
                "Round wireframe glasses, curly hair, scarf. Artwork only."
            ),
            "plan": PanelPlan(
                panel_id="p7", beat_id="b7", scene_id="s7", reading_order_index=1,
                narrative_function=NarrativeFunction.ACTION_PREPARATION,
                story_event="Nour stands at the rooftop parapet, looking out over the city in sharp side profile.",
                reader_takeaway="Nour resolves to embark on the journey.",
                character_ids=["nour"],
                environment="rain-washed terracotta rooftop parapet at dusk",
                shot_type=ShotType.CLOSE_UP,
                subject_scale=FramingScale.MEDIUM_CLOSE_UP,
                camera_angle=CameraAngle.EYE_LEVEL,
                camera_position=CameraPosition.PROFILE,
                composition_type=CompositionType.RULE_OF_THIRDS,
                emotional_intent="stoic resolve and quiet determination in sharp profile",
                visual_focus="the distant industrial skyline across the bay",
                text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
            ),
            "action": "Nour stands in clean side profile, sightline directed horizontally across the misty rooftops, jaw set.",
        },
        {
            "id": "08_sequential_continuity",
            "name": "Sequential emotional progression",
            "baseline_prompt": (
                f"{style_rules} Nour in a series of actions escaping from a locked room. "
                "Round glasses, curly hair, green scarf. Artwork only."
            ),
            "plan": PanelPlan(
                panel_id="p8", beat_id="b8", scene_id="s8", reading_order_index=1,
                narrative_function=NarrativeFunction.IMPACT,
                story_event="Nour unlatches the skylight lock, pushing upward toward freedom.",
                reader_takeaway="Nour breaks through the final barrier.",
                character_ids=["nour"],
                environment="attic rafters directly beneath copper skylight frame",
                shot_type=ShotType.IMPACT,
                subject_scale=FramingScale.MEDIUM_SHOT,
                camera_angle=CameraAngle.LOW_ANGLE,
                camera_position=CameraPosition.THREE_QUARTER,
                composition_type=CompositionType.DIAGONAL_ACTION,
                emotional_intent="focused physical exertion and adrenaline surge",
                visual_focus="the iron sliding bolt clicking free",
                text=PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE),
            ),
            "action": "Nour braces feet against rafters, driving shoulders upward to shove the skylight hatch open.",
        },
    ]

    results = []

    print(f"=== Starting Real-Generation Benchmark ({len(benchmark_definitions)} Scenarios) ===")
    print(f"Model: {config.muse_image_model} | Reference: {REF_IMAGE_PATH.name}")

    for item in benchmark_definitions:
        scen_id = item["id"]
        print(f"\n--- Scenario {scen_id}: {item['name']} ---")

        # Compile Skill-Assisted Prompt
        scene = SceneSpec(
            scene_id=f"scene_{scen_id}",
            scene_index=0,
            title=item["name"],
            shot_type=item["plan"].shot_type.value,
            action=item["action"],
            character_ids=["nour"],
            panel_plan=item["plan"],
        )
        skill_prompt = build_scene_generation_prompt(
            line_and_tone=style_rules,
            scene=scene,
            character_specs=[nour_spec],
            visual_invariants=nour_spec.visual_invariants,
            prohibited_deviations=nour_spec.restrictions,
        )

        baseline_prompt = item["baseline_prompt"]

        # 1. Run Baseline Generation
        print("  Generating Baseline...")
        req_baseline = GenerationRequest(
            prompt=baseline_prompt,
            reference_images=ref_payload,
            model=config.muse_image_model,
            panel_id=f"{scen_id}_base",
            scene_id=f"scene_{scen_id}",
            dimensions=[512, 512],
        )
        t0 = time.time()
        resp_base = adapter.generate(req_baseline)
        t_base = round(time.time() - t0, 2)
        print(f"  Baseline completed: success={resp_base.success}, status={resp_base.http_status}, time={t_base}s")

        base_file = OUTPUT_DIR / f"{scen_id}_baseline.png"
        base_pixels = {}
        if resp_base.success and resp_base.image_bytes:
            base_file.write_bytes(resp_base.image_bytes)
            base_pixels = analyze_panel_pixels(resp_base.image_bytes)

        # 2. Run Skill-Assisted Generation
        print("  Generating Skill-Assisted...")
        req_skill = GenerationRequest(
            prompt=skill_prompt,
            reference_images=ref_payload,
            model=config.muse_image_model,
            panel_id=f"{scen_id}_skill",
            scene_id=f"scene_{scen_id}",
            dimensions=[512, 512],
        )
        t0 = time.time()
        resp_skill = adapter.generate(req_skill)
        t_skill = round(time.time() - t0, 2)
        print(f"  Skill-Assisted completed: success={resp_skill.success}, status={resp_skill.http_status}, time={t_skill}s")

        skill_file = OUTPUT_DIR / f"{scen_id}_skill_assisted.png"
        skill_pixels = {}
        if resp_skill.success and resp_skill.image_bytes:
            skill_file.write_bytes(resp_skill.image_bytes)
            skill_pixels = analyze_panel_pixels(resp_skill.image_bytes)

        # Evaluate both with the CharacterPerformanceEvaluator
        eval_base = evaluator.evaluate(
            resp_base.image_bytes,
            character_spec=nour_spec,
            panel_plan=item["plan"],
            compiled_prompt=baseline_prompt,
            is_simulated=False,
        )
        eval_skill = evaluator.evaluate(
            resp_skill.image_bytes,
            character_spec=nour_spec,
            panel_plan=item["plan"],
            compiled_prompt=skill_prompt,
            is_simulated=False,
        )

        record = {
            "scenario_id": scen_id,
            "scenario_name": item["name"],
            "baseline": {
                "prompt": baseline_prompt,
                "duration_seconds": t_base,
                "success": resp_base.success,
                "image_path": str(base_file) if resp_base.success else None,
                "pixel_metrics": base_pixels,
                "verdict": eval_base.verdict.value,
                "overall_score": eval_base.overall_score,
            },
            "skill_assisted": {
                "prompt": skill_prompt,
                "duration_seconds": t_skill,
                "success": resp_skill.success,
                "image_path": str(skill_file) if resp_skill.success else None,
                "pixel_metrics": skill_pixels,
                "verdict": eval_skill.verdict.value,
                "overall_score": eval_skill.overall_score,
            },
        }
        results.append(record)

    report_path = OUTPUT_DIR / "benchmark_report.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n=== Benchmark Complete! Saved report to {report_path} ===")
    return results


if __name__ == "__main__":
    run_benchmark()
