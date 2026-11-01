"""
Comprehensive Automated Tests for InkLoop Visual Verification Service
(Workstream S7 / Milestone M2 - ADR-002).
Tests multi-tier verification:
- L0: Deterministic Code Checks (decodability, aspect ratio, non-blank, sheet bleed)
- L1: Structure & Subject Framing (SAM segmentation & scale thresholds)
- L2: Multimodal Vision Judge (Rule of Closed Failure, tri-state verdicts, human escalation)
- Early rejection pipeline integration and BatchOrchestrator integration.
"""
import io
import pytest
from PIL import Image, ImageDraw
import numpy as np

from app.config import InkLoopConfig
from app.schemas import (
    AttributeCheck,
    AttributeVerdict,
    VerificationResult,
    CharacterSpec,
    ReferenceAsset,
    Tolerances,
    BoundingBox,
    PanelStatus,
    BatchStatus,
)
from app.verification.schemas import (
    VerificationMode,
    L0CheckResult,
    L1SubjectResult,
    L2JudgeResult,
)
from app.verification.l0_code import L0CodeChecker
from app.verification.l1_subject import L1SubjectChecker
from app.verification.l2_judge import L2VisionJudge, build_judge_prompt
from app.verification.service import (
    VisualVerificationService,
    SimulatedVisualVerificationService,
)
from app.orchestrator import BatchOrchestrator
from app.image_adapter import SimulatedImageGenerationAdapter
from tests.fixtures.benchmark_fixtures import create_m0_benchmark_batch_spec


# ==============================================================================
# Helper Functions to Generate Synthetic Test Images
# ==============================================================================

def create_valid_textured_png(width: int = 512, height: int = 512) -> bytes:
    """Creates a valid PNG with high variance and varied shapes (non-blank)."""
    img = Image.new("RGB", (width, height), color=(120, 140, 160))
    draw = ImageDraw.Draw(img)
    # Add varying geometric patterns to ensure high entropy / pixel variance
    draw.rectangle([50, 50, width - 50, height - 50], fill=(200, 50, 50), outline=(20, 20, 20), width=4)
    draw.ellipse([width // 4, height // 4, 3 * width // 4, 3 * height // 4], fill=(50, 200, 50))
    draw.line([0, 0, width, height], fill=(255, 255, 0), width=6)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def create_solid_color_png(width: int = 256, height: int = 256, color=(255, 255, 255)) -> bytes:
    """Creates a completely flat solid color PNG (zero variance)."""
    img = Image.new("RGB", (width, height), color=color)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def create_sheet_bleed_png(width: int = 256, height: int = 256, border_px: int = 4) -> bytes:
    """Creates a textured image surrounded by a solid pure white border ring (sheet bleed artifact)."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Textured inner content
    draw.rectangle(
        [border_px + 2, border_px + 2, width - border_px - 3, height - border_px - 3],
        fill=(40, 80, 160),
    )
    draw.ellipse(
        [border_px + 10, border_px + 10, width - border_px - 10, height - border_px - 10],
        fill=(220, 100, 30),
    )
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


@pytest.fixture
def nour_spec() -> CharacterSpec:
    return CharacterSpec(
        id="nour",
        name="Nour",
        attributes=[
            AttributeCheck(id="hair", text="short messy black hair, one white streak on the left", required=True),
            AttributeCheck(id="glasses", text="round wireframe glasses", required=True),
            AttributeCheck(id="jacket", text="oversized hooded jacket with lightning patch", required=True),
        ],
        tolerances=Tolerances(min_face_px_for_check=80),
    )


# ==============================================================================
# 1. Tier 0: L0 Deterministic Code Checker Tests
# ==============================================================================

def test_l0_valid_textured_png_passes():
    """Proves that a decodable, high-variance, non-bordered PNG passes all L0 checks."""
    checker = L0CodeChecker()
    valid_bytes = create_valid_textured_png(512, 512)

    result = checker.check(valid_bytes, target_dimensions=(512, 512), target_aspect_ratio="1:1")
    assert result.passed is True
    assert result.checks["decodable"] is True
    assert result.checks["format_valid"] is True
    assert result.checks["non_blank"] is True
    assert result.checks["aspect_ratio_match"] is True
    assert result.checks["dimensions_match"] is True
    assert result.checks["no_sheet_bleed"] is True
    assert result.dimensions == (512, 512)
    assert result.pixel_std is not None and result.pixel_std > 10.0


def test_l0_corrupted_and_empty_bytes_fail():
    """Proves that empty or malformed bytes immediately fail L0 without crashing."""
    checker = L0CodeChecker()

    res_empty = checker.check(b"")
    assert res_empty.passed is False
    assert "empty" in (res_empty.reason or "").lower()

    res_garbage = checker.check(b"\x89PNG\r\n\x1a\nNotAValidPngDataGarbage123456789")
    assert res_garbage.passed is False
    assert "failed to decode" in (res_garbage.reason or "").lower()


def test_l0_blank_solid_image_fails():
    """Proves that a completely solid white or black image is rejected as a blank frame."""
    checker = L0CodeChecker(min_pixel_std=2.0)

    white_bytes = create_solid_color_png(256, 256, color=(255, 255, 255))
    res_white = checker.check(white_bytes)
    assert res_white.passed is False
    assert res_white.checks["non_blank"] is False
    assert "blank or solid" in (res_white.reason or "").lower()

    black_bytes = create_solid_color_png(256, 256, color=(0, 0, 0))
    res_black = checker.check(black_bytes)
    assert res_black.passed is False
    assert res_black.checks["non_blank"] is False


def test_l0_aspect_ratio_mismatch_fails():
    """Proves that an image violating declared aspect ratio fails L0."""
    checker = L0CodeChecker(aspect_ratio_tolerance=0.05)
    # 512x256 is 2:1 aspect ratio
    wide_bytes = create_valid_textured_png(512, 256)

    res = checker.check(wide_bytes, target_aspect_ratio="1:1")
    assert res.passed is False
    assert res.checks["aspect_ratio_match"] is False
    assert "aspect ratio mismatch" in (res.reason or "").lower()


def test_l0_dimension_mismatch_fails():
    """Proves that an image with mismatched dimensions fails L0."""
    checker = L0CodeChecker()
    img_bytes = create_valid_textured_png(256, 256)

    res = checker.check(img_bytes, target_dimensions=(1024, 1024))
    assert res.passed is False
    assert res.checks["dimensions_match"] is False
    assert "dimension mismatch" in (res.reason or "").lower()


def test_l0_sheet_bleed_detection():
    """Proves that an artificial solid white border around high-variance content is caught as bleed."""
    checker = L0CodeChecker(border_thickness=4, max_border_uniformity=0.98)
    bleed_bytes = create_sheet_bleed_png(256, 256, border_px=4)

    res = checker.check(bleed_bytes, check_sheet_bleed=True)
    assert res.passed is False
    assert res.checks["no_sheet_bleed"] is False
    assert "sheet bleed detected" in (res.reason or "").lower()


# ==============================================================================
# 2. Tier 1: L1 Subject & Structure Checker Tests
# ==============================================================================

def test_l1_simulated_detects_person_framing():
    """Proves that L1 simulated evaluation extracts subject boxes and verifies framing."""
    checker = L1SubjectChecker()
    valid_bytes = create_valid_textured_png(512, 512)

    res = checker.check(
        candidate_bytes=valid_bytes,
        concept="person",
        expected_subject_count=1,
        is_simulated=True,
    )
    assert res.passed is True
    assert res.subject_count >= 1
    assert res.framing_ok is True
    assert res.face_scale_ok is True
    assert res.is_simulated is True


def test_l1_subject_count_zero_fails():
    """Proves that zero detected subjects fails L1 when a character is expected."""
    checker = L1SubjectChecker()
    valid_bytes = create_valid_textured_png(512, 512)

    res = checker.check(
        candidate_bytes=valid_bytes,
        concept="person",
        expected_subject_count=1,
        is_simulated=True,
        mock_boxes=[],  # 0 subjects detected
    )
    assert res.passed is False
    assert res.subject_count == 0
    assert "no character detected" in (res.reason or "").lower()


def test_l1_subject_scale_too_small_fails():
    """Proves that a subject occupying less than the minimum fraction fails framing."""
    checker = L1SubjectChecker(min_subject_fraction=0.05)
    valid_bytes = create_valid_textured_png(1000, 1000)

    # 20x20 box in 1000x1000 image = 400 / 1,000,000 = 0.04% (< 5%)
    tiny_box = [BoundingBox(x=500, y=500, width=20, height=20, label="person", confidence=0.9)]
    res = checker.check(
        candidate_bytes=valid_bytes,
        expected_subject_count=1,
        is_simulated=True,
        mock_boxes=tiny_box,
    )
    assert res.passed is False
    assert res.framing_ok is False
    assert "subject scale too small" in (res.reason or "").lower()


def test_l1_face_size_below_threshold_fails():
    """Proves that an estimated face resolution below min_face_px_for_check fails."""
    checker = L1SubjectChecker()
    valid_bytes = create_valid_textured_png(1000, 1000)

    # Bounding box of height 120px; 120 * 0.22 = 26.4px face (< 80px tolerance)
    small_face_box = [BoundingBox(x=100, y=100, width=80, height=120, label="person", confidence=0.9)]
    tolerances = Tolerances(min_face_px_for_check=80)

    res = checker.check(
        candidate_bytes=valid_bytes,
        expected_subject_count=1,
        tolerances=tolerances,
        is_simulated=True,
        mock_boxes=small_face_box,
    )
    assert res.passed is False
    assert res.face_scale_ok is False
    assert "face resolution" in (res.reason or "").lower()


# ==============================================================================
# 3. Tier 2: L2 Multimodal Vision Judge Tests
# ==============================================================================

def test_l2_all_attributes_pass(nour_spec):
    """Proves that when all required attributes have verdict 'pass', L2 passes."""
    judge = L2VisionJudge()
    cand_bytes = create_valid_textured_png(256, 256)
    ref_bytes = create_valid_textured_png(256, 256)

    res = judge.evaluate(
        reference_bytes=ref_bytes,
        candidate_bytes=cand_bytes,
        character_id="nour",
        attributes=nour_spec.attributes,
        is_simulated=True,
    )
    assert res.passed is True
    assert len(res.verdicts) == len(nour_spec.attributes)
    assert all(v.verdict == "pass" for v in res.verdicts)
    assert res.rejection_reason is None
    assert res.is_simulated is True


def test_l2_single_attribute_fail_rejects_candidate(nour_spec):
    """Proves that if any required attribute has verdict 'fail', L2 rejects."""
    judge = L2VisionJudge()
    cand_bytes = create_valid_textured_png(256, 256)

    # Simulate failing glasses
    mock_verdicts = [
        AttributeVerdict(attr_id="hair", verdict="pass", evidence="Matches white streak"),
        AttributeVerdict(attr_id="glasses", verdict="fail", evidence="Candidate has no glasses"),
        AttributeVerdict(attr_id="jacket", verdict="pass", evidence="Matches jacket and patch"),
    ]

    res = judge.evaluate(
        reference_bytes=None,
        candidate_bytes=cand_bytes,
        character_id="nour",
        attributes=nour_spec.attributes,
        is_simulated=True,
        mock_verdicts=mock_verdicts,
    )
    assert res.passed is False
    assert "glasses" in (res.rejection_reason or "")
    assert res.rejection_reason is not None


def test_l2_unsure_escalates_to_human_review(nour_spec):
    """Proves that if any required attribute is 'unsure', L2 rejects and flags human escalation."""
    judge = L2VisionJudge()
    cand_bytes = create_valid_textured_png(256, 256)

    mock_verdicts = [
        AttributeVerdict(attr_id="hair", verdict="pass", evidence="Visible hair"),
        AttributeVerdict(attr_id="glasses", verdict="unsure", evidence="Subject is facing away, glasses obscured"),
        AttributeVerdict(attr_id="jacket", verdict="pass", evidence="Jacket visible"),
    ]

    res = judge.evaluate(
        reference_bytes=None,
        candidate_bytes=cand_bytes,
        character_id="nour",
        attributes=nour_spec.attributes,
        is_simulated=True,
        mock_verdicts=mock_verdicts,
    )
    assert res.passed is False
    assert "human review" in (res.rejection_reason or "").lower()
    assert "glasses" in (res.rejection_reason or "")


def test_l2_rule_of_closed_failure_overrides_model_true(nour_spec):
    """Proves that code enforces Rule of Closed Failure even if external LLM claimed passed=True."""
    judge = L2VisionJudge()
    # A raw LLM response that erroneously set passed: true despite a fail verdict
    flawed_v_result = VerificationResult(
        passed=True,  # Flawed model claim
        verdicts=[
            AttributeVerdict(attr_id="hair", verdict="pass", evidence="OK"),
            AttributeVerdict(attr_id="glasses", verdict="fail", evidence="Missing glasses"),
            AttributeVerdict(attr_id="jacket", verdict="pass", evidence="OK"),
        ]
    )

    result = judge._enforce_closed_failure(
        v_result=flawed_v_result,
        attributes=nour_spec.attributes,
        raw_text="{}",
        is_simulated=True,
        latency=0.01,
        model="test-judge",
    )
    # Must be forced to False
    assert result.passed is False
    assert "glasses" in (result.rejection_reason or "")


def test_l2_optional_attribute_fail_does_not_block_acceptance():
    """Proves that an optional (required=False) attribute failing does not block acceptance."""
    judge = L2VisionJudge()
    attrs = [
        AttributeCheck(id="hair", text="black hair", required=True),
        AttributeCheck(id="scar", text="small scar on cheek", required=False),  # Optional
    ]
    mock_verdicts = [
        AttributeVerdict(attr_id="hair", verdict="pass", evidence="Black hair verified"),
        AttributeVerdict(attr_id="scar", verdict="fail", evidence="Scar not visible at this angle"),
    ]

    res = judge.evaluate(
        reference_bytes=None,
        candidate_bytes=b"dummy",
        character_id="nour",
        attributes=attrs,
        is_simulated=True,
        mock_verdicts=mock_verdicts,
    )
    assert res.passed is True
    assert res.rejection_reason is None


# ==============================================================================
# 4. Hierarchical Pipeline & Early Rejection Integration Tests
# ==============================================================================

def test_pipeline_early_rejection_l0_skips_l1_and_l2(nour_spec):
    """Proves that if L0 fails (e.g. corrupt bytes), L1 and L2 are NOT called."""
    service = SimulatedVisualVerificationService()
    corrupted_bytes = b"NotAValidImage"

    result = service.verify_panel(
        reference_asset=None,
        candidate_bytes=corrupted_bytes,
        character_spec=nour_spec,
    )
    assert result.passed is False
    assert result.l0_passed is False
    assert result.l1_passed is None  # Skipped
    assert result.l2_passed is None  # Skipped
    assert "L0 Code check failed" in (result.rejection_reason or "")


def test_pipeline_early_rejection_l1_skips_l2(nour_spec):
    """Proves that if L0 passes but L1 fails (no subject), L2 is NOT called."""
    service = SimulatedVisualVerificationService()
    valid_bytes = create_valid_textured_png(512, 512)

    # Inject mock L1 checker that returns 0 subjects
    service.l1_checker.check = lambda *args, **kwargs: L1SubjectResult(
        passed=False,
        subject_count=0,
        boxes=[],
        mask_available=False,
        framing_ok=False,
        face_scale_ok=False,
        reason="Zero characters detected in panel",
        is_simulated=True,
    )

    result = service.verify_panel(
        reference_asset=None,
        candidate_bytes=valid_bytes,
        character_spec=nour_spec,
    )
    assert result.passed is False
    assert result.l0_passed is True
    assert result.l1_passed is False
    assert result.l2_passed is None  # Skipped
    assert "L1 Subject check failed" in (result.rejection_reason or "")


def test_pipeline_full_pass(nour_spec):
    """Proves that when L0, L1, and L2 pass, VerificationResult confirms all tiers passed."""
    service = SimulatedVisualVerificationService()
    valid_bytes = create_valid_textured_png(512, 512)

    result = service.verify_panel(
        reference_asset=None,
        candidate_bytes=valid_bytes,
        character_spec=nour_spec,
        target_dimensions=(512, 512),
        target_aspect_ratio="1:1",
    )
    assert result.passed is True
    assert result.l0_passed is True
    assert result.l1_passed is True
    assert result.l2_passed is True
    assert result.is_simulated is True
    assert len(result.verdicts) == len(nour_spec.attributes)


# ==============================================================================
# 5. BatchOrchestrator Integration Tests
# ==============================================================================

def test_orchestrator_integration_with_verification_service(tmp_path):
    """
    Proves end-to-end integration: BatchOrchestrator invoking VisualVerificationService.
    With require_verification=True, all panels generate and verify successfully.
    """
    config = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(
        default_success=True,
        simulated_cost=0.01,
        simulated_usage={"total_tokens": 100},
        duration_seconds=0.01,
    )
    # Inject valid PNG generator into simulated adapter
    valid_png = create_valid_textured_png(512, 512)
    adapter._create_dummy_png = lambda label: valid_png

    verifier_service = SimulatedVisualVerificationService(config=config)

    orchestrator = BatchOrchestrator(
        config=config,
        adapter=adapter,
        run_log_dir=tmp_path / "logs",
        verifier=verifier_service,  # Service passed directly as callable verifier
    )

    batch_spec = create_m0_benchmark_batch_spec(
        batch_id="test_orchestrator_verification_batch",
        output_dir=str(tmp_path / "output"),
    )
    batch_spec.require_verification = True

    summary = orchestrator.orchestrate_batch(batch_spec)

    assert summary.status == BatchStatus.COMPLETED
    assert summary.total_panels == 6
    assert summary.generated_panels == 6
    assert summary.verified_panels == 6
    assert summary.unverified_panels == 0
    assert summary.failed_panels == 0
    assert summary.unresolved_panels == 0


def test_orchestrator_retry_on_l2_fail_and_abort_on_unsure(tmp_path):
    """
    Proves that when verifier rejects with 'fail', orchestrator retries;
    when verifier returns 'unsure', orchestrator aborts retries and transitions to NEEDS_HUMAN.
    """
    config = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True, duration_seconds=0.01)
    valid_png = create_valid_textured_png(512, 512)
    adapter._create_dummy_png = lambda label: valid_png

    # Verifier that returns UNSURE on hair
    unsure_verdicts = [
        AttributeVerdict(attr_id="hair", verdict="unsure", evidence="Hair obscured"),
        AttributeVerdict(attr_id="glasses", verdict="pass", evidence="OK"),
        AttributeVerdict(attr_id="jacket", verdict="pass", evidence="OK"),
    ]
    unsure_verifier = SimulatedVisualVerificationService(config=config, mock_verdicts=unsure_verdicts)

    orchestrator = BatchOrchestrator(
        config=config,
        adapter=adapter,
        run_log_dir=tmp_path / "logs",
        verifier=unsure_verifier,
    )

    batch_spec = create_m0_benchmark_batch_spec(
        batch_id="test_unsure_escalation_batch",
        output_dir=str(tmp_path / "output"),
    )
    batch_spec.require_verification = True

    summary = orchestrator.orchestrate_batch(batch_spec)

    # Panels should be marked NEEDS_HUMAN, not silently accepted or retried forever
    assert summary.status != BatchStatus.COMPLETED
    assert summary.verified_panels == 0
    for p in summary.panel_results:
        assert p.status == PanelStatus.NEEDS_HUMAN
        assert p.verification_status == "UNSURE"


# ==============================================================================
# 6. Security and Truthfulness Tests
# ==============================================================================

def test_no_secrets_in_verification_details_or_results():
    """Proves that MODEL_API_KEY, headers, and bearer tokens never leak into verification results."""
    service = SimulatedVisualVerificationService()
    valid_bytes = create_valid_textured_png(256, 256)

    result = service.verify_panel(reference_asset=None, candidate_bytes=valid_bytes)
    dumped_str = result.model_dump_json()

    assert "Bearer" not in dumped_str
    assert "Authorization" not in dumped_str
    assert "MODEL_API_KEY" not in dumped_str


def test_truthful_simulation_labeling():
    """Proves that simulated verifier explicitly sets is_simulated=True and never claims live proof."""
    service = SimulatedVisualVerificationService()
    valid_bytes = create_valid_textured_png(256, 256)

    result = service.verify_panel(reference_asset=None, candidate_bytes=valid_bytes)
    assert result.is_simulated is True
    assert result.details.get("l0", {}).get("passed") is True


def test_l1_live_sam_error_fails_closed_without_heuristic_fallback(monkeypatch):
    """
    Phase 5 & 7 Invariant: Proves that an error in live SAM (HTTP 500 or network error)
    fails closed with passed=False and is_simulated=False, and NEVER silently falls back
    to simulated heuristic success.
    """
    import httpx
    from app.verification.l1_subject import L1SubjectChecker
    from app.config import InkLoopConfig

    cfg = InkLoopConfig(model_api_key="mock_secret_key_for_testing_12345")
    checker = L1SubjectChecker(config=cfg)
    valid_bytes = create_valid_textured_png(256, 256)

    # 1. Simulate HTTP 500 server error from live SAM endpoint
    class Mock500Response:
        status_code = 500
        text = "GPU cluster out of memory"

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Mock500Response())
    res_500 = checker.check(valid_bytes, is_simulated=False)
    assert res_500.passed is False
    assert res_500.is_simulated is False
    assert "Live SAM API returned status 500" in (res_500.reason or "")

    # 2. Simulate network exception
    def mock_raise(*args, **kwargs):
        raise httpx.ConnectTimeout("Connection to SAM model timed out")

    monkeypatch.setattr(httpx, "post", mock_raise)
    res_timeout = checker.check(valid_bytes, is_simulated=False)
    assert res_timeout.passed is False
    assert res_timeout.is_simulated is False
    assert "Live SAM API call exception" in (res_timeout.reason or "")

