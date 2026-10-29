"""
Unit tests for SAM 3.1 and Muse Spark response parsers and payload builders.
"""
import pytest
from app.parsers import parse_sam_response, parse_verifier_response, build_image_edit_payload
from app.schemas import VerificationResult, SegmentationResult

def test_parse_sam_response_with_box_and_mask():
    raw_sample = "<0f>0<|box;x1=81;y1=71;x2=1237;y2=1919;w=1280;h=1920|><|mask;x=0;y=0;data=1024,641,~!!5[z#MZtDcf=^m8|>"
    res = parse_sam_response(raw_sample)
    assert isinstance(res, SegmentationResult)
    assert res.subject_count == 1
    assert res.mask_available is True
    assert len(res.boxes) == 1
    box = res.boxes[0]
    assert box.x == 81.0
    assert box.y == 71.0
    assert box.width == 1156.0  # 1237 - 81
    assert box.height == 1848.0  # 1919 - 71
    assert box.label == "person"

def test_parse_sam_response_no_detections():
    raw_sample = "No subjects detected in frame."
    res = parse_sam_response(raw_sample)
    assert res.subject_count == 0
    assert len(res.boxes) == 0
    assert res.mask_available is False

def test_parse_verifier_response_clean_json():
    json_text = """
    {
      "verdicts": [
        {"attr_id": "hair", "verdict": "pass", "evidence": "Short messy black hair with distinct white streak on left"},
        {"attr_id": "glasses", "verdict": "pass", "evidence": "Round wireframe glasses visible"},
        {"attr_id": "jacket", "verdict": "pass", "evidence": "Oversized hooded jacket with lightning patch"}
      ],
      "passed": true,
      "rejection_reason": null
    }
    """
    res = parse_verifier_response(json_text)
    assert isinstance(res, VerificationResult)
    assert res.passed is True
    assert len(res.verdicts) == 3
    assert res.verdicts[0].attr_id == "hair"
    assert res.verdicts[0].verdict == "pass"
    assert res.rejection_reason is None

def test_parse_verifier_response_markdown_fences():
    fenced_text = """```json
    {
      "verdicts": [
        {"attr_id": "hair", "verdict": "fail", "evidence": "Blonde hair, no white streak"},
        {"attr_id": "glasses", "verdict": "fail", "evidence": "No glasses detected"},
        {"attr_id": "jacket", "verdict": "fail", "evidence": "Plain crewneck sweater"}
      ],
      "passed": false,
      "rejection_reason": "Candidate lacks all three required canonical character attributes."
    }
    ```"""
    res = parse_verifier_response(fenced_text)
    assert isinstance(res, VerificationResult)
    assert res.passed is False
    assert len(res.verdicts) == 3
    assert res.verdicts[0].verdict == "fail"
    assert "Candidate lacks" in res.rejection_reason

def test_build_image_edit_payload():
    dummy_bytes = b"fake_png_data_bytes_12345"
    payload = build_image_edit_payload(
        prompt="A comic book panel with Nour",
        image_bytes=dummy_bytes,
        mime_type="image/png"
    )
    assert payload["model"] == "muse-image-1.0"
    assert payload["prompt"] == "A comic book panel with Nour"
    assert payload["n"] == 1
    assert len(payload["images"]) == 1
    assert payload["images"][0]["image_url"].startswith("data:image/png;base64,")
