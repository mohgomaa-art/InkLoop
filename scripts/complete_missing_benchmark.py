"""
Complete any missing images in runs/creative_skills_benchmark/ and update benchmark_report.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image

from app.config import InkLoopConfig, PROJECT_ROOT
from app.image_adapter import MetaImageGenerationAdapter, GenerationRequest, ReferenceImagePayload
from app.context_builder import build_scene_generation_prompt
from app.schemas import CharacterSpec, AttributeCheck, SceneSpec
from app.verification.performance_verifier import analyze_panel_pixels, CharacterPerformanceEvaluator

OUTPUT_DIR = PROJECT_ROOT / "runs" / "creative_skills_benchmark"
REF_IMAGE_PATH = PROJECT_ROOT / "runs" / "m0_visual" / "reference" / "nour_reference.png"


def complete_benchmark():
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

    report_path = OUTPUT_DIR / "benchmark_report.json"
    data = json.loads(report_path.read_text(encoding="utf-8"))

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

    for item in data:
        scen_id = item["scenario_id"]
        # Check baseline
        base_file = OUTPUT_DIR / f"{scen_id}_baseline.png"
        if not base_file.exists() or not item["baseline"]["success"]:
            print(f"Retrying Baseline for {scen_id}...")
            req = GenerationRequest(
                prompt=item["baseline"]["prompt"],
                reference_images=ref_payload,
                model=config.muse_image_model,
                panel_id=f"{scen_id}_base_retry",
                dimensions=[512, 512],
            )
            resp = adapter.generate(req)
            if resp.success and resp.image_bytes:
                base_file.write_bytes(resp.image_bytes)
                item["baseline"]["success"] = True
                item["baseline"]["image_path"] = str(base_file)
                item["baseline"]["pixel_metrics"] = analyze_panel_pixels(resp.image_bytes)
                ev = evaluator.evaluate(resp.image_bytes, character_spec=nour_spec, is_simulated=False)
                item["baseline"]["verdict"] = ev.verdict.value
                item["baseline"]["overall_score"] = ev.overall_score
                print(f"  Success: {base_file.name}")
            else:
                print(f"  Failed: {resp.http_status} - {resp.error_message}")

        # Check skill-assisted
        skill_file = OUTPUT_DIR / f"{scen_id}_skill_assisted.png"
        if not skill_file.exists() or not item["skill_assisted"]["success"]:
            print(f"Retrying Skill-Assisted for {scen_id}...")
            req = GenerationRequest(
                prompt=item["skill_assisted"]["prompt"],
                reference_images=ref_payload,
                model=config.muse_image_model,
                panel_id=f"{scen_id}_skill_retry",
                dimensions=[512, 512],
            )
            resp = adapter.generate(req)
            if resp.success and resp.image_bytes:
                skill_file.write_bytes(resp.image_bytes)
                item["skill_assisted"]["success"] = True
                item["skill_assisted"]["image_path"] = str(skill_file)
                item["skill_assisted"]["pixel_metrics"] = analyze_panel_pixels(resp.image_bytes)
                ev = evaluator.evaluate(resp.image_bytes, character_spec=nour_spec, is_simulated=False)
                item["skill_assisted"]["verdict"] = ev.verdict.value
                item["skill_assisted"]["overall_score"] = ev.overall_score
                print(f"  Success: {skill_file.name}")
            else:
                print(f"  Failed: {resp.http_status} - {resp.error_message}")

    report_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Benchmark data updated successfully.")


if __name__ == "__main__":
    complete_benchmark()
