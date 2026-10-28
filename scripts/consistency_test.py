import json
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.config import InkLoopConfig
from app.schemas import CharacterSpec, AttributeCheck

# Define Character Spec for M0 Benchmark (original, neutral character "Nour")
NOUR_SPEC = CharacterSpec(
    id="nour",
    attributes=[
        AttributeCheck(id="hair", text="short messy black hair, one white streak on the left", required=True),
        AttributeCheck(id="glasses", text="round glasses", required=True),
        AttributeCheck(id="jacket", text="oversized hooded jacket, lightning-bolt patch on chest", required=True),
        AttributeCheck(id="scar", text="small scar on right cheek", required=False),
    ]
)

# Define 6 original, neutral test scenes
BENCHMARK_SCENES = [
    {
        "id": "scene_01",
        "title": "Cafe Portrait",
        "shot_type": "medium close-up, front view",
        "description": "Nour sitting at a small wooden cafe table with a warm cup of tea, looking directly towards the viewer."
    },
    {
        "id": "scene_02",
        "title": "Night Reading",
        "shot_type": "medium shot, night lighting",
        "description": "Nour reading a hardcover book under the warm cone of light from an old streetlamp on a quiet stone path."
    },
    {
        "id": "scene_03",
        "title": "Surprised Corridor",
        "shot_type": "dynamic medium shot",
        "description": "Nour reacting with wide-eyed surprise in an empty library hallway, dropping a small brass key onto the floor."
    },
    {
        "id": "scene_04",
        "title": "Rain Walk",
        "shot_type": "three-quarter side shot",
        "description": "Nour walking briskly through gentle evening rain holding a transparent umbrella, street reflections visible."
    },
    {
        "id": "scene_05",
        "title": "Workbench Inspection",
        "shot_type": "close-up shot",
        "description": "Nour leaning closely over a wooden workbench, carefully inspecting a small brass mechanical gear with a magnifying lens."
    },
    {
        "id": "scene_06",
        "title": "Harbor Sunset",
        "shot_type": "wide medium shot, sunset backlight",
        "description": "Nour sitting peacefully on a wooden bench at the edge of a harbor pier, looking out over calm water at dusk."
    }
]

def build_prompt(character: CharacterSpec, scene: Dict[str, str], style: str = "black and white ink with delicate screentone shading") -> str:
    attr_str = ", ".join([a.text for a in character.attributes if a.required])
    return (
        f"Comic book panel illustration, {style}. "
        f"Character: {character.id}, featuring {attr_str}. "
        f"Scene: {scene['description']} ({scene['shot_type']}). "
        f"Clean linework, high contrast, no speech bubbles, no dialogue text, no watermarks."
    )

def run_consistency_experiment():
    config = InkLoopConfig.load()
    output_path = Path(__file__).parent.parent / "runs" / "m0_consistency_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "milestone": "M0",
        "character": NOUR_SPEC.model_dump(),
        "style": "B&W ink with screentone",
        "pass_criteria": "All required attributes (hair with white streak on left, round glasses, jacket with lightning-bolt patch) verifiably present. Target: >= 4/6 scenes passing in Arm B.",
        "config": {
            "endpoint": config.meta_base_url,
            "image_model": config.muse_image_model,
            "max_prompt_iterations": 1,
            "global_spend_cap_usd": config.global_spend_cap_usd,
        },
        "scenes": BENCHMARK_SCENES,
        "results": {
            "arm_a_text_only": [],
            "arm_b_anchored": []
        },
        "summary": {
            "arm_a_pass_count": 0,
            "arm_b_pass_count": 0,
            "threshold_met": False,
            "verdict": "BLOCKED"
        }
    }

    print("=================================================================")
    print("INKLOOP M0: 6-SCENE CHARACTER CONSISTENCY EXPERIMENT")
    print("=================================================================")
    print(f"Character: {NOUR_SPEC.id} | Required attributes: {[a.id for a in NOUR_SPEC.attributes if a.required]}")
    print(f"Exit Gate Criterion: Arm B >= 4/6 passing after <= 1 prompt iteration")

    if not config.has_credentials:
        print("\n[!] FATAL: Cannot execute live generation experiment.")
        print("[!] Missing credentials (META_API_KEY / MODEL_API_KEY is not set).")
        print("[!] In accordance with Hackathon Integrity Directives, results cannot be fabricated.")
        report["summary"]["verdict"] = "BLOCKED"
        report["summary"]["error"] = "Execution blocked due to missing META_API_KEY in environment"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[+] Status report written to: {output_path}")
        return report

    from openai import OpenAI
    client = OpenAI(base_url=config.meta_base_url, api_key=config.meta_api_key)

    print("[*] Generating reference anchor sheet for character Nour...")
    # Real generation loop will execute here when credentials are provided
    return report

if __name__ == "__main__":
    run_consistency_experiment()
