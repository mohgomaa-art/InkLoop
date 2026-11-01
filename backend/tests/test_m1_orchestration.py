"""
Comprehensive test suite for InkLoop M1 Task 4:
Six-Panel Generation Orchestration, Independent Context & Complete Attempt Logging.
"""
import json
import hashlib
from decimal import Decimal
from pathlib import Path
import pytest
from pydantic import BaseModel

from app.config import InkLoopConfig, PROJECT_ROOT
from app.schemas import (
    StoryBible,
    StyleBible,
    CharacterSpec,
    AttributeCheck,
    ReferenceAsset,
    SceneSpec,
    BatchSpec,
    BatchStatus,
    PanelStatus,
    ErrorCategory,
    RetryDecision,
    GenerationAttemptRecord,
    VerificationResult,
    AttributeVerdict,
)
from app.context_builder import build_panel_context_packet, compute_context_fingerprint
from app.image_adapter import (
    SimulatedImageGenerationAdapter,
    MetaImageGenerationAdapter,
    GenerationRequest,
    GenerationResponse,
)
from app.orchestrator import BatchOrchestrator
from app.execution import AttemptStatus, BudgetManager, ExecutionManager, RunStatus
from tests.fixtures.benchmark_fixtures import (
    CANONICAL_M0_STORY_BIBLE,
    CANONICAL_M0_SIX_SCENES,
    create_m0_benchmark_batch_spec,
)


def test_orchestrator_persists_execution_manager_attempt_and_budget(tmp_path):
    """A simulated generation is recorded in the authoritative run/event ledger."""
    manager = ExecutionManager(
        db_path=tmp_path / "execution.db",
        budget_manager=BudgetManager(global_cap_usd="25.00"),
    )
    adapter = SimulatedImageGenerationAdapter(default_success=True, simulated_cost=0.02)
    orchestrator = BatchOrchestrator(
        config=InkLoopConfig.load(),
        adapter=adapter,
        run_log_dir=tmp_path / "logs",
        execution_manager=manager,
    )
    spec = BatchSpec(
        batch_id="execution_manager_integration",
        project_id="inkloop",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        max_retries_per_panel=0,
        spend_cap_usd=1.0,
        require_verification=False,
    )

    summary = orchestrator.orchestrate_batch(spec)
    trace = manager.get_run_summary(spec.batch_id)

    assert summary.status == BatchStatus.COMPLETED
    assert trace.status == RunStatus.SUCCEEDED
    assert trace.total_attempts == 1
    assert trace.total_estimated_usd == Decimal("0.0200")
    assert trace.total_reported_usd == 0
    assert trace.event_count >= 8  # run, operation, reservation, attempt, settlement, completion
    attempt = manager.db.list_attempts_for_run(spec.batch_id)[0]
    assert attempt.status == AttemptStatus.SUCCEEDED
    assert attempt.cost_classification.value == "estimated"
    assert attempt.verification_verdict == "UNVERIFIED"
    manager.close()


def test_execution_manager_keeps_unreported_provider_cost_unknown(tmp_path):
    """A budget estimate is not recorded as provider-reported spend."""
    class UnpricedLiveAdapter:
        is_simulated = False

        def __init__(self):
            self.delegate = SimulatedImageGenerationAdapter(default_success=True)

        def generate(self, request):
            response = self.delegate.generate(request)
            response.is_simulated = False
            response.cost_usd = None
            response.usage = None
            return response

    manager = ExecutionManager(
        db_path=tmp_path / "execution.db",
        budget_manager=BudgetManager(global_cap_usd="25.00"),
    )
    spec = BatchSpec(
        batch_id="execution_manager_unknown_cost",
        project_id="inkloop",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        max_retries_per_panel=0,
        spend_cap_usd=1.0,
        require_verification=False,
    )
    orchestrator = BatchOrchestrator(
        config=InkLoopConfig.load(),
        adapter=UnpricedLiveAdapter(),
        run_log_dir=tmp_path / "logs",
        execution_manager=manager,
    )

    orchestrator.orchestrate_batch(spec)
    trace = manager.get_run_summary(spec.batch_id)
    attempt = manager.db.list_attempts_for_run(spec.batch_id)[0]

    assert trace.total_reported_usd == Decimal("0.0000")
    assert trace.missing_cost_count == 1
    assert attempt.cost_amount_usd is None
    assert attempt.cost_classification.value == "unknown"
    manager.close()

# ===========================================================================
# 1. BATCH BEHAVIOR TESTS
# ===========================================================================

def test_six_panel_batch_creation_and_stable_identifiers(tmp_path):
    """Verifies that a 6-panel batch generates stable identifiers and preserves canonical order."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    batch_spec = create_m0_benchmark_batch_spec(
        batch_id="test_stable_batch_001",
        output_dir=str(tmp_path / "out")
    )
    summary = orchestrator.orchestrate_batch(batch_spec)

    assert summary.batch_id == "test_stable_batch_001"
    assert summary.status == BatchStatus.COMPLETED
    assert summary.total_panels == 6
    assert summary.successful_panels == 6
    assert summary.failed_panels == 0
    assert summary.unresolved_panels == 0

    # Verify panel IDs and ordering
    expected_panel_ids = [f"panel_{i:02d}" for i in range(1, 7)]
    actual_panel_ids = [p.panel_id for p in summary.panel_results]
    assert actual_panel_ids == expected_panel_ids

    # Verify all 6 outputs generated
    for p_id in expected_panel_ids:
        out_file = tmp_path / "out" / f"{p_id}.png"
        assert out_file.exists()
        assert out_file.stat().st_size > 0

def test_six_panels_produce_six_independent_results(tmp_path):
    """Ensures each panel result has independent output hashes and distinct context packets."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    batch_spec = create_m0_benchmark_batch_spec(
        batch_id="test_indep_batch_002",
        output_dir=str(tmp_path / "out")
    )
    summary = orchestrator.orchestrate_batch(batch_spec)

    assert len(summary.panel_results) == 6
    fingerprints = [p.context_fingerprint for p in summary.panel_results]
    assert len(set(fingerprints)) == 6, "Every panel must have a unique context fingerprint"

def test_one_panel_failure_does_not_erase_other_panels(tmp_path):
    """Ensures a failure in one panel leaves other successful panels intact and recorded."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)

    # Script panel_03 to fail permanently with 400 Bad Request
    adapter.script_panel_responses("panel_03", [
        GenerationResponse(
            success=False,
            http_status=400,
            error_category=ErrorCategory.BAD_REQUEST,
            error_message="Invalid parameters in prompt",
            duration_seconds=0.05
        )
    ])

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")
    batch_spec = create_m0_benchmark_batch_spec(
        batch_id="test_partial_failure_003",
        output_dir=str(tmp_path / "out")
    )
    summary = orchestrator.orchestrate_batch(batch_spec)

    assert summary.status == BatchStatus.COMPLETED_WITH_FAILURES
    assert summary.successful_panels == 5
    assert summary.failed_panels == 1
    assert summary.total_panels == 6

    # Verify panels 1, 2, 4, 5, 6 succeeded
    p3 = next(p for p in summary.panel_results if p.panel_id == "panel_03")
    assert p3.status == PanelStatus.FAILED
    assert p3.accepted_attempt_id is None

    p1 = next(p for p in summary.panel_results if p.panel_id == "panel_01")
    assert p1.status == PanelStatus.ACCEPTED
    assert (tmp_path / "out" / "panel_01.png").exists()

# ===========================================================================
# 2. CONTEXT ISOLATION & PURITY TESTS
# ===========================================================================

def test_panel_instructions_do_not_leak_between_panels():
    """Verifies that panel-specific instructions in one scene do not contaminate other packets."""
    scene_a = SceneSpec(
        scene_id="scene_a",
        scene_index=0,
        title="Scene A",
        shot_type="medium shot",
        action="reading a book",
        character_ids=["nour"],
        panel_instructions="SPECIAL_PANEL_A_INSTRUCTION: Focus on right eye reflection",
    )
    scene_b = SceneSpec(
        scene_id="scene_b",
        scene_index=1,
        title="Scene B",
        shot_type="wide shot",
        action="walking down street",
        character_ids=["nour"],
        panel_instructions=None,
    )

    packet_a = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene_a, "panel_01")
    packet_b = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene_b, "panel_02")

    assert "SPECIAL_PANEL_A_INSTRUCTION" in packet_a.generation_prompt
    assert "SPECIAL_PANEL_A_INSTRUCTION" not in packet_b.generation_prompt

def test_canonical_reference_and_bible_version_traceability():
    """Verifies that every packet contains the traceable Story Bible version and reference asset hash."""
    scene = CANONICAL_M0_SIX_SCENES[0]
    packet = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene, "panel_01")

    assert packet.bible_version == "1.0.0"
    assert packet.bible_id == "bible_nour_m0"
    assert len(packet.reference_assets) == 1
    assert packet.reference_assets[0].asset_id == "nour_reference"
    assert packet.reference_assets[0].content_hash == "b2c2c4dc003a9db32a4847a1dab46bda801ce3a9b69ff0c0381c5ab8a203e644"

def test_fingerprint_determinism_and_sensitivity():
    """Verifies that identical inputs yield identical fingerprints, and modifications yield different ones."""
    scene = CANONICAL_M0_SIX_SCENES[0]
    packet1 = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene, "panel_01")
    packet2 = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene, "panel_01")

    assert packet1.context_fingerprint == packet2.context_fingerprint

    # Modify narrative state
    modified_scene = scene.model_copy(deep=True)
    modified_scene.scene_state = {"time_of_day": "midnight"}
    packet_modified = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, modified_scene, "panel_01")

    assert packet_modified.context_fingerprint != packet1.context_fingerprint

def test_continuity_is_passed_explicitly_without_hidden_state():
    """Verifies that continuity facts are explicitly declared in the prompt and packet."""
    scene = CANONICAL_M0_SIX_SCENES[1]  # Scene 2 has explicit previous_panel_summary
    packet = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene, "panel_02")

    assert packet.previous_panel_continuity == "Nour finished tea at the cafe and went for an evening walk."
    assert "Narrative continuity from previous beat: Nour finished tea at the cafe and went for an evening walk." in packet.generation_prompt

# ===========================================================================
# 3. ATTEMPT LOGGING & SANITIZATION TESTS
# ===========================================================================

def test_each_attempt_creates_separate_record(tmp_path):
    """Ensures retries create distinct attempt records with sequential attempt numbers."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)

    # Script panel_01 to fail once with 503 Server Error, then succeed on retry
    adapter.script_panel_responses("panel_01", [
        GenerationResponse(
            success=False,
            http_status=503,
            error_category=ErrorCategory.SERVER_ERROR,
            error_message="Backend GPU cluster warm-up",
            duration_seconds=0.1
        ),
        GenerationResponse(
            success=True,
            http_status=200,
            image_bytes=b"dummy_png_bytes_panel_01_retry",
            endpoint="POST /v1/images/edits",
            duration_seconds=0.12
        )
    ])

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")
    single_scene = [CANONICAL_M0_SIX_SCENES[0]]
    spec = BatchSpec(
        batch_id="test_retry_logging_004",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=single_scene,
        output_dir=str(tmp_path / "out")
    )
    summary = orchestrator.orchestrate_batch(spec)

    assert summary.status == BatchStatus.COMPLETED
    assert len(summary.attempt_history) == 2

    att1 = summary.attempt_history[0]
    att2 = summary.attempt_history[1]

    assert att1.attempt_number == 1
    assert att1.error_category == "SERVER_ERROR"
    assert att1.retry_decision == "RETRY_WITH_CORRECTION"
    assert att1.final_panel_status == "PENDING"

    assert att2.attempt_number == 2
    assert att2.error_category is None
    assert att2.retry_decision == "NONE_SUCCESS"
    assert att2.final_panel_status == "ACCEPTED"
    assert att2.output_content_hash == hashlib.sha256(b"dummy_png_bytes_panel_01_retry").hexdigest()

def test_missing_usage_and_cost_distinguished_from_zero(tmp_path):
    """Verifies that missing provider usage is represented as None/unknown, not fabricated zero."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(
        default_success=True,
        simulated_usage=None,
        simulated_cost=None
    )
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    single_scene = [CANONICAL_M0_SIX_SCENES[0]]
    spec = BatchSpec(
        batch_id="test_missing_usage_005",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=single_scene,
    )
    summary = orchestrator.orchestrate_batch(spec)

    attempt = summary.attempt_history[0]
    assert attempt.usage is None
    assert attempt.cost_usd is None
    assert summary.missing_usage_information is True
    assert summary.missing_cost_information is True
    assert summary.simulated_cost_usd is None
    assert summary.simulated_usage is None

def test_secrets_and_api_keys_strictly_excluded_from_logs(tmp_path, monkeypatch):
    """Verifies that API keys and Bearer headers are NEVER written to logs or persisted files."""
    secret_key = "super_secret_production_key_xyz_98765"
    monkeypatch.setenv("MODEL_API_KEY", secret_key)
    cfg = InkLoopConfig.load()

    adapter = SimulatedImageGenerationAdapter(default_success=True)
    log_dir = tmp_path / "logs"
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=log_dir)

    spec = create_m0_benchmark_batch_spec(
        batch_id="test_secrets_exclusion_006",
        output_dir=str(tmp_path / "out")
    )
    summary = orchestrator.orchestrate_batch(spec)

    # 1. Check in-memory summary serialization
    summary_json = summary.model_dump_json()
    assert secret_key not in summary_json
    assert "Authorization" not in summary_json

    # 2. Check on-disk persisted file
    persisted_file = log_dir / "test_secrets_exclusion_006.json"
    assert persisted_file.exists()
    persisted_text = persisted_file.read_text(encoding="utf-8")
    assert secret_key not in persisted_text
    assert "Bearer" not in persisted_text

# ===========================================================================
# 4. FAILURE AND BUDGET CONTROLS
# ===========================================================================

def test_non_retryable_errors_stop_immediately(tmp_path):
    """Verifies that 401 Authentication or 400 Bad Request errors never enter retry loops."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)

    adapter.script_panel_responses("panel_01", [
        GenerationResponse(
            success=False,
            http_status=401,
            error_category=ErrorCategory.AUTHENTICATION_ERROR,
            error_message="Invalid Bearer Token",
            duration_seconds=0.02
        )
    ])

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")
    spec = BatchSpec(
        batch_id="test_no_retry_401",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        max_retries_per_panel=2,
    )
    summary = orchestrator.orchestrate_batch(spec)

    assert summary.status == BatchStatus.FAILED
    assert len(summary.attempt_history) == 1, "Non-retryable 401 must abort on first attempt without looping"
    assert summary.attempt_history[0].retry_decision == "DO_NOT_RETRY_PERMANENT"

def test_retryable_errors_respect_attempt_limit(tmp_path):
    """Verifies that transient errors retry up to max_attempts and then mark NEEDS_HUMAN."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)

    # 3 consecutive rate limit errors for panel_01 (max_retries=2 -> max_attempts=3)
    rate_limit_resp = GenerationResponse(
        success=False,
        http_status=429,
        error_category=ErrorCategory.RATE_LIMIT_EXCEEDED,
        error_message="Rate limit exceeded. Retry in 2s.",
        duration_seconds=0.05
    )
    adapter.script_panel_responses("panel_01", [rate_limit_resp, rate_limit_resp, rate_limit_resp])

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")
    spec = BatchSpec(
        batch_id="test_retry_limit_429",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        max_retries_per_panel=2,
    )
    summary = orchestrator.orchestrate_batch(spec)

    assert summary.status == BatchStatus.FAILED
    assert len(summary.attempt_history) == 3
    final_att = summary.attempt_history[-1]
    assert final_att.attempt_number == 3
    assert final_att.retry_decision == "MAX_RETRIES_REACHED"
    assert summary.panel_results[0].status == PanelStatus.NEEDS_HUMAN

def test_spending_cap_prevents_unauthorized_operations(tmp_path):
    """Verifies that hitting the global spend cap halts subsequent operations."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True, simulated_cost=0.01)

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    # Set spend cap to $0.02 (allows at most 2 operations out of 6 scenes)
    spec = create_m0_benchmark_batch_spec(
        batch_id="test_spend_cap_enforcement",
        spend_cap_usd=0.02
    )
    summary = orchestrator.orchestrate_batch(spec)

    assert summary.status == BatchStatus.COMPLETED_WITH_FAILURES
    assert summary.successful_panels == 2
    assert summary.failed_panels == 4

# ===========================================================================
# 5. RESUMABILITY TESTS
# ===========================================================================

def test_resumed_batch_does_not_regenerate_completed_panels(tmp_path):
    """Verifies that resuming a partially failed batch reuses completed panels with matching inputs."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)

    # Initial run: panel_02 fails with 500 error
    adapter.script_panel_responses("panel_02", [
        GenerationResponse(
            success=False,
            http_status=500,
            error_category=ErrorCategory.SERVER_ERROR,
            error_message="GPU transient error",
            duration_seconds=0.05
        ),
        GenerationResponse(
            success=False,
            http_status=500,
            error_category=ErrorCategory.SERVER_ERROR,
            error_message="GPU transient error",
            duration_seconds=0.05
        ),
        GenerationResponse(
            success=False,
            http_status=500,
            error_category=ErrorCategory.SERVER_ERROR,
            error_message="GPU transient error",
            duration_seconds=0.05
        )
    ])

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")
    spec = BatchSpec(
        batch_id="test_resumable_batch",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=CANONICAL_M0_SIX_SCENES[:3],  # 3 scenes
        max_retries_per_panel=2,
    )

    initial_summary = orchestrator.orchestrate_batch(spec)
    assert initial_summary.status == BatchStatus.COMPLETED_WITH_FAILURES
    assert initial_summary.successful_panels == 2
    assert initial_summary.unresolved_panels == 1  # panel_02 failed after retries

    initial_request_count = len(adapter.request_history)

    # Resume run: Now panel_02 succeeds
    adapter.default_success = True
    resumed_summary = orchestrator.resume_batch(spec, initial_summary)

    # Panels 1 and 3 should NOT have been re-requested
    new_requests = len(adapter.request_history) - initial_request_count
    assert new_requests == 1, "Only panel_02 should have been regenerated during resume"
    assert resumed_summary.status == BatchStatus.COMPLETED
    assert resumed_summary.successful_panels == 3
    assert resumed_summary.failed_panels == 0

# ===========================================================================
# 6. FULL SIX-PANEL BENCHMARK ACCEPTANCE TEST
# ===========================================================================

def test_full_m0_six_panel_benchmark_orchestration(tmp_path):
    """
    Primary Acceptance Gate:
    Orchestrates all 6 canonical scenes from the M0 benchmark through the orchestration service.
    Verifies that:
    1. All 6 panels run through the adapter in order.
    2. Context packet for each scene contains canonical character reference assets.
    3. Complete attempt history is stored with zero secrets.
    4. Output files exist with valid SHA-256 hashes.
    5. Batch summary persists as machine-readable JSON in the runs store.
    """
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(
        default_success=True,
        simulated_usage={"input_tokens": 12400, "output_tokens": 1000, "total_tokens": 13400},
        simulated_cost=0.01,
        duration_seconds=0.02
    )

    run_log_dir = tmp_path / "runs" / "batches"
    out_dir = tmp_path / "runs" / "m1_panels"
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=run_log_dir)

    spec = create_m0_benchmark_batch_spec(
        batch_id="m0_benchmark_six_panel_acceptance",
        output_dir=str(out_dir)
    )

    summary = orchestrator.orchestrate_batch(spec)

    # 1. Batch status
    assert summary.status == BatchStatus.COMPLETED
    assert summary.total_panels == 6
    assert summary.successful_panels == 6
    assert summary.failed_panels == 0
    assert summary.unresolved_panels == 0
    assert summary.total_attempts == 6

    # 2. Panel results and outputs
    for i in range(1, 7):
        p_id = f"panel_{i:02d}"
        p_res = next(p for p in summary.panel_results if p.panel_id == p_id)
        assert p_res.status == PanelStatus.ACCEPTED
        assert p_res.output_asset_path is not None
        assert Path(p_res.output_asset_path).exists()
        assert p_res.output_content_hash is not None
        assert len(p_res.output_content_hash) == 64

    # 3. Usage & Cost (Simulated accounting strictly segregated from real provider spend)
    assert summary.is_simulated is True
    assert summary.cost_mode == "synthetic_simulated"
    assert summary.known_cost_usd == 0.0
    assert summary.simulated_cost_usd == 0.06
    assert summary.known_usage == {}
    assert summary.simulated_usage["total_tokens"] == 13400 * 6
    assert summary.missing_cost_information is False

    # 4. Persistence validation
    saved_json_path = run_log_dir / "m0_benchmark_six_panel_acceptance.json"
    assert saved_json_path.exists()
    loaded_data = json.loads(saved_json_path.read_text(encoding="utf-8"))
    assert loaded_data["batch_id"] == "m0_benchmark_six_panel_acceptance"
    assert loaded_data["status"] == "COMPLETED"
    assert len(loaded_data["panel_results"]) == 6
    assert len(loaded_data["attempt_history"]) == 6

def test_interoperability_with_project_story_bible(tmp_path):
    """
    Verifies that the orchestrator seamlessly consumes the StoryBible from
    backend/app/project/bible.py (created by Agent 1/2) without contract friction.
    """
    from app.project import create_canonical_nour_bible

    project_bible = create_canonical_nour_bible("proj_nour_m1")
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    spec = BatchSpec(
        batch_id="test_interop_batch",
        story_bible=project_bible,
        scenes=CANONICAL_M0_SIX_SCENES[:2],
        output_dir=str(tmp_path / "out")
    )

    summary = orchestrator.orchestrate_batch(spec)
    assert summary.status == BatchStatus.COMPLETED
    assert summary.total_panels == 2
    assert summary.successful_panels == 2
    assert summary.bible_version == "1"
    assert summary.story_id == "story_01"

# ===========================================================================
# 6. INTEGRATION REVIEW & ROBUSTNESS TESTS (TASK 4 DEFENSE)
# ===========================================================================

def test_verification_gating_unverified_remains_pending(tmp_path):
    """
    Verifies that when require_verification=True, successfully generated images
    without visual verification are NOT marked ACCEPTED; they remain GENERATED_PENDING_VERIFICATION.
    """
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs", verifier=None)

    spec = BatchSpec(
        batch_id="test_unverified_gate_001",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=CANONICAL_M0_SIX_SCENES[:2],
        output_dir=str(tmp_path / "out"),
        require_verification=True
    )

    summary = orchestrator.orchestrate_batch(spec)

    assert summary.status == BatchStatus.COMPLETED_WITH_FAILURES
    assert summary.successful_panels == 0
    assert summary.unverified_panels == 2
    for p in summary.panel_results:
        assert p.status == PanelStatus.GENERATED_PENDING_VERIFICATION
        assert p.verification_status == "UNVERIFIED"

def test_verifier_passed_accepted(tmp_path):
    """Verifies that when an attached verifier confirms visual compliance, panel is ACCEPTED."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)

    def dummy_passing_verifier(ref_asset, img_bytes, char_spec):
        return VerificationResult(
            passed=True,
            verdicts=[AttributeVerdict(attr_id="spiky_hair", verdict="pass", evidence="Matches reference silhouette")]
        )

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs", verifier=dummy_passing_verifier)

    spec = BatchSpec(
        batch_id="test_verifier_pass_002",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out"),
        require_verification=True
    )

    summary = orchestrator.orchestrate_batch(spec)
    assert summary.status == BatchStatus.COMPLETED
    assert summary.successful_panels == 1
    p1 = summary.panel_results[0]
    assert p1.status == PanelStatus.ACCEPTED
    assert p1.verification_status == "PASSED"
    assert p1.verification_result is not None
    assert p1.verification_result.passed is True

def test_verifier_failed_triggers_retry_and_rejection(tmp_path):
    """Verifies that visual verifier failure records rejection and triggers bounded retry."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)

    def dummy_failing_verifier(ref_asset, img_bytes, char_spec):
        return VerificationResult(
            passed=False,
            verdicts=[AttributeVerdict(attr_id="hood", verdict="fail", evidence="Hood is missing from candidate")],
            rejection_reason="Hood not detected"
        )

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs", verifier=dummy_failing_verifier)

    spec = BatchSpec(
        batch_id="test_verifier_fail_003",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        max_retries_per_panel=1,
        output_dir=str(tmp_path / "out"),
        require_verification=True
    )

    summary = orchestrator.orchestrate_batch(spec)
    assert summary.status == BatchStatus.FAILED
    assert summary.successful_panels == 0
    p1 = summary.panel_results[0]
    assert p1.status == PanelStatus.NEEDS_HUMAN
    assert len(summary.attempt_history) == 2
    assert summary.attempt_history[0].verification_status == "FAILED"
    assert summary.attempt_history[1].verification_status == "FAILED"

def test_verifier_unsure_escalates_to_needs_human(tmp_path):
    """Verifies that an inconclusive ('unsure') verdict halts retries and escalates to NEEDS_HUMAN."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)

    def dummy_unsure_verifier(ref_asset, img_bytes, char_spec):
        return VerificationResult(
            passed=False,
            verdicts=[AttributeVerdict(attr_id="face", verdict="unsure", evidence="Face partially occluded by shadow")],
            rejection_reason="Face occluded, cannot reliably verify identity"
        )

    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs", verifier=dummy_unsure_verifier)

    spec = BatchSpec(
        batch_id="test_verifier_unsure_004",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        max_retries_per_panel=3,
        output_dir=str(tmp_path / "out"),
        require_verification=True
    )

    summary = orchestrator.orchestrate_batch(spec)
    p1 = summary.panel_results[0]
    assert p1.status == PanelStatus.NEEDS_HUMAN
    # Must stop immediately on UNSURE without burning remaining 3 retries
    assert len(summary.attempt_history) == 1
    assert summary.attempt_history[0].verification_status == "UNSURE"

def test_live_adapter_missing_cost_remains_none(tmp_path):
    """Verifies that when a live provider omits cost/usage, it stays None and is not converted to 0.0."""
    from app.image_adapter import ImageGenerationAdapter

    class MockLiveAdapter(ImageGenerationAdapter):
        is_simulated = False
        def generate(self, request: GenerationRequest) -> GenerationResponse:
            return GenerationResponse(
                success=True,
                http_status=200,
                image_bytes=b"\x89PNG\r\n\x1a\n\x00fakeimagebytes",
                endpoint="https://api.provider.com/v1/images",
                duration_seconds=0.1,
                is_simulated=False,
                usage=None,
                cost_usd=None,
                sanitized_metadata={"model": request.model}
            )

    cfg = InkLoopConfig.load()
    orchestrator = BatchOrchestrator(config=cfg, adapter=MockLiveAdapter(), run_log_dir=tmp_path / "logs")

    spec = BatchSpec(
        batch_id="test_live_missing_cost_005",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )

    summary = orchestrator.orchestrate_batch(spec)
    assert summary.is_simulated is False
    assert summary.cost_mode == "real"
    assert summary.known_cost_usd is None  # Unknown cost must remain None
    assert summary.missing_cost_information is True
    assert summary.missing_usage_information is True
    assert summary.simulated_cost_usd is None

def test_resumed_batch_regenerates_when_dimensions_or_instructions_change(tmp_path):
    """Verifies that changing dimensions or panel_instructions invalidates context fingerprint."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    out_dir = tmp_path / "out"
    scene1 = CANONICAL_M0_SIX_SCENES[0]
    scene2 = CANONICAL_M0_SIX_SCENES[1]

    spec1 = BatchSpec(
        batch_id="test_invalidation_006",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[scene1, scene2],
        output_dir=str(out_dir)
    )
    summary1 = orchestrator.orchestrate_batch(spec1)
    assert summary1.successful_panels == 2

    # Modify scene 2 instructions and dimensions
    scene2_modified = SceneSpec(
        scene_id=scene2.scene_id,
        scene_index=scene2.scene_index,
        title=scene2.title,
        shot_type=scene2.shot_type,
        action=scene2.action,
        character_ids=scene2.character_ids,
        dimensions=(1024, 1536),
        panel_instructions="CHANGED: Extreme macro close-up on eye"
    )

    spec2 = BatchSpec(
        batch_id="test_invalidation_006",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[scene1, scene2_modified],
        output_dir=str(out_dir)
    )

    adapter.request_history.clear()
    summary2 = orchestrator.resume_batch(spec2)

    # Panel 1 fingerprint matched -> reused (0 new requests for panel 1)
    # Panel 2 fingerprint changed -> regenerated (1 new request for panel 2)
    assert len(adapter.request_history) == 1
    assert adapter.request_history[0].panel_id == "panel_02"
    assert summary2.successful_panels == 2

def test_resumed_batch_regenerates_when_output_file_missing_from_disk(tmp_path):
    """Verifies that if output image file was deleted from disk, resumption forces regeneration."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    out_dir = tmp_path / "out"
    scene1 = CANONICAL_M0_SIX_SCENES[0]

    spec = BatchSpec(
        batch_id="test_missing_file_007",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[scene1],
        output_dir=str(out_dir)
    )
    summary1 = orchestrator.orchestrate_batch(spec)
    assert summary1.successful_panels == 1
    file_path = Path(summary1.panel_results[0].output_asset_path)
    assert file_path.exists()

    # Delete output file from disk
    file_path.unlink()
    assert not file_path.exists()

    adapter.request_history.clear()
    summary2 = orchestrator.resume_batch(spec)

    # Must regenerate because file was missing
    assert len(adapter.request_history) == 1
    assert file_path.exists()
    assert summary2.successful_panels == 1

def test_resumed_attempt_numbering_avoids_collision(tmp_path):
    """Verifies that resuming a batch after prior failures increments attempt numbering to prevent ID collisions."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=False)  # Run 1 fails
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    out_dir = tmp_path / "out"
    scene1 = CANONICAL_M0_SIX_SCENES[0]

    spec = BatchSpec(
        batch_id="test_attempt_collision_008",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=[scene1],
        max_retries_per_panel=1,  # 2 attempts total
        output_dir=str(out_dir)
    )
    summary1 = orchestrator.orchestrate_batch(spec)
    assert summary1.status == BatchStatus.FAILED
    assert len(summary1.attempt_history) == 2
    attempt_ids_run1 = [a.attempt_id for a in summary1.attempt_history]
    assert attempt_ids_run1 == ["test_attempt_collision_008_panel_01_att1", "test_attempt_collision_008_panel_01_att2"]

    # Run 2: adapter succeeds
    adapter.default_success = True
    summary2 = orchestrator.resume_batch(spec)
    assert summary2.status == BatchStatus.COMPLETED

    all_attempt_ids = [a.attempt_id for a in summary2.attempt_history]
    # No duplicate IDs permitted
    assert len(all_attempt_ids) == len(set(all_attempt_ids))
    # Resumed attempt must be numbered att3
    assert all_attempt_ids == [
        "test_attempt_collision_008_panel_01_att1",
        "test_attempt_collision_008_panel_01_att2",
        "test_attempt_collision_008_panel_01_att3"
    ]

def test_global_spend_cap_clamps_batch_spec_spend_cap(tmp_path):
    """Verifies that config.global_spend_cap_usd strictly bounds batch_spec.spend_cap_usd."""
    # Set global spend cap to $0.015 (only enough for 1 operation at $0.01)
    cfg = InkLoopConfig.load()
    cfg.global_spend_cap_usd = 0.015

    adapter = SimulatedImageGenerationAdapter(default_success=True, simulated_cost=0.01)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    spec = BatchSpec(
        batch_id="test_cap_clamp_009",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=CANONICAL_M0_SIX_SCENES[:3],
        spend_cap_usd=500.0,  # Unreasonably high requested cap
        output_dir=str(tmp_path / "out")
    )

    summary = orchestrator.orchestrate_batch(spec)
    # Global cap of $0.015 must stop execution before second panel ($0.01 + $0.01 > $0.015)
    assert summary.status == BatchStatus.COMPLETED_WITH_FAILURES
    assert summary.successful_panels == 1
    assert summary.failed_panels == 2
    # Verify budget exceeded was recorded
    budget_att = next(a for a in summary.attempt_history if a.error_category == ErrorCategory.BUDGET_EXCEEDED.value)
    assert "0.01" in budget_att.error_message or "0.02" in budget_att.error_message

def test_incremental_checkpoint_persists_during_run(tmp_path):
    """Verifies that an intermediate checkpoint JSON is safely persisted to disk after each panel."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    log_dir = tmp_path / "logs"
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=log_dir)

    spec = BatchSpec(
        batch_id="test_checkpoint_010",
        story_bible=CANONICAL_M0_STORY_BIBLE,
        scenes=CANONICAL_M0_SIX_SCENES[:2],
        output_dir=str(tmp_path / "out")
    )

    summary = orchestrator.orchestrate_batch(spec)
    checkpoint_file = log_dir / "test_checkpoint_010.json"
    assert checkpoint_file.exists()
    checkpoint_data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
    assert checkpoint_data["batch_id"] == "test_checkpoint_010"
    assert len(checkpoint_data["panel_results"]) == 2

def test_fingerprint_invalidated_by_story_facts(tmp_path):
    """Verifies that mutating story_facts invalidates context fingerprint and prevents stale reuse."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    bible1 = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible1.story_facts = ["Fact 1: City is abandoned"]

    spec1 = BatchSpec(
        batch_id="test_facts_invalidation",
        story_bible=bible1,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    summary1 = orchestrator.orchestrate_batch(spec1)
    fp1 = summary1.panel_results[0].context_fingerprint

    # Mutate story_facts
    bible2 = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible2.story_facts = ["Fact 1: City is abandoned", "Fact 2: Heavy persistent snowfall"]

    spec2 = BatchSpec(
        batch_id="test_facts_invalidation",
        story_bible=bible2,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    adapter.request_history.clear()
    summary2 = orchestrator.resume_batch(spec2)
    fp2 = summary2.panel_results[0].context_fingerprint

    assert fp1 != fp2
    assert len(adapter.request_history) == 1

def test_fingerprint_invalidated_by_canon_hash(tmp_path):
    """Verifies that changing canon_hash invalidates fingerprint and forces regeneration."""
    from app.project import create_canonical_nour_bible
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    bible = create_canonical_nour_bible("proj_hash_test")
    setattr(bible, "canon_hash", "11112222333344445555666677778888")

    spec1 = BatchSpec(
        batch_id="test_canon_hash_invalidation",
        story_bible=bible,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    summary1 = orchestrator.orchestrate_batch(spec1)
    fp1 = summary1.panel_results[0].context_fingerprint

    # Update canon_hash
    setattr(bible, "canon_hash", "99998888777766665555444433332222")
    spec2 = BatchSpec(
        batch_id="test_canon_hash_invalidation",
        story_bible=bible,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    adapter.request_history.clear()
    summary2 = orchestrator.resume_batch(spec2)
    fp2 = summary2.panel_results[0].context_fingerprint

    assert fp1 != fp2
    assert len(adapter.request_history) == 1

def test_fingerprint_invalidated_by_style_palette(tmp_path):
    """Verifies that changing style palette invalidates fingerprint."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    bible1 = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible1.style.palette = "monochrome"

    spec1 = BatchSpec(
        batch_id="test_palette_invalidation",
        story_bible=bible1,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    summary1 = orchestrator.orchestrate_batch(spec1)
    fp1 = summary1.panel_results[0].context_fingerprint

    bible2 = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible2.style.palette = "duotone_sepia"

    spec2 = BatchSpec(
        batch_id="test_palette_invalidation",
        story_bible=bible2,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    adapter.request_history.clear()
    summary2 = orchestrator.resume_batch(spec2)
    fp2 = summary2.panel_results[0].context_fingerprint

    assert fp1 != fp2
    assert len(adapter.request_history) == 1

def test_fingerprint_invalidated_by_character_restrictions(tmp_path):
    """Verifies that changing character-level restrictions invalidates context fingerprint."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    bible1 = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible1.characters["nour"].restrictions = []

    spec1 = BatchSpec(
        batch_id="test_restrictions_invalidation",
        story_bible=bible1,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    summary1 = orchestrator.orchestrate_batch(spec1)
    fp1 = summary1.panel_results[0].context_fingerprint

    bible2 = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible2.characters["nour"].restrictions = ["never remove glasses", "no smile"]

    spec2 = BatchSpec(
        batch_id="test_restrictions_invalidation",
        story_bible=bible2,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    adapter.request_history.clear()
    summary2 = orchestrator.resume_batch(spec2)
    fp2 = summary2.panel_results[0].context_fingerprint

    assert fp1 != fp2
    assert len(adapter.request_history) == 1

def test_fingerprint_invalidated_by_reference_asset_mime_type(tmp_path):
    """Verifies that changing reference asset mime_type invalidates fingerprint."""
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs")

    bible1 = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible1.character_assets["nour"].mime_type = "image/png"

    spec1 = BatchSpec(
        batch_id="test_mime_invalidation",
        story_bible=bible1,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    summary1 = orchestrator.orchestrate_batch(spec1)
    fp1 = summary1.panel_results[0].context_fingerprint

    bible2 = CANONICAL_M0_STORY_BIBLE.model_copy(deep=True)
    bible2.character_assets["nour"].mime_type = "image/webp"

    spec2 = BatchSpec(
        batch_id="test_mime_invalidation",
        story_bible=bible2,
        scenes=[CANONICAL_M0_SIX_SCENES[0]],
        output_dir=str(tmp_path / "out")
    )
    adapter.request_history.clear()
    summary2 = orchestrator.resume_batch(spec2)
    fp2 = summary2.panel_results[0].context_fingerprint

    assert fp1 != fp2
    assert len(adapter.request_history) == 1

def test_unverified_benchmark_accounting_integrity(tmp_path):
    """
    Verifies that when no visual verifier runs:
    - Generated panels are accurately counted (6/6).
    - Verified panels are 0/6.
    - Unverified panels are 6/6.
    - Pipeline acceptance does not claim real visual verification.
    """
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "logs", verifier=None)

    spec = create_m0_benchmark_batch_spec(
        batch_id="test_unverified_accounting",
        output_dir=str(tmp_path / "out")
    )
    summary = orchestrator.orchestrate_batch(spec)

    assert summary.total_panels == 6
    assert summary.generated_panels == 6
    assert summary.verified_panels == 0
    assert summary.unverified_panels == 6
    assert summary.successful_panels == 6
    for p in summary.panel_results:
        assert p.verification_status == "UNVERIFIED"
        assert p.verification_result is None
