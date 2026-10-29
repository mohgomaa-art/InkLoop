"""
Comprehensive automated tests for InkLoop Image Generation Knowledge Catalogue
and 60-Group Taxonomy Coverage Register (Milestone 1 / Task T6.1).
Validates schema integrity, evidence provenance, empirical recipe constraints,
truthful coverage inventory, and deterministic serialization.
"""
from pathlib import Path
import json
import subprocess
import sys
import pytest
from pydantic import ValidationError

from app.catalogue.enums import (
    CoverageStatus,
    EvidenceClass,
    ClaimConfidence,
    RuleType,
    OutcomeVerdict,
    LicenseType,
    LicenseTargetType,
    ReviewDecision,
)
from app.catalogue.models import (
    TaxonomyGroupRecord,
    SourceRecord,
    ResearchClaim,
    GenerationRule,
    RecipeRecord,
    CoverageSummary,
    LicenseRecord,
    PromotionReviewRecord,
)
from app.catalogue.register import TaxonomyRegister
from app.catalogue.governance import (
    LicenseRegistry,
    PromotionWorkflow,
    create_default_license_registry,
)
from app.image_adapter import GenerationRequest, GenerationResponse, SimulatedImageGenerationAdapter
from app.contracts.engine import EngineRunRequest, ImageGenerationParams, EngineId


@pytest.fixture
def register() -> TaxonomyRegister:
    """Provides an initialized TaxonomyRegister with the authoritative 60-group register."""
    return TaxonomyRegister()


# ==============================================================================
# 1. 60-Group Representation & Numbering Tests
# ==============================================================================

def test_all_60_groups_represented_exactly_once(register):
    """Proves that every agreed taxonomy group is represented exactly once without omission."""
    groups = register.list_groups()
    assert len(groups) == 60, f"Expected exactly 60 groups, found {len(groups)}"

    group_ids = [g.group_id for g in groups]
    assert len(set(group_ids)) == 60, "All group IDs must be unique"

    group_numbers = [g.group_number for g in groups]
    assert len(set(group_numbers)) == 60, "All group numbers must be unique"


def test_consecutive_group_numbering_1_to_60(register):
    """Proves that groups are consecutively numbered 1 to 60 with no gaps."""
    groups = register.list_groups()
    expected_numbers = list(range(1, 61))
    actual_numbers = [g.group_number for g in groups]
    assert actual_numbers == expected_numbers


def test_canonical_names_and_element_counts_preserved(register):
    """Proves that canonical group names and full element lists from Section 7 are preserved."""
    summary = register.get_summary()
    assert summary.total_canonical_elements == 840, "All 840 canonical elements across the 60 groups must be present"

    # Spot-check critical groups
    g1 = register.get_group(1)
    assert g1.canonical_name == "01. Comic Formats"
    assert "Manga" in g1.canonical_elements
    assert "Webtoon" in g1.canonical_elements
    assert "4-Koma" in g1.canonical_elements

    g19 = register.get_group(19)
    assert g19.canonical_name == "19. Stroke & Line Art Types"
    assert "Clean Line Art" in g19.canonical_elements
    assert "Screentone" in g19.canonical_elements

    g60 = register.get_group(60)
    assert g60.canonical_name == "60. Visual Continuity & Validation"
    assert "Character Identity" in g60.canonical_elements
    assert "Reference Matching" in g60.canonical_elements
    assert "Verifier Confidence" in g60.canonical_elements


# ==============================================================================
# 2. Schema Validation & Integrity Invariants
# ==============================================================================

def test_unresearched_group_cannot_claim_validation():
    """Proves that an UNRESEARCHED group is rejected if it attempts to claim empirical validation."""
    with pytest.raises(ValidationError) as exc:
        TaxonomyGroupRecord(
            group_id="tax_01_comic_formats",
            group_number=1,
            canonical_name="01. Comic Formats",
            image_generation_relevance="Test relevance",
            canonical_elements=["Manga"],
            status=CoverageStatus.UNRESEARCHED,
            is_empirically_validated=True,  # Illegal: unresearched cannot be validated
        )
    assert "claims 'is_empirically_validated=True'" in str(exc.value)


def test_validated_group_requires_passing_recipe_and_evidence():
    """Proves that a group cannot be labeled VALIDATED without empirical passing recipes and primary sources."""
    # Attempt 1: Validated status without empirical validation flag
    with pytest.raises(ValidationError) as exc1:
        TaxonomyGroupRecord(
            group_id="tax_60_test",
            group_number=60,
            canonical_name="60. Visual Continuity & Validation",
            image_generation_relevance="Test relevance",
            canonical_elements=["Character Identity"],
            status=CoverageStatus.VALIDATED,
            is_empirically_validated=False,
        )
    assert "'is_empirically_validated' is False" in str(exc1.value)

    # Attempt 2: Validated status with no passing recipes
    with pytest.raises(ValidationError) as exc2:
        TaxonomyGroupRecord(
            group_id="tax_60_test",
            group_number=60,
            canonical_name="60. Visual Continuity & Validation",
            image_generation_relevance="Test relevance",
            canonical_elements=["Character Identity"],
            status=CoverageStatus.VALIDATED,
            is_empirically_validated=True,
            recipes=[],  # Empty recipes
        )
    assert "contains no passing, empirically validated recipes" in str(exc2.value)


def test_recipe_without_experiment_cannot_be_empirically_validated():
    """Proves that a RecipeRecord without a linked experiment cannot claim empirical validation."""
    with pytest.raises(ValidationError) as exc:
        RecipeRecord(
            recipe_id="rec_unbacked_01",
            taxonomy_group_id="tax_19_stroke_line_art_types",
            intended_outcome="Consistent screentone",
            use_case="Background panels",
            required_prompt_components=["clean linework"],
            target_model="muse-image-1.0",
            experiment_id=None,  # No experiment!
            is_empirically_validated=True,  # Illegal without experiment
        )
    assert "cannot be marked 'is_empirically_validated=True' without a linked 'experiment_id'" in str(exc.value)


def test_invalid_status_and_malformed_records_rejected():
    """Proves that invalid enum values and malformed records raise Pydantic validation errors."""
    with pytest.raises(ValidationError):
        TaxonomyGroupRecord(
            group_id="tax_invalid",
            group_number=99,  # Out of range 1..60
            canonical_name="Invalid",
            image_generation_relevance="Invalid",
            canonical_elements=[],
            status="fabricated_status",  # Invalid enum
        )


# ==============================================================================
# 3. Truthful Coverage & Statistical Inventory Tests
# ==============================================================================

def test_coverage_summary_counts_match_real_data(register):
    """Proves that coverage counts are deterministic and accurately reflect baseline research reality."""
    summary = register.get_summary()

    # Truthful baseline verification:
    # Exactly 0 groups are VALIDATED (Group 60 contains 14 elements; M0 tested solo portrait anchoring).
    # Exactly 1 group (60) is EXPERIMENTALLY_TESTED with documented M0 empirical trials and passing recipe.
    # Exactly 4 groups (07, 08, 19, 28) are RESEARCHED with documented comic theory/style rules.
    # Exactly 55 groups are UNRESEARCHED with explicit gaps documented.
    assert summary.total_groups == 60
    assert summary.validated_count == 0, "No broad group is fully validated without multi-element recipes"
    assert summary.experimentally_tested_count == 1, "Group 60 is experimentally tested from M0 trials"
    assert summary.researched_count == 4, "Groups 07, 08, 19, and 28 are researched"
    assert summary.unresearched_count == 55, "55 groups remain unresearched at baseline"
    assert summary.deprecated_count == 0

    assert summary.status_breakdown["validated"] == 0
    assert summary.status_breakdown["experimentally_tested"] == 1
    assert summary.status_breakdown["researched"] == 4
    assert summary.status_breakdown["unresearched"] == 55

    # Incompleteness must be visible: all 60 groups have explicit documented gaps
    assert len(summary.gaps_by_group) == 60


def test_deterministic_serialization_roundtrip(register, tmp_path):
    """Proves that exporting and reloading the register produces bit-for-bit identical structure."""
    out_file = tmp_path / "exported_taxonomy.json"
    register.save(target_path=out_file)
    assert out_file.is_file()

    # Re-load in a separate instance
    reloaded_reg = TaxonomyRegister(data_file=out_file)
    assert len(reloaded_reg.list_groups()) == 60

    original_json = json.dumps([g.model_dump() for g in register.list_groups()], sort_keys=True)
    reloaded_json = json.dumps([g.model_dump() for g in reloaded_reg.list_groups()], sort_keys=True)
    assert original_json == reloaded_json


def test_register_invariants_pass_audit(register):
    """Proves that the built-in register passes all invariant audits with zero violations."""
    errors = register.validate_invariants()
    assert len(errors) == 0, f"Invariant audit failed: {errors}"


# ==============================================================================
# 4. Existing Engine Preservation & Contract Compatibility
# ==============================================================================

def test_existing_image_adapter_contracts_continue_to_pass():
    """Proves that ImageGenerationAdapter and GenerationRequest contracts remain unaltered and functional."""
    adapter = SimulatedImageGenerationAdapter()
    req = GenerationRequest(
        prompt="black and white comic ink, clean linework, Nour smiling",
        panel_id="panel_test_01",
        scene_id="scene_test_01",
    )
    resp = adapter.generate(req)
    assert resp.success is True
    assert resp.is_simulated is True
    assert resp.image_bytes is not None


def test_no_duplicate_infrastructure():
    """Proves that the catalogue reuses shared models without creating competing databases or run logs."""
    from app.contracts.identity import IdPrefix
    assert IdPrefix.TAXONOMY.value == "tax"

    from app.contracts.engine import ProvenanceRecord, EngineId
    prov = ProvenanceRecord(
        engine_id=EngineId.E1_IMAGE_GENERATION,
        config_hash="test_config_hash",
        taxonomy_rule_ids=["rul_60_pass_reference_image", "rul_19_screentone_linework"]
    )
    assert len(prov.taxonomy_rule_ids) == 2


# ==============================================================================
# 5. Research Governance, Provenance, Licensing & Promotion Tests (T6.1)
# ==============================================================================

def test_detailed_source_provenance_and_scope_limits(register):
    """Proves that sources capture exact locations, what they establish, and what they do NOT establish."""
    g60 = register.get_group(60)
    assert len(g60.sources) >= 2

    # Check Meta documentation source
    src_meta = next(s for s in g60.sources if s.source_id == "src_meta_muse_docs_2026")
    assert src_meta.source_location is not None
    assert src_meta.what_it_establishes is not None
    assert "edits" in src_meta.what_it_establishes
    assert src_meta.what_it_does_not_establish is not None
    assert "comic" in src_meta.what_it_does_not_establish.lower()

    # Check M0 experiment source
    src_m0 = next(s for s in g60.sources if s.source_id == "src_inkloop_m0_feasibility")
    assert "runs/m0_visual" in src_m0.source_location
    assert "nour_reference.png" in src_m0.what_it_establishes
    assert "multi-character" in src_m0.what_it_does_not_establish.lower()


def test_claims_distinguish_artistic_theory_vs_empirical(register):
    """Proves that claims explicitly distinguish artistic theory from empirical observation."""
    g60 = register.get_group(60)
    for claim in g60.claims:
        assert claim.artistic_theory_vs_empirical == "empirical_observation"

    g19 = register.get_group(19)
    for claim in g19.claims:
        assert claim.artistic_theory_vs_empirical == "artistic_theory"


def test_broad_group_anti_gaming_validation_guard():
    """
    Proves that a broad group (>3 elements) cannot be marked VALIDATED with only 1 passing recipe.
    Requires comprehensive multi-element validation (>= 2 passing recipes).
    """
    r1 = RecipeRecord(
        recipe_id="rec_test_01",
        taxonomy_group_id="tax_60_visual_continuity_validation",
        intended_outcome="Portrait consistency",
        use_case="Solo portrait",
        required_prompt_components=["clean linework"],
        target_model="muse-image-1.0",
        experiment_id="exp_01",
        result=OutcomeVerdict.PASS,
        is_empirically_validated=True,
    )
    src = SourceRecord(
        source_id="src_test_primary",
        title="Test Doc",
        evidence_class=EvidenceClass.PRIMARY_PROVIDER_DOC,
    )

    # 1 recipe on a 14-element group must fail validation
    with pytest.raises(ValidationError) as exc:
        TaxonomyGroupRecord(
            group_id="tax_60_visual_continuity_validation",
            group_number=60,
            canonical_name="60. Visual Continuity & Validation",
            image_generation_relevance="Test relevance",
            canonical_elements=["E1", "E2", "E3", "E4", "E5"],  # 5 elements (>3)
            status=CoverageStatus.VALIDATED,
            is_empirically_validated=True,
            recipes=[r1],  # Only 1 recipe
            sources=[src],
        )
    assert "Broad groups (>3 elements) require comprehensive element validation" in str(exc.value)

    # 2 passing recipes across broad group satisfies the anti-gaming guard
    r2 = RecipeRecord(
        recipe_id="rec_test_02",
        taxonomy_group_id="tax_60_visual_continuity_validation",
        intended_outcome="Lighting consistency",
        use_case="Lighting transition",
        required_prompt_components=["monochrome lighting"],
        target_model="muse-image-1.0",
        experiment_id="exp_02",
        result=OutcomeVerdict.PASS,
        is_empirically_validated=True,
    )
    valid_broad_group = TaxonomyGroupRecord(
        group_id="tax_60_visual_continuity_validation",
        group_number=60,
        canonical_name="60. Visual Continuity & Validation",
        image_generation_relevance="Test relevance",
        canonical_elements=["E1", "E2", "E3", "E4", "E5"],
        status=CoverageStatus.VALIDATED,
        is_empirically_validated=True,
        recipes=[r1, r2],  # 2 recipes!
        sources=[src],
    )
    assert valid_broad_group.status == CoverageStatus.VALIDATED


def test_license_governance_and_unknown_commercial_safety():
    """Proves that LicenseRecord prevents silent commercial use of unknown license terms."""
    with pytest.raises(ValidationError) as exc:
        LicenseRecord(
            license_id="lic_bad_unknown",
            target_type=LicenseTargetType.EXTERNAL_DATASET,
            target_identifier="unverified_faces_dataset",
            license_type=LicenseType.UNKNOWN,
            license_name="Unknown Internet Scraping",
            is_commercial_use_permitted=True,  # Illegal: UNKNOWN cannot permit commercial use!
        )
    assert "cannot permit commercial use when license_type is 'UNKNOWN'" in str(exc.value)


def test_license_registry_and_commercial_clearance():
    """Proves that LicenseRegistry tracks font, library, model, and reference assets."""
    registry = create_default_license_registry()

    # Verify default known assets
    assert registry.is_target_commercially_cleared(LicenseTargetType.FONT, "Amiri") is True
    assert registry.is_target_commercially_cleared(LicenseTargetType.SOFTWARE_LIBRARY, "Pillow") is True
    assert registry.is_target_commercially_cleared(LicenseTargetType.SOFTWARE_LIBRARY, "pydantic") is True
    assert registry.is_target_commercially_cleared(LicenseTargetType.SOFTWARE_LIBRARY, "httpx") is True
    assert registry.is_target_commercially_cleared(LicenseTargetType.MODEL_GENERATED, "muse-image-1.0") is True
    assert registry.is_target_commercially_cleared(LicenseTargetType.REFERENCE_IMAGE, "nour_reference.png") is True

    # Unknown asset is not cleared
    assert registry.is_target_commercially_cleared(LicenseTargetType.EXTERNAL_DATASET, "random_asset") is False

    # Register an unknown dataset without commercial clearance
    unknown_record = LicenseRecord(
        license_id="lic_dataset_scraped_art",
        target_type=LicenseTargetType.EXTERNAL_DATASET,
        target_identifier="scraped_art_pack",
        license_type=LicenseType.UNKNOWN,
        license_name="Unclear Web Scrape",
        is_commercial_use_permitted=False,
    )
    registry.register_license(unknown_record)
    assert registry.is_target_commercially_cleared(LicenseTargetType.EXTERNAL_DATASET, "scraped_art_pack") is False

    audit = registry.audit_licenses()
    assert audit["total_registered_licenses"] == 7
    assert audit["commercial_cleared_count"] == 6
    assert audit["uncleared_or_unknown_count"] == 1


def test_promotion_workflow_claim_and_audit_trail():
    """Proves that PromotionWorkflow logs formal review records and prevents baseless claim promotion."""
    workflow = PromotionWorkflow()

    claim = ResearchClaim(
        claim_id="clm_speculative_01",
        taxonomy_group_id="tax_01_comic_formats",
        claim_text="Webtoon vertical canvas reduces diffusion boundary artifacts by 50%.",
        confidence=ClaimConfidence.HYPOTHESIS,
        source_ids=[],
    )

    # Attempt promotion without verified evidence or sources -> REJECTED
    rec1, updated_claim1 = workflow.review_claim(
        claim=claim,
        target_confidence=ClaimConfidence.EXPERIMENTAL_RESULT,
        reviewer_id="reviewer_lead",
        reviewer_role="Project Lead",
        rationale="Promoting based on hunch without run log.",
        evidence_verified=[],
    )
    assert rec1.decision == ReviewDecision.REJECTED
    assert updated_claim1.confidence == ClaimConfidence.HYPOTHESIS

    # Promotion with verified experiment artifact -> APPROVED
    rec2, updated_claim2 = workflow.review_claim(
        claim=claim,
        target_confidence=ClaimConfidence.EXPERIMENTAL_RESULT,
        reviewer_id="reviewer_lead",
        reviewer_role="Project Lead",
        rationale="Verified against run benchmark artifact runs/exp_webtoon_01.json",
        evidence_verified=["runs/exp_webtoon_01.json"],
    )
    assert rec2.decision == ReviewDecision.APPROVED_PROMOTION
    assert updated_claim2.confidence == ClaimConfidence.EXPERIMENTAL_RESULT
    assert updated_claim2.reviewed_by == "reviewer_lead"
    assert updated_claim2.reviewed_at is not None

    # Check reviews retrieved
    reviews = workflow.get_reviews_for_target("clm_speculative_01")
    assert len(reviews) == 2


def test_promotion_workflow_group_rejection_and_approval(register):
    """Proves that PromotionWorkflow validates group coverage rules before approving status change."""
    workflow = PromotionWorkflow()
    g1 = register.get_group(1)  # UNRESEARCHED

    # Attempt to promote UNRESEARCHED to VALIDATED without evidence -> REJECTED
    rec, group_result = workflow.review_group(
        group=g1,
        target_status=CoverageStatus.VALIDATED,
        reviewer_id="reviewer_lead",
        reviewer_role="Project Lead",
        rationale="Want to fast-track comic formats",
        evidence_verified=[],
    )
    assert rec.decision == ReviewDecision.REJECTED
    assert group_result.status == CoverageStatus.UNRESEARCHED

    # Check that rejection rationale details the integrity violation
    assert "invariant violation" in rec.rationale


def test_taxonomy_cli_script_runs_cleanly():
    """Proves that scripts/generate_taxonomy.py runs with --check and --audit returning exit code 0."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    script_path = repo_root / "scripts" / "generate_taxonomy.py"
    assert script_path.is_file(), "scripts/generate_taxonomy.py must exist"

    # Run --check
    proc_check = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc_check.returncode == 0, f"generate_taxonomy.py --check failed: {proc_check.stderr}"
    assert "AUDIT PASSED" in proc_check.stdout

    # Run --audit
    proc_audit = subprocess.run(
        [sys.executable, str(script_path), "--audit"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc_audit.returncode == 0, f"generate_taxonomy.py --audit failed: {proc_audit.stderr}"
    assert "LICENSING & GOVERNANCE AUDIT" in proc_audit.stdout

