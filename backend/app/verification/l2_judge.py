"""
InkLoop Visual Verification Service - L2 Multimodal Vision Judge.
Evaluates candidate panel image against canonical character reference sheet and checklist
using Meta Muse Spark (live) or deterministic offline simulation.
Enforces the Rule of Closed Failure (ADR-002).
"""
import base64
import json
import time
from typing import Optional, List, Dict, Any, Union
import httpx

from app.config import InkLoopConfig
from app.schemas import (
    AttributeCheck,
    AttributeVerdict,
    VerificationResult,
    CharacterSpec,
)
from app.parsers import parse_verifier_response
from app.verification.schemas import L2JudgeResult


JUDGE_SYSTEM_PROMPT = """You are InkLoop's Chief Verifier and Canon Judge.
Your sole role is to inspect the candidate image against the selected being's reference and creator-declared checklist. The subject may be human, nonhuman, masked, headless, object-like, abstract, or any creator-defined form.
CRITICAL RULES:
1. You can only remove or fail candidates. You cannot fix, edit, or add content.
2. For each attribute, evaluate strictly:
   - "pass": The attribute is clearly visible, correctly placed, and matches the canonical reference likeness and spec.
   - "fail": The declared attribute is missing or contradicted, or the depicted form has drifted from explicit creator constraints. Do not use human anatomy, age, face, hair, clothing, or limb expectations unless they are present in the selected checklist.
   - "unsure": The attribute is obscured, out of frame, or ambiguous. (Treated as fail).
3. Verify only the selected identity's declared shape, parts, material, markings, and other visual anchors. Do not penalize intentional nonhuman forms or changes allowed by the profile.
4. Return ONLY valid JSON adhering to the specified schema without Markdown fences or commentary.
"""


def build_judge_prompt(character_id: str, attributes: List[AttributeCheck]) -> str:
    checklist_lines = "\n".join([f"- [{a.id}] (Required: {a.required}): {a.text}" for a in attributes])
    return f"""Character: {character_id}
Checklist to evaluate:
{checklist_lines}

Required JSON Output Schema:
{{
  "verdicts": [
    {",\n    ".join([f'{{"attr_id": "{a.id}", "verdict": "pass"|"fail"|"unsure", "evidence": "concise observation"}}' for a in attributes])}
  ],
  "passed": true|false,
  "rejection_reason": "Summary of failure if any required attribute is fail/unsure, else null"
}}"""


class L2VisionJudge:
    """
    Tier-2 Multimodal Vision Judge.
    Compares candidate panel with reference sheet against canonical attributes.
    Enforces the Rule of Closed Failure: any 'fail' or 'unsure' on a required attribute fails closed.
    """

    def __init__(
        self,
        config: Optional[InkLoopConfig] = None,
        timeout_seconds: float = 45.0,
        mock_verdicts: Optional[List[AttributeVerdict]] = None,
    ):
        self.config = config or InkLoopConfig.load()
        self.timeout_seconds = timeout_seconds
        self.mock_verdicts = mock_verdicts

    def evaluate(
        self,
        reference_bytes: Optional[bytes],
        candidate_bytes: bytes,
        character_id: str,
        attributes: List[AttributeCheck],
        *,
        is_simulated: bool = False,
        mock_verdicts: Optional[List[AttributeVerdict]] = None,
    ) -> L2JudgeResult:
        """
        Runs multimodal visual comparison.
        """
        # If no attributes to check, trivially pass
        if not attributes:
            return L2JudgeResult(
                passed=True,
                verdicts=[],
                rejection_reason=None,
                raw_response=None,
                is_simulated=is_simulated,
                latency=0.0,
                model="no_attributes",
            )

        can_run_live = (
            (not is_simulated)
            and self.config.has_credentials
            and (reference_bytes is not None and len(reference_bytes) > 0)
        )

        if can_run_live:
            return self._run_live_judge(
                reference_bytes=reference_bytes,
                candidate_bytes=candidate_bytes,
                character_id=character_id,
                attributes=attributes,
            )
        else:
            return self._run_simulated_judge(
                reference_bytes=reference_bytes,
                candidate_bytes=candidate_bytes,
                character_id=character_id,
                attributes=attributes,
                mock_verdicts=mock_verdicts,
            )

    def _run_live_judge(
        self,
        reference_bytes: bytes,
        candidate_bytes: bytes,
        character_id: str,
        attributes: List[AttributeCheck],
    ) -> L2JudgeResult:
        """Dispatches multimodal comparison to Meta Muse Spark."""
        ref_b64 = base64.b64encode(reference_bytes).decode("ascii")
        cand_b64 = base64.b64encode(candidate_bytes).decode("ascii")

        ref_data_url = f"data:image/png;base64,{ref_b64}"
        cand_data_url = f"data:image/png;base64,{cand_b64}"

        prompt_text = build_judge_prompt(character_id, attributes)

        payload = {
            "model": self.config.muse_spark_model,
            "reasoning": {"effort": "low"},
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "REFERENCE IMAGE (CANON):"},
                        {"type": "input_image", "image_url": ref_data_url},
                        {"type": "input_text", "text": "CANDIDATE PANEL IMAGE TO VERIFY:"},
                        {"type": "input_image", "image_url": cand_data_url},
                        {"type": "input_text", "text": prompt_text},
                    ]
                }
            ],
            "max_output_tokens": 1024
        }

        api_key = (
            self.config.model_api_key.get_secret_value()
            if hasattr(self.config.model_api_key, "get_secret_value")
            else (self.config.model_api_key or "")
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        start_t = time.time()
        try:
            resp = httpx.post(
                f"{self.config.meta_base_url}/responses",
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            latency = round(time.time() - start_t, 2)

            if resp.status_code != 200:
                # Live call failed, fail closed
                return L2JudgeResult(
                    passed=False,
                    verdicts=[
                        AttributeVerdict(
                            attr_id=a.id,
                            verdict="unsure",
                            evidence=f"API error {resp.status_code}: live verifier call failed",
                        )
                        for a in attributes
                    ],
                    rejection_reason=f"Live vision judge HTTP error {resp.status_code}",
                    raw_response=resp.text[:300],
                    is_simulated=False,
                    latency=latency,
                    model=self.config.muse_spark_model,
                )

            data = resp.json()
            raw_text = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            raw_text = c.get("text", "")

            # Parse structured response
            v_result = parse_verifier_response(raw_text)
            return self._enforce_closed_failure(
                v_result=v_result,
                attributes=attributes,
                raw_text=raw_text,
                is_simulated=False,
                latency=latency,
                model=self.config.muse_spark_model,
            )

        except Exception as e:
            latency = round(time.time() - start_t, 2)
            # Fail closed on network or unparseable exceptions
            return L2JudgeResult(
                passed=False,
                verdicts=[
                    AttributeVerdict(
                        attr_id=a.id,
                        verdict="unsure",
                        evidence=f"Verifier exception: {str(e)}",
                    )
                    for a in attributes
                ],
                rejection_reason=f"Vision judge exception: {str(e)}",
                raw_response=None,
                is_simulated=False,
                latency=latency,
                model=self.config.muse_spark_model,
            )

    def _run_simulated_judge(
        self,
        reference_bytes: Optional[bytes],
        candidate_bytes: bytes,
        character_id: str,
        attributes: List[AttributeCheck],
        mock_verdicts: Optional[List[AttributeVerdict]] = None,
    ) -> L2JudgeResult:
        """Deterministic offline simulated judgment."""
        actual_mock_verdicts = mock_verdicts if mock_verdicts is not None else self.mock_verdicts
        if actual_mock_verdicts is not None:
            verdicts = actual_mock_verdicts
        else:
            # Deterministic default: pass all attributes with simulated evidence tag
            verdicts = [
                AttributeVerdict(
                    attr_id=a.id,
                    verdict="pass",
                    evidence=f"[SIMULATED] Attribute '{a.id}' matched canonical reference ({a.text})",
                )
                for a in attributes
            ]

        v_result = VerificationResult(
            passed=True,
            verdicts=verdicts,
            rejection_reason=None,
            is_simulated=True,
        )

        return self._enforce_closed_failure(
            v_result=v_result,
            attributes=attributes,
            raw_text="[SIMULATED_DETERMINISTIC_RESPONSE]",
            is_simulated=True,
            latency=0.01,
            model="simulated-vision-judge",
        )

    def _enforce_closed_failure(
        self,
        v_result: VerificationResult,
        attributes: List[AttributeCheck],
        raw_text: str,
        is_simulated: bool,
        latency: float,
        model: str,
    ) -> L2JudgeResult:
        """
        Enforces Rule of Closed Failure:
        Never trusts raw passed=True if any required attribute has verdict 'fail' or 'unsure'.
        """
        required_attrs = {a.id: a for a in attributes if a.required}
        verdict_map = {v.attr_id: v.verdict for v in v_result.verdicts}

        failing_attrs: List[str] = []
        unsure_attrs: List[str] = []

        for attr_id in required_attrs:
            v = verdict_map.get(attr_id, "unsure")
            if v == "fail":
                failing_attrs.append(attr_id)
            elif v == "unsure":
                unsure_attrs.append(attr_id)

        passed = True
        rejection_reason = v_result.rejection_reason

        if failing_attrs:
            passed = False
            rejection_reason = (
                f"Required attribute(s) failed verification: {', '.join(failing_attrs)}"
            )
        elif unsure_attrs:
            passed = False
            rejection_reason = (
                f"Required attribute(s) ambiguous/unsure (escalating to human review): {', '.join(unsure_attrs)}"
            )

        return L2JudgeResult(
            passed=passed,
            verdicts=v_result.verdicts,
            rejection_reason=rejection_reason if not passed else None,
            raw_response=raw_text,
            is_simulated=is_simulated,
            latency=latency,
            model=model,
        )
