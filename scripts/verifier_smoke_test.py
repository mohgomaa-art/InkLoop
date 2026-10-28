import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.config import InkLoopConfig
from app.schemas import CharacterSpec, AttributeCheck, VerificationResult, AttributeVerdict

NOUR_SPEC = CharacterSpec(
    id="nour",
    attributes=[
        AttributeCheck(id="hair", text="short messy black hair, one white streak on the left", required=True),
        AttributeCheck(id="glasses", text="round glasses", required=True),
        AttributeCheck(id="jacket", text="oversized hooded jacket, lightning-bolt patch on chest", required=True),
    ]
)

JUDGE_SYSTEM_PROMPT = """You are InkLoop's Chief Verifier and Canon Judge.
Your sole role is to inspect the candidate image against the character reference sheet and declared checklist.
CRITICAL RULES:
1. You can only remove or fail candidates. You cannot fix, edit, or add content.
2. For each attribute, evaluate strictly:
   - "pass": The attribute is clearly visible, correctly placed, and matches the canonical spec.
   - "fail": The attribute is missing, contradicted, or corrupted.
   - "unsure": The attribute is obscured, out of frame, or ambiguous. (Treated as fail).
3. Return ONLY valid JSON adhering to the specified schema without Markdown fences or commentary.
"""

def build_judge_prompt(character: CharacterSpec) -> str:
    checklist = "\n".join([f"- [{a.id}] (Required: {a.required}): {a.text}" for a in character.attributes])
    return f"""Character: {character.id}
Checklist to evaluate:
{checklist}

Required JSON Output Schema:
{{
  "verdicts": [
    {{"attr_id": "hair", "verdict": "pass"|"fail"|"unsure", "evidence": "specific visual details observed"}},
    {{"attr_id": "glasses", "verdict": "pass"|"fail"|"unsure", "evidence": "specific visual details observed"}},
    {{"attr_id": "jacket", "verdict": "pass"|"fail"|"unsure", "evidence": "specific visual details observed"}}
  ],
  "passed": true|false,
  "rejection_reason": "Summary of failure if any required attribute is fail/unsure, else null"
}}
"""

def run_verifier_test():
    config = InkLoopConfig.load()
    output_path = Path(__file__).parent.parent / "runs" / "m0_verifier_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "milestone": "M0",
        "component": "L2 Muse Spark Multimodal Verifier",
        "model": config.muse_spark_model,
        "test_cases": [
            {
                "case_id": "control_case_matching",
                "description": "Candidate matches character specification completely",
                "expected_verdict": "pass"
            },
            {
                "case_id": "corrupted_case_wrong_hair_no_glasses",
                "description": "Candidate deliberately generated with blonde straight hair and no glasses",
                "expected_verdict": "fail"
            }
        ],
        "status": "BLOCKED" if not config.has_credentials else "READY",
        "details": {}
    }

    print("=================================================================")
    print("INKLOOP M0: L2 VERIFIER FEASIBILITY SMOKE TEST")
    print("=================================================================")
    print(f"Target Judge Model: {config.muse_spark_model}")
    print(f"Schema Validation: Strict Pydantic VerificationResult")

    if not config.has_credentials:
        print("[!] Execution blocked: META_API_KEY is not set.")
        report["details"]["error"] = "Missing credentials"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[+] Verifier report written to: {output_path}")
        return report

    # Live call execution with credentials...
    return report

if __name__ == "__main__":
    run_verifier_test()
