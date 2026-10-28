import os
import subprocess
from pathlib import Path
import pytest
from app.config import InkLoopConfig, PROJECT_ROOT
from app.schemas import CharacterSpec, AttributeCheck, VerificationResult, AttributeVerdict

def test_canonical_model_api_key(monkeypatch):
    """Ensure canonical MODEL_API_KEY is loaded correctly."""
    monkeypatch.setenv("MODEL_API_KEY", "test_key_canonical_12345")
    monkeypatch.delenv("META_API_KEY", raising=False)
    cfg = InkLoopConfig.load()
    assert cfg.has_credentials is True
    assert cfg.model_api_key == "test_key_canonical_12345"

def test_fallback_meta_api_key(monkeypatch):
    """Ensure legacy META_API_KEY works as a fallback when MODEL_API_KEY is unset."""
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("META_API_KEY", "test_key_legacy_67890")
    cfg = InkLoopConfig.load()
    assert cfg.has_credentials is True
    assert cfg.model_api_key == "test_key_legacy_67890"

def test_canonical_precedence_over_legacy(monkeypatch):
    """Ensure MODEL_API_KEY takes precedence when both are present."""
    monkeypatch.setenv("MODEL_API_KEY", "canonical_priority_key")
    monkeypatch.setenv("META_API_KEY", "legacy_ignored_key")
    cfg = InkLoopConfig.load()
    assert cfg.model_api_key == "canonical_priority_key"

def test_missing_key_behavior(monkeypatch):
    """Ensure missing credentials safely report false and not set."""
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    cfg = InkLoopConfig.load()
    assert cfg.has_credentials is False
    assert cfg.model_api_key is None
    assert cfg.mask_key() == "[NOT SET]"

def test_safe_credential_masking(monkeypatch):
    """Ensure mask_key never exposes any character of the secret key."""
    secret = "secret_raw_key_super_confidential_9999"
    monkeypatch.setenv("MODEL_API_KEY", secret)
    cfg = InkLoopConfig.load()
    masked = cfg.mask_key()
    assert masked == "[SET - REDACTED]"
    assert "secret" not in masked
    assert "9999" not in masked
    assert "confidential" not in masked

def test_project_root_resolution():
    """Ensure PROJECT_ROOT resolves to the repository root containing INKLOOP_PROJECT_BRIEF.md."""
    assert (PROJECT_ROOT / "INKLOOP_PROJECT_BRIEF.md").exists()
    assert (PROJECT_ROOT / ".gitignore").exists()

def test_credential_files_excluded_by_gitignore():
    """Verify that .gitignore properly excludes .env and secret files."""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
    assert ".env" in lines
    assert ".env*.local" in lines
    assert "*.key" in lines

    # Verify using git check-ignore command
    res = subprocess.run(["git", "check-ignore", ".env"], cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert res.returncode == 0
    assert ".env" in res.stdout

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
