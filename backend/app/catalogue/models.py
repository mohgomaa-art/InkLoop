"""
InkLoop Image Generation Knowledge Catalogue - Machine-Readable Data Model.
Supports evidence provenance, generation guidance, compatibility constraints,
versioned recipes, and empirical experiment outcomes.
"""
from datetime import datetime, timezone
import json
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict

from app.catalogue.enums import (
    CoverageStatus,
    EvidenceClass,
    ClaimConfidence,
    RuleType,
    OutcomeVerdict,
    ConflictPriority,
    LicenseType,
    LicenseTargetType,
    ReviewDecision,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceRecord(BaseModel):
    """
    Bibliographic and technical source provenance for an image-generation claim or rule.
    Captures exact source location, what it establishes, and what it does not establish.
    """
    source_id: str = Field(..., description="Stable source identifier (e.g. 'src_meta_muse_2026')")
    title: str = Field(..., description="Title of documentation, publication, or experiment log")
    authors: List[str] = Field(default_factory=list, description="Authors or organizational publisher")
    publisher: Optional[str] = Field(default=None, description="Publishing entity or venue")
    url_or_doi: Optional[str] = Field(default=None, description="URL, DOI, arXiv ID, or repository path")
    publication_date: Optional[str] = Field(default=None, description="Publication date (YYYY-MM-DD or year)")
    accessed_date: str = Field(default_factory=utc_now_iso, description="Date accessed or verified in UTC")
    evidence_class: EvidenceClass = Field(..., description="Rigorous classification of evidence strength")
    supported_claim_ids: List[str] = Field(default_factory=list, description="IDs of claims or rules supported by this source")
    license_or_access: Optional[str] = Field(default=None, description="License terms or access restrictions")
    source_location: Optional[str] = Field(default=None, description="Exact document section, chapter, page, URL, or experiment artifact path")
    what_it_establishes: Optional[str] = Field(default=None, description="Explicit statement of what this source proves or documents")
    what_it_does_not_establish: Optional[str] = Field(default=None, description="Explicit boundaries and limits of what this source does NOT prove")
    notes: Optional[str] = Field(default=None, description="Technical annotations on source validity")

    model_config = ConfigDict(extra="forbid")


class ResearchClaim(BaseModel):
    """
    Discrete technical claim about visual behavior, model capability, or prompt effect.
    """
    claim_id: str = Field(..., description="Stable claim identifier (e.g. 'clm_60_anchor_drift')")
    taxonomy_group_id: str = Field(..., description="Parent taxonomy group ID")
    claim_text: str = Field(..., description="Exact formulation of the technical claim")
    confidence: ClaimConfidence = Field(..., description="Confidence classification (FACT, INFERENCE, HYPOTHESIS, EXPERIMENTAL_RESULT, UNKNOWN)")
    source_ids: List[str] = Field(default_factory=list, description="IDs of supporting SourceRecords")
    model_applicability: List[str] = Field(default_factory=list, description="Specific models where claim holds (e.g. ['muse-image-1.0'])")
    verification_status: str = Field(default="unverified", description="'unverified', 'hypothesized', 'tested', or 'empirically_verified'")
    artistic_theory_vs_empirical: str = Field(default="empirical_observation", description="'artistic_theory' or 'empirical_observation'")
    reviewed_by: Optional[str] = Field(default=None, description="Identifier of reviewer or lead investigator")
    reviewed_at: Optional[str] = Field(default=None, description="Review timestamp in UTC")
    empirical_notes: Optional[str] = Field(default=None, description="Contextual limits or caveats")

    model_config = ConfigDict(extra="forbid")


class LicenseRecord(BaseModel):
    """
    Formal governance and rights tracking for assets, fonts, code, models, and reference images (T6.1).
    Ensures commercial safety, attribution obligations, and prevents silent usage of unknown rights.
    """
    license_id: str = Field(..., description="Stable license identifier (e.g. 'lic_font_amiri_ofl')")
    target_type: LicenseTargetType = Field(..., description="Target category being governed")
    target_identifier: str = Field(..., description="Name, asset ID, or module path of the governed artifact")
    license_type: LicenseType = Field(..., description="Standardized license classification")
    license_name: str = Field(..., description="Full human-readable license title (e.g. 'SIL Open Font License 1.1')")
    license_url_or_path: Optional[str] = Field(default=None, description="Canonical URL or repository path to full license text")
    is_commercial_use_permitted: bool = Field(default=False, description="Whether commercial use is affirmatively permitted")
    attribution_required: bool = Field(default=True, description="Whether copyright/author attribution is legally required")
    attribution_text: Optional[str] = Field(default=None, description="Exact attribution string to include if required")
    copyleft_or_sharealike: bool = Field(default=False, description="Whether derivative works must carry same license")
    restrictions_or_notes: Optional[str] = Field(default=None, description="Specific constraints or usage limits")
    verified_by: Optional[str] = Field(default=None, description="Sign-off identity or compliance role")
    verified_at: Optional[str] = Field(default=None, description="Verification timestamp in UTC")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_license_safety(self) -> "LicenseRecord":
        if self.license_type == LicenseType.UNKNOWN and self.is_commercial_use_permitted:
            raise ValueError(
                f"License '{self.license_id}' cannot permit commercial use when license_type is 'UNKNOWN'."
            )
        return self


class PromotionReviewRecord(BaseModel):
    """
    Formal audit record of review and promotion of a research claim, recipe, or taxonomy group (T6.1).
    Audits reviewer identity, decision, rationale, and evidence validation before status upgrades.
    """
    review_id: str = Field(..., description="Unique review identifier (e.g. 'rev_clm_60_anchor')")
    target_id: str = Field(..., description="ID of claim, recipe, or taxonomy group reviewed")
    target_type: str = Field(..., description="'claim', 'recipe', or 'group'")
    reviewer_role: str = Field(..., description="Role of reviewer (e.g. 'Lead Research Agent', 'Project Lead')")
    reviewer_id: str = Field(..., description="Unique reviewer ID or handle")
    decision: ReviewDecision = Field(..., description="Review outcome: approved_promotion, rejected, more_evidence_needed")
    previous_status: str = Field(..., description="Status prior to review")
    promoted_to_status: Optional[str] = Field(default=None, description="New status if approved")
    rationale: str = Field(..., description="Detailed technical justification for decision")
    evidence_verified: List[str] = Field(default_factory=list, description="IDs of sources, experiments, or artifacts checked")
    reviewed_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")


class GenerationRule(BaseModel):
    """
    Actionable prompt directive, negative constraint, or compatibility rule for generation.
    """
    rule_id: str = Field(..., description="Stable rule identifier (e.g. 'rul_19_screentone_lines')")
    taxonomy_group_id: str = Field(..., description="Parent taxonomy group ID")
    rule_type: RuleType = Field(..., description="Rule classification (POSITIVE_GUIDANCE, NEGATIVE_CONSTRAINT, etc.)")
    directive_text: str = Field(..., description="The concrete prompt directive or negative token instruction")
    confidence: ClaimConfidence = Field(default=ClaimConfidence.HYPOTHESIS)
    applies_to_models: List[str] = Field(default_factory=lambda: ["muse-image-1.0"])
    compatible_concepts: List[str] = Field(default_factory=list, description="Visual concepts known to harmonize with this rule")
    conflicting_concepts: List[str] = Field(default_factory=list, description="Visual concepts known to clash or degrade quality")
    interacting_variables: List[str] = Field(default_factory=list, description="Parameters that alter rule behavior (e.g. aspect_ratio, shot_scale)")
    failure_modes: List[str] = Field(default_factory=list, description="Observed artifacts or visual bugs when misapplied")
    priority: ConflictPriority = Field(default=ConflictPriority.MEDIUM, description="Resolution priority when two rules clash")
    exception_rules: List[str] = Field(default_factory=list, description="Situations where this rule should be skipped")
    source_ids: List[str] = Field(default_factory=list)
    is_empirically_tested: bool = Field(default=False)

    model_config = ConfigDict(extra="forbid")


class RecipeRecord(BaseModel):
    """
    Versioned, controlled image-generation recipe linked to empirical evidence.
    """
    recipe_id: str = Field(..., description="Stable recipe identifier (e.g. 'rec_60_ref_anchor_portrait')")
    taxonomy_group_id: str = Field(..., description="Parent taxonomy group ID")
    intended_outcome: str = Field(..., description="Desired visual effect or composition target")
    use_case: str = Field(..., description="Comic production context where this recipe applies")
    applies_to_character_ids: List[str] = Field(default_factory=list, description="Optional canonical characters this character-specific recipe may describe")
    required_prompt_components: List[str] = Field(..., description="Mandatory positive prompt tokens/clauses")
    prohibited_conditions: List[str] = Field(default_factory=list, description="Negative prompts or clashing attributes")
    target_model: str = Field(default="muse-image-1.0", description="Image generation model targeted")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Recommended endpoint parameters")
    reference_image_required: bool = Field(default=False)
    reference_requirements: Optional[str] = Field(default=None, description="Specs for required canonical reference asset")
    experiment_id: Optional[str] = Field(default=None, description="Linked InkLoop experiment run ID if tested")
    experiment_version: Optional[str] = Field(default=None)
    input_artifact_ids: List[str] = Field(default_factory=list)
    output_artifact_ids: List[str] = Field(default_factory=list)
    expected_outcome: Optional[str] = Field(default=None)
    observed_outcome: Optional[str] = Field(default=None)
    evaluation_method: Optional[str] = Field(default=None, description="Evaluation protocol used (e.g. 'muse-spark-1.3 tri-state checklist')")
    result: OutcomeVerdict = Field(default=OutcomeVerdict.UNTESTED)
    failure_observations: List[str] = Field(default_factory=list)
    retries_needed: int = Field(default=0)
    limitations: List[str] = Field(default_factory=list)
    is_empirically_validated: bool = Field(default=False)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_recipe_integrity(self) -> "RecipeRecord":
        """Enforces that a recipe cannot be claimed as empirically validated without a recorded experiment."""
        if self.is_empirically_validated:
            if not self.experiment_id:
                raise ValueError(
                    f"Recipe '{self.recipe_id}' cannot be marked 'is_empirically_validated=True' without a linked 'experiment_id'."
                )
            if self.result == OutcomeVerdict.UNTESTED:
                raise ValueError(
                    f"Recipe '{self.recipe_id}' is marked validated but has result 'UNTESTED'."
                )
        return self


class TaxonomyGroupRecord(BaseModel):
    """
    Authoritative record for one of the 60 taxonomy groups.
    Tracks canonical elements, image-generation relevance, coverage status, and research gaps.
    """
    group_id: str = Field(..., description="Stable taxonomy identifier (e.g. 'tax_01_comic_formats')")
    group_number: int = Field(..., description="Sequential group number from 1 to 60", ge=1, le=60)
    canonical_name: str = Field(..., description="Standardized title from INKLOOP_TASKS.md Section 7")
    image_generation_relevance: str = Field(..., description="Specific explanation of why this group matters to image generation")
    canonical_elements: List[str] = Field(..., description="Full element list from Section 7 without omission")
    status: CoverageStatus = Field(default=CoverageStatus.UNRESEARCHED, description="Authoritative coverage lifecycle state")
    has_primary_sources: bool = Field(default=False)
    has_generation_rules: bool = Field(default=False)
    has_failure_modes: bool = Field(default=False)
    has_recipes: bool = Field(default=False)
    has_recorded_experiments: bool = Field(default=False)
    is_empirically_validated: bool = Field(default=False)
    research_gaps: List[str] = Field(default_factory=list, description="Explicit open gaps or unverified assumptions")
    claims: List[ResearchClaim] = Field(default_factory=list)
    rules: List[GenerationRule] = Field(default_factory=list)
    recipes: List[RecipeRecord] = Field(default_factory=list)
    sources: List[SourceRecord] = Field(default_factory=list)
    version: str = Field(default="1.0.0")
    updated_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_group_coverage_integrity(self) -> "TaxonomyGroupRecord":
        """
        Guarantees that an unresearched group cannot be silently marked validated,
        and that a validated group has real experimental and primary backing.
        """
        if self.status == CoverageStatus.VALIDATED:
            if not self.is_empirically_validated:
                raise ValueError(
                    f"Group '{self.group_id}' has status 'VALIDATED' but 'is_empirically_validated' is False."
                )
            # Must have at least one validated recipe with passing outcome
            passing_recipes = [
                r for r in self.recipes
                if r.is_empirically_validated and r.result == OutcomeVerdict.PASS and r.experiment_id is not None
            ]
            if not passing_recipes:
                raise ValueError(
                    f"Group '{self.group_id}' is marked 'VALIDATED' but contains no passing, empirically validated recipes."
                )
            # Broad group anti-gaming rule: a single recipe cannot validate an entire broad group
            if len(self.canonical_elements) > 3 and len(passing_recipes) < 2:
                raise ValueError(
                    f"Group '{self.group_id}' has {len(self.canonical_elements)} canonical elements but only "
                    f"{len(passing_recipes)} passing recipe(s). Broad groups (>3 elements) require comprehensive "
                    f"element validation (at least 2 passing recipes across diverse elements) to attain full 'VALIDATED' status."
                )
            # Must have primary source or experiment record
            valid_sources = [
                s for s in self.sources
                if s.evidence_class in (EvidenceClass.PRIMARY_PROVIDER_DOC, EvidenceClass.INKLOOP_EXPERIMENT, EvidenceClass.PEER_REVIEWED_RESEARCH)
            ]
            if not valid_sources:
                raise ValueError(
                    f"Group '{self.group_id}' is marked 'VALIDATED' but has no primary or experimental source backing."
                )

        elif self.status == CoverageStatus.EXPERIMENTALLY_TESTED:
            if not self.has_recorded_experiments:
                raise ValueError(
                    f"Group '{self.group_id}' has status 'EXPERIMENTALLY_TESTED' but 'has_recorded_experiments' is False."
                )

        elif self.status == CoverageStatus.UNRESEARCHED:
            if self.is_empirically_validated:
                raise ValueError(
                    f"Group '{self.group_id}' is marked 'UNRESEARCHED' but claims 'is_empirically_validated=True'."
                )
            if self.has_recorded_experiments:
                raise ValueError(
                    f"Group '{self.group_id}' is marked 'UNRESEARCHED' but claims 'has_recorded_experiments=True'."
                )

        return self

    @property
    def name(self) -> str:
        return self.canonical_name

    @property
    def description(self) -> str:
        return self.image_generation_relevance

    @property
    def coverage_status(self) -> CoverageStatus:
        return self.status

    @property
    def research_claims(self) -> List[ResearchClaim]:
        return self.claims

    @property
    def prompt_recipes(self) -> List[RecipeRecord]:
        return self.recipes


class CoverageSummary(BaseModel):
    """
    Deterministic statistical inventory of the 60-group coverage register.
    """
    total_groups: int = 60
    unresearched_count: int
    researched_count: int
    experimentally_tested_count: int
    validated_count: int
    deprecated_count: int
    total_canonical_elements: int
    total_elements: int = 840
    total_sources: int
    total_claims: int
    total_rules: int
    total_recipes: int
    total_experiments: int
    status_breakdown: Dict[str, int]
    gaps_by_group: Dict[str, List[str]]
    generated_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
