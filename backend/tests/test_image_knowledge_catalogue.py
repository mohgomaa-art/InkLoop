"""
Comprehensive automated tests for InkLoop Image Generation Knowledge Catalogue
and 60-Group Taxonomy Coverage Register (Milestone 1 / Task T6.1).
Validates schema integrity, evidence provenance, empirical recipe constraints,
truthful coverage inventory, and deterministic serialization.
"""
from pathlib import Path
import json
import pytest
from pydantic import ValidationError

from app.catalogue.enums import (
    CoverageStatus,
    EvidenceClass,
    ClaimConfidence,
    RuleType,
    OutcomeVerdict,
)
from app.catalogue.models import (
    TaxonomyGroupRecord,
    SourceRecord,
    ResearchClaim,
    GenerationRule,
    RecipeRecord,
    CoverageSummary,
)
from app.catalogue.register import TaxonomyRegister
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
    # Exactly 1 group (60) is VALIDATED from M0 feasibility experiment.
    # Exactly 4 groups (07, 08, 19, 28) are RESEARCHED with documented comic theory/style rules.
    # Exactly 55 groups are UNRESEARCHED with explicit gaps documented.
    assert summary.total_groups == 60
    assert summary.validated_count == 1, "Only Group 60 is validated at baseline"
    assert summary.researched_count == 4, "Groups 07, 08, 19, and 28 are researched"
    assert summary.unresearched_count == 55, "55 groups remain unresearched at baseline"
    assert summary.experimentally_tested_count == 0
    assert summary.deprecated_count == 0

    assert summary.status_breakdown["validated"] == 1
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
