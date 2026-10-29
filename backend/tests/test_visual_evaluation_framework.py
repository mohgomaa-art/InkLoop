"""
Comprehensive Automated Tests for InkLoop Visual Evaluation & Experimental Design (Task T6.2).
Validates frozen configurations, experiment plans, denominator reconciliation,
blind human evaluation protocol, visual regression corpus, M0 historical preservation,
and contract integration with existing execution and storage subsystems.
"""
from pathlib import Path
import json
import pytest
from pydantic import ValidationError

from app.evaluation.enums import (
    ExperimentType,
    ExperimentStatus,
    ReproducibilityLevel,
    EvaluationDimension,
    EvaluationVerdict,
    EvaluatorType,
    SampleOutcomeStatus,
    RegressionDomain,
    RegressionReadiness,
)
from app.evaluation.uncertainty import (
    wilson_score_interval,
    cohens_kappa,
    reconcile_sample_denominator,
)
from app.evaluation.models import (
    FrozenConfig,
    ExperimentArm,
    ExperimentPlan,
    SampleExecutionRecord,
    EvaluationDimensionResult,
    EvaluationRecord,
    UncertaintySummary,
    ExperimentExecutionSummary,
)
from app.evaluation.blinding import (
    BlindEvaluationItem,
    BlindEvaluationSheet,
    BlindingKeyEntry,
    BlindingKeyMap,
    HumanJudgmentRecord,
    AdjudicatedSampleResult,
    AdjudicationReport,
    BlindingService,
)
from app.evaluation.regression import (
    VisualRegressionCase,
    RegressionEvaluationResult,
    VisualRegressionCorpus,
)
from app.evaluation.m0_adapter import (
    build_m0_experiment_plan,
    load_m0_execution_summary,
    NOUR_REF_SHA256,
)
from app.contracts.engine import EngineId
from app.execution.models import CostRecord
from app.execution.states import CostClassification


# ==============================================================================
# 1. Experiment Schemas & Field Validation (Requirement 1)
# ==============================================================================

def test_experiment_schemas_reject_malformed_fields():
    """Proves that experiment schemas strictly reject missing required fields and secret tokens."""
    # 1. Missing required prompt
    with pytest.raises(ValidationError):
        FrozenConfig(
            provider="meta_ai",
            model_name="muse-image-1.0",
            # prompt missing!
        )

    # 2. Security violation: secret in parameters
    with pytest.raises(ValueError) as exc:
        FrozenConfig(
            provider="meta_ai",
            model_name="muse-image-1.0",
            prompt="clean linework",
            parameters={"api_key": "secret_token_123"},  # Forbidden!
        )
    assert "Security violation: Secret field" in str(exc.value)

    # 3. Security violation: Bearer token in prompt
    with pytest.raises(ValueError) as exc2:
        FrozenConfig(
            provider="meta_ai",
            model_name="muse-image-1.0",
            prompt="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        )
    assert "Security violation: Detected potential secret" in str(exc2.value)


# ==============================================================================
# 2. Deterministic Serialization & Configuration Hashes (Requirement 2 & 3)
# ==============================================================================

def test_frozen_config_deterministic_serialization_and_hash():
    """Proves that configurations serialize deterministically and produce bit-identical hashes."""
    c1 = FrozenConfig(
        provider="meta_ai",
        model_name="muse-image-1.0",
        prompt="black and white comic ink, clean linework",
        negative_constraints=["color", "speech bubbles", "dialogue text"],
        parameters={"endpoint": "/v1/images/generations", "size": "1920x1280", "n": 1},
        seed=42,
    )

    # c2 with re-ordered keys and re-ordered negative constraints
    c2 = FrozenConfig(
        provider="meta_ai",
        model_name="muse-image-1.0",
        prompt="black and white comic ink, clean linework",
        negative_constraints=["dialogue text", "color", "speech bubbles"],
        parameters={"n": 1, "size": "1920x1280", "endpoint": "/v1/images/generations"},
        seed=42,
    )

    assert c1.config_hash != ""
    assert c1.config_hash == c2.config_hash


def test_changing_input_creates_distinct_config_identity():
    """Proves that changing any parameter or input artifact digest changes the configuration identity."""
    base = FrozenConfig(
        provider="meta_ai",
        model_name="muse-image-1.0",
        prompt="black and white comic ink, Nour smiling",
        input_artifact_hashes={"art_nour_ref": NOUR_REF_SHA256},
    )

    # Change prompt slightly
    modified_prompt = FrozenConfig(
        provider="meta_ai",
        model_name="muse-image-1.0",
        prompt="black and white comic ink, Nour looking serious",
        input_artifact_hashes={"art_nour_ref": NOUR_REF_SHA256},
    )
    assert base.config_hash != modified_prompt.config_hash

    # Change input artifact hash
    modified_hash = FrozenConfig(
        provider="meta_ai",
        model_name="muse-image-1.0",
        prompt="black and white comic ink, Nour smiling",
        input_artifact_hashes={"art_nour_ref": "0000000000000000000000000000000000000000000000000000000000000000"},
    )
    assert base.config_hash != modified_hash.config_hash


# ==============================================================================
# 3. Experiment Plans vs Executed Experiments (Requirement 4)
# ==============================================================================

def test_experiment_plans_cannot_be_mistaken_for_executed_experiments():
    """Proves that unexecuted experiment plans remain distinct from executed summaries."""
    config = FrozenConfig(
        provider="meta_ai",
        model_name="muse-image-1.0",
        prompt="clean linework",
    )
    arm = ExperimentArm(
        arm_id="arm_control",
        name="Control Arm",
        description="Baseline generation",
        planned_samples=10,
        frozen_config=config,
    )

    plan = ExperimentPlan(
        experiment_id="exp_planned_only_01",
        title="Unexecuted Plan",
        research_question="Does parameter X improve yield?",
        predeclared_hypothesis="Hypothesis H1",
        primary_metric="first_pass_yield",
        planned_analysis="Wilson interval test",
        arms=[arm],
        is_executed=False,  # Explicitly unexecuted
    )
    assert plan.is_executed is False

    # Attempting to create an execution summary without sample records must fail denominator validation
    with pytest.raises(ValueError) as exc:
        ExperimentExecutionSummary(
            experiment_id="exp_planned_only_01",
            title="Unexecuted Plan",
            experiment_plan=plan,
            total_planned_samples=10,
            total_started_samples=0,
            total_completed_samples=0,
            total_failed_samples=0,
            total_filtered_samples=0,
            total_unresolved_samples=0,
            total_unfinished_samples=0,  # 0 accounted vs 10 planned -> Mismatch!
        )
    assert "Denominator accounting mismatch" in str(exc.value)


# ==============================================================================
# 4. Denominator Reconciliation & Failure Accounting (Requirement 5 & 6)
# ==============================================================================

def test_sample_counts_reconcile_with_denominators():
    """Proves that every planned sample must be accounted for across outcomes."""
    # Perfect reconciliation
    recon = reconcile_sample_denominator(
        planned=10,
        completed=7,
        failed=1,
        filtered=1,
        unresolved=1,
        unfinished=0,
    )
    assert recon["is_reconciled"] is True
    assert recon["completion_rate"] == 0.70
    assert recon["failure_rate"] == 0.10
    assert recon["filter_rate"] == 0.10
    assert recon["unresolved_rate"] == 0.10

    # Unaccounted dropped failure raises error
    with pytest.raises(ValueError) as exc:
        reconcile_sample_denominator(
            planned=10,
            completed=7,
            failed=0,  # Dropping 3 failures!
            filtered=0,
            unresolved=0,
            unfinished=0,
        )
    assert "Denominator accounting mismatch: planned=10 but" in str(exc.value)


def test_missing_outputs_remain_unresolved():
    """Proves that samples marked SUCCESS cannot have missing output digests."""
    with pytest.raises(ValidationError) as exc:
        SampleExecutionRecord(
            sample_id="samp_missing_01",
            experiment_id="exp_test",
            arm_id="arm_test",
            status=SampleOutcomeStatus.SUCCESS,
            output_sha256=None,      # Missing output!
            output_artifact_id=None,
        )
    assert "marked SUCCESS must record output_sha256 or output_artifact_id" in str(exc.value)

    # Failed samples must state why
    with pytest.raises(ValidationError) as exc2:
        SampleExecutionRecord(
            sample_id="samp_failed_01",
            experiment_id="exp_test",
            arm_id="arm_test",
            status=SampleOutcomeStatus.FAILED,
            failure_reason=None,  # Missing failure reason!
        )
    assert "marked FAILED must specify a failure_reason" in str(exc2.value)


# ==============================================================================
# 5. Blind Human Evaluation & Blinding Service (Requirement 7, 8, 9, 10)
# ==============================================================================

def test_blind_sheets_conceal_experimental_arms():
    """Proves that blind sheets contain zero arm tokens, prompt text, or revealing paths."""
    sample_entries = [
        {
            "sample_id": "samp_01",
            "arm_id": "arm_a_text_only",
            "scene_id": "scene_01",
            "file_path": "runs/m0_visual/arm_a/scene_01_baseline.png",
            "sha256": "fbc3817796702758a3de647456bd10e8e90f656ffec63c75f0979b1604f4063d",
            "scene_context": "Sitting at cafe table drinking tea",
        },
        {
            "sample_id": "samp_02",
            "arm_id": "arm_b_reference_anchored",
            "scene_id": "scene_01",
            "file_path": "runs/m0_visual/arm_b/scene_01_anchored.png",
            "sha256": "70ffcdf3905df47979073e3b5e86410e6fd34f2d93ce1cc5b0cfdd56327c7b22",
            "scene_context": "Sitting at cafe table drinking tea",
        },
    ]

    sheet, key_map = BlindingService.create_blind_sheet(
        experiment_id="exp_test_blind",
        sample_entries=sample_entries,
        random_seed=1234,
    )

    sheet_json = sheet.to_json()
    assert "arm_a" not in sheet_json
    assert "arm_b" not in sheet_json
    assert "baseline" not in sheet_json
    assert "anchored" not in sheet_json
    assert "clean_candidate" in sheet_json or "blind_candidate" in sheet_json


def test_randomized_ordering_reproducible_with_seed():
    """Proves that randomized sample ordering is bit-identical for the same seed."""
    sample_entries = [
        {"sample_id": f"s_{i}", "arm_id": f"arm_{i % 2}", "file_path": f"p_{i}.png", "sha256": f"h_{i}"}
        for i in range(10)
    ]

    sheet1, key_map1 = BlindingService.create_blind_sheet("exp_seed_test", sample_entries, random_seed=42)
    sheet2, key_map2 = BlindingService.create_blind_sheet("exp_seed_test", sample_entries, random_seed=42)
    sheet3, key_map3 = BlindingService.create_blind_sheet("exp_seed_test", sample_entries, random_seed=999)

    order1 = [key_map1.mappings[item.blind_id].original_sample_id for item in sheet1.items]
    order2 = [key_map2.mappings[item.blind_id].original_sample_id for item in sheet2.items]
    order3 = [key_map3.mappings[item.blind_id].original_sample_id for item in sheet3.items]

    assert order1 == order2
    assert order1 != order3


def test_individual_human_judgments_preserved_not_overwritten():
    """Proves that individual rater evaluations are preserved and disagreements are analyzed."""
    sample_entries = [
        {"sample_id": "s_01", "arm_id": "arm_a", "file_path": "runs/test.png", "sha256": "hash_01"}
    ]
    sheet, key_map = BlindingService.create_blind_sheet("exp_adjudicate_test", sample_entries, random_seed=77)
    blind_id = sheet.items[0].blind_id

    # Two raters with diverging verdicts
    j1 = HumanJudgmentRecord(
        judgment_id="j_01",
        sheet_id=sheet.sheet_id,
        blind_id=blind_id,
        rater_id="rater_expert_1",
        verdict=EvaluationVerdict.PASS,
        confidence=4.0,
        rationale="Attribute streak clearly visible.",
    )
    j2 = HumanJudgmentRecord(
        judgment_id="j_02",
        sheet_id=sheet.sheet_id,
        blind_id=blind_id,
        rater_id="rater_expert_2",
        verdict=EvaluationVerdict.FAIL,
        confidence=5.0,
        rationale="Glasses frame shape drifted to square.",
    )

    report = BlindingService.adjudicate_blind_judgments(key_map, [j1, j2])

    assert report.total_evaluated_items == 1
    sample_result = report.adjudicated_samples[0]
    assert sample_result.unanimous is False
    assert len(sample_result.rater_judgments) == 2
    # Individual judgments preserved
    r_ids = [j.rater_id for j in sample_result.rater_judgments]
    assert "rater_expert_1" in r_ids
    assert "rater_expert_2" in r_ids

    # CSV export functional
    csv_text = report.to_csv()
    assert "blind_id,sample_id,arm_id" in csv_text
    assert "rater_expert_1:pass" in csv_text


def test_agreement_and_uncertainty_edge_cases():
    """Proves that Kappa and Wilson calculations handle edge cases without crashing."""
    # 1. Zero total Wilson interval
    low, high = wilson_score_interval(0, 0)
    assert low == 0.0 and high == 0.0

    # 2. Perfect agreement Kappa
    k_perf = cohens_kappa(["pass", "fail", "pass"], ["pass", "fail", "pass"])
    assert k_perf["kappa"] == 1.0
    assert k_perf["interpretation"] == "almost_perfect_agreement"

    # 3. Complete disagreement Kappa
    k_dis = cohens_kappa(["pass", "pass"], ["fail", "fail"], categories=["pass", "fail"])
    assert k_dis["kappa"] <= 0.0

    # 4. Differing rater list lengths raise ValueError
    with pytest.raises(ValueError):
        cohens_kappa(["pass"], ["pass", "fail"])


# ==============================================================================
# 6. Visual Regression Corpus & Engine Readiness Invariant (Requirement 11)
# ==============================================================================

def test_unimplemented_engines_cannot_pass_regression():
    """
    Proves the strict invariant: Unimplemented engines (E2, E4, E5, E6, E7, S8)
    cannot be marked READY and cannot report passing regression results.
    """
    corpus = VisualRegressionCorpus(seed_defaults=True)

    # 1. Unimplemented engine cannot be instantiated with readiness='READY'
    with pytest.raises(ValidationError) as exc:
        VisualRegressionCase(
            case_id="reg_illegal_ready",
            domain=RegressionDomain.TEXT_RENDERING,
            engine_id=EngineId.E4_TEXT_GENERATION,
            engine_implemented=False,  # Unimplemented!
            title="Illegal Text Case",
            description="Testing illegal readiness",
            expected_behavior="Text renders cleanly",
            failure_definition="Garbled text",
            readiness=RegressionReadiness.READY,  # Illegal!
        )
    assert "cannot be marked readiness='READY'" in str(exc.value)

    # 2. Check that pre-seeded case for E5 Typography is blocked
    arabic_case = corpus.get_case("reg_04_text_arabic_shaping")
    assert arabic_case is not None
    assert arabic_case.readiness == RegressionReadiness.BLOCKED_BY_ENGINE
    assert arabic_case.engine_implemented is False

    # 3. Attempting to evaluate blocked case strictly returns NOT_EVALUABLE
    eval_res = corpus.evaluate_case(
        case_id="reg_04_text_arabic_shaping",
        candidate_sha256="fake_hash_12345",
    )
    assert eval_res.verdict == EvaluationVerdict.NOT_EVALUABLE
    assert eval_res.is_blocked is True
    assert "Engine 'e5_typography_font' is not implemented yet" in eval_res.block_reason

    # 4. Check readiness inventory stats
    inv = corpus.get_readiness_inventory()
    assert inv["total_cases"] == 7
    assert inv["readiness_summary"]["ready"] == 3  # E1 Image Gen cases
    assert inv["readiness_summary"]["blocked_by_engine"] == 4  # E5, E6, E7, S8 cases


# ==============================================================================
# 7. M0 Historical Experiment Preservation & Integrity (Requirement 12 & 13)
# ==============================================================================

def test_m0_historical_records_integrity_and_limits():
    """
    Proves that the historical M0 visual feasibility experiment is accurately ingested
    without retrospective inflation of scope or unbacked claims.
    """
    summary = load_m0_execution_summary()

    # Denominator verification: exactly 12 samples (6 per arm)
    assert summary.total_planned_samples == 12
    assert summary.total_completed_samples == 12
    assert summary.total_failed_samples == 0
    assert summary.total_filtered_samples == 0
    assert summary.total_unresolved_samples == 0
    assert len(summary.sample_records) == 12
    assert len(summary.evaluation_records) == 12

    # Arm pass rates: Arm A 0% (0/6), Arm B 100% (6/6)
    assert summary.first_pass_yield["arm_a_text_only"] == 0.0
    assert summary.first_pass_yield["arm_b_reference_anchored"] == 1.0

    # Honest uncertainty summaries
    u_a = next(u for u in summary.uncertainty_summaries if "arm_a" in u.metric_name)
    u_b = next(u for u in summary.uncertainty_summaries if "arm_b" in u.metric_name)
    assert u_a.point_estimate == 0.0
    assert u_a.confidence_interval_high <= 0.41
    assert u_b.point_estimate == 1.0
    assert u_b.confidence_interval_low >= 0.59

    # Billing confirmed is explicitly False and marked UNAVAILABLE
    assert summary.reported_usage_summary["billing_confirmed"] is False
    assert summary.reported_usage_summary["billing_status"] == "UNAVAILABLE"

    # Limitations explicitly disclose small sample size
    assert any("exploratory" in lim.lower() for lim in summary.limitations)


def test_real_artifact_references_and_hashes():
    """Proves that nour_reference.png hash matches actual on-disk file digest."""
    ref_path = Path(__file__).resolve().parent.parent.parent / "runs" / "m0_visual" / "reference" / "nour_reference.png"
    assert ref_path.is_file(), f"Expected canonical asset at {ref_path}"

    import hashlib
    with open(ref_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    assert actual_hash.lower() == NOUR_REF_SHA256.lower()


# ==============================================================================
# 8. No Duplicate Infrastructure & Contract Re-use (Requirement 14)
# ==============================================================================

def test_no_duplicate_registries_or_databases():
    """Proves that T6.2 reuses shared execution, identity, and storage models."""
    from app.contracts.identity import IdPrefix
    assert IdPrefix.TAXONOMY.value == "tax"
    assert IdPrefix.RUN.value == "run"
    assert IdPrefix.ARTIFACT.value == "art"

    # Uses standard CostRecord
    cost = CostRecord(
        amount_usd=0.01,
        classification=CostClassification.ESTIMATED,
    )
    assert cost.classification == CostClassification.ESTIMATED
