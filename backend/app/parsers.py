"""
Parsers and payload builders for Meta Model API responses and requests.
Handles Muse Spark structured verification outputs and SAM 3.1 token formats.
"""
import re
import json
import base64
import hashlib
from typing import Optional, Dict, Any
from app.schemas import VerificationResult, AttributeVerdict, BoundingBox, SegmentationResult

SAM_BOX_PATTERN = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")
SAM_MASK_PATTERN = re.compile(r"<\|mask;x=(\d+);y=(\d+);data=([^|>]+)\|>")

def parse_sam_response(raw_text: str) -> SegmentationResult:
    """
    Parses SAM 3.1 text output containing custom special tokens for boxes and masks.
    Example: '<0f>0<|box;x1=81;y1=71;x2=1237;y2=1919;w=1280;h=1920|><|mask;x=0;y=0;data=...|>'
    """
    boxes = []
    box_matches = SAM_BOX_PATTERN.findall(raw_text)
    for match in box_matches:
        x1, y1, x2, y2, w, h = map(float, match)
        boxes.append(BoundingBox(
            x=x1,
            y=y1,
            width=x2 - x1,
            height=y2 - y1,
            label="person",
            confidence=1.0
        ))

    mask_matches = SAM_MASK_PATTERN.findall(raw_text)
    has_mask = len(mask_matches) > 0
    mask_sha256 = hashlib.sha256(
        "\n".join(f"{x}:{y}:{data}" for x, y, data in mask_matches).encode("utf-8")
    ).hexdigest() if has_mask else None

    return SegmentationResult(
        subject_count=len(boxes),
        boxes=boxes,
        mask_available=has_mask,
        mask_sha256=mask_sha256,
    )

def parse_verifier_response(raw_text: str) -> VerificationResult:
    """
    Cleans markdown formatting and parses the structured JSON returned by Muse Spark.
    Ensures strict validation against VerificationResult schema.
    """
    clean_text = raw_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    data = json.loads(clean_text)
    verdicts = [
        AttributeVerdict(
            attr_id=v["attr_id"],
            verdict=v["verdict"],
            evidence=v.get("evidence", "")
        )
        for v in data.get("verdicts", [])
    ]
    passed = data.get("passed", False)
    rejection_reason = data.get("rejection_reason")

    return VerificationResult(
        passed=passed,
        verdicts=verdicts,
        rejection_reason=rejection_reason
    )

def build_image_edit_payload(
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/png",
    model: str = "muse-image-1.0"
) -> Dict[str, Any]:
    """
    Builds the JSON payload for reference-anchored generation via POST /v1/images/edits.
    Encodes reference bytes into an inline data URI.
    """
    b64_str = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64_str}"
    return {
        "model": model,
        "prompt": prompt,
        "images": [
            {"image_url": data_url}
        ],
        "n": 1
    }
