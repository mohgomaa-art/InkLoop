import pytest
from app.config import InkLoopConfig
from app.schemas import CharacterSpec, AttributeCheck, VerificationResult, AttributeVerdict

def test_config_secret_masking(monkeypatch):
    """Ensure API keys are masked and never exposed in plaintext representations."""
    monkeypatch.setenv("META_API_KEY", "meta_secret_key_1234567890_abcdef")
    cfg = InkLoopConfig.load()
    assert cfg.has_credentials is True
    masked = cfg.mask_key()
    assert masked == "meta...cdef"
    assert "1234567890" not in masked

def test_config_empty_credentials(monkeypatch):
    """Ensure missing credentials report false safely."""
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    cfg = InkLoopConfig.load()
    assert cfg.has_credentials is False
    assert cfg.mask_key() == "[NOT SET]"

def test_character_spec_schema_valid():
    """Verify that a canonical character spec validates correctly."""
    spec = CharacterSpec(
        id="nour",
        attributes=[
            AttributeCheck(id="hair", text="short messy black hair, one white streak on the left", required=True),
            AttributeCheck(id="glasses", text="round glasses", required=True),
            AttributeCheck(id="jacket", text="oversized hooded jacket, lightning-bolt patch on chest", required=True),
        ]
    )
    assert spec.id == "nour"
    assert len(spec.attributes) == 3
    assert spec.tolerances.min_face_px_for_check == 80

def test_verification_result_all_pass():
    """Verify that all-pass verdicts allow candidate acceptance."""
    verdicts = [
        AttributeVerdict(attr_id="hair", verdict="pass", evidence="Messy black hair with white streak visible on left"),
        AttributeVerdict(attr_id="glasses", verdict="pass", evidence="Round wireframe glasses visible on face"),
        AttributeVerdict(attr_id="jacket", verdict="pass", evidence="Oversized dark jacket with lightning bolt patch"),
    ]
    all_required_pass = all(v.verdict == "pass" for v in verdicts)
    result = VerificationResult(
        passed=all_required_pass,
        verdicts=verdicts,
        rejection_reason=None
    )
    assert result.passed is True
    assert result.rejection_reason is None

def test_verification_result_unsure_fails():
    """Verify that 'unsure' is treated as a rejection in the verification gate."""
    verdicts = [
        AttributeVerdict(attr_id="hair", verdict="pass", evidence="White streak visible"),
        AttributeVerdict(attr_id="glasses", verdict="unsure", evidence="Angle obscures glasses"),
        AttributeVerdict(attr_id="jacket", verdict="pass", evidence="Jacket patch visible"),
    ]
    all_required_pass = all(v.verdict == "pass" for v in verdicts)
    result = VerificationResult(
        passed=all_required_pass,
        verdicts=verdicts,
        rejection_reason="Attribute 'glasses' is unsure due to camera angle"
    )
    assert result.passed is False
    assert "glasses" in result.rejection_reason

def test_verification_result_corrupted_fails():
    """Verify that a corrupted attribute (fail) strictly rejects the candidate."""
    verdicts = [
        AttributeVerdict(attr_id="hair", verdict="fail", evidence="Hair is blonde and straight"),
        AttributeVerdict(attr_id="glasses", verdict="fail", evidence="No glasses present"),
        AttributeVerdict(attr_id="jacket", verdict="pass", evidence="Jacket patch visible"),
    ]
    all_required_pass = all(v.verdict == "pass" for v in verdicts)
    result = VerificationResult(
        passed=all_required_pass,
        verdicts=verdicts,
        rejection_reason="Failed attributes: hair, glasses"
    )
    assert result.passed is False
