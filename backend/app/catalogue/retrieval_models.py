"""
InkLoop Image Knowledge Catalogue - Retrieval Domain Models & Contracts.
Defines typed requests, budget constraints, candidate evaluations,
relevance rankings, and auditable retrieval results.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.catalogue.enums import (
    CoverageStatus,
    ClaimConfidence,
    ConflictPriority,
)
from app.catalogue.models import (
    GenerationRule,
    RecipeRecord,
    ResearchClaim,
    SourceRecord,
    utc_now_iso,
)


class KnowledgeBudget(BaseModel):
    """
    Explicit boundary on knowledge injected into generation prompts.
    Guarantees no indiscriminate prompt-stuffing across the 60 taxonomy groups.
    """
    max_rules: int = Field(default=3, ge=1, le=10, description="Maximum positive/negative generation rules to select")
    max_recipes: int = Field(default=1, ge=0, le=3, description="Maximum full prompt recipes to select")
    max_claims: int = Field(default=2, ge=0, le=5, description="Maximum research claims to attach for provenance")
    max_prompt_tokens_approx: int = Field(default=150, ge=20, le=500, description="Approximate token ceiling for injected knowledge clauses")

    model_config = ConfigDict(extra="forbid")


class KnowledgeRetrievalPolicy(BaseModel):
    """
    Governance policy controlling status thresholds and hypothesis inclusion.
    """
    allow_hypotheses: bool = Field(default=False, description="Whether claims/rules classified as HYPOTHESIS are eligible")
    min_coverage_status: CoverageStatus = Field(
        default=CoverageStatus.RESEARCHED,
        description="Minimum group coverage status for candidates (UNRESEARCHED groups excluded by default)"
    )
    require_provenance: bool = Field(default=True, description="Require linked SourceRecord or experiment ID for selected items")
    enforce_strict_compatibility: bool = Field(default=True, description="Reject candidates with any declared conflicting concepts")
    allow_empty_selection: bool = Field(default=True, description="If True, return clean empty result when no signals match instead of error")

    model_config = ConfigDict(extra="forbid")


class KnowledgeRetrievalRequest(BaseModel):
    """
    Typed query contract capturing all scene and style signals available to E1's context builder.
    Does not depend on external or hidden state.
    """
    scene_id: str = Field(..., description="Unique scene identifier (e.g. 'scene_01')")
    shot_type: str = Field(..., description="Camera framing and shot scale (e.g. 'medium close-up', 'wide shot')")
    action: str = Field(..., description="Subject action description")
    camera_angle: Optional[str] = Field(default=None, description="Camera perspective or view angle")
    lighting: Optional[str] = Field(default=None, description="Scene lighting description")
    panel_instructions: Optional[str] = Field(default=None, description="Panel-specific composition directives")
    character_ids: List[str] = Field(default_factory=list, description="IDs of characters present in the scene")
    has_reference_images: bool = Field(default=False, description="Whether canonical character reference images are supplied")
    visual_invariants: List[str] = Field(default_factory=list, description="Hard canon visual invariants for characters")
    style_medium: str = Field(default="", description="Art medium (e.g. 'comic ink')")
    style_line_and_tone: str = Field(default="", description="Style linework and tonal rules")
    style_palette: Optional[str] = Field(default=None, description="Palette constraint (e.g. 'monochrome')")
    style_positive_constraints: List[str] = Field(default_factory=list, description="Style-wide positive directives")
    style_negative_constraints: List[str] = Field(default_factory=list, description="Style-wide negative constraints")
    target_model: str = Field(default="muse-image-1.0", description="Target image generation model")
    required_group_ids: List[str] = Field(default_factory=list, description="Explicit group IDs that must be considered if eligible")
    prohibited_group_ids: List[str] = Field(default_factory=list, description="Explicit group IDs excluded from selection")
    budget: KnowledgeBudget = Field(default_factory=KnowledgeBudget)
    policy: KnowledgeRetrievalPolicy = Field(default_factory=KnowledgeRetrievalPolicy)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_request_sanity(self) -> "KnowledgeRetrievalRequest":
        if not self.scene_id.strip():
            raise ValueError("scene_id cannot be empty or whitespace")
        if not self.shot_type.strip():
            raise ValueError("shot_type cannot be empty or whitespace")
        return self


class CandidateEvaluation(BaseModel):
    """
    Transparent evaluation record explaining why an item was selected or excluded.
    """
    record_id: str = Field(..., description="ID of rule, recipe, or claim evaluated")
    record_type: str = Field(..., description="'rule', 'recipe', or 'claim'")
    group_id: str = Field(..., description="Parent taxonomy group ID")
    group_number: int = Field(..., description="Parent taxonomy group number (1..60)")
    status: CoverageStatus = Field(..., description="Group coverage status")
    relevance_score: float = Field(default=0.0, description="Calculated relevance score")
    relevance_signals: List[str] = Field(default_factory=list, description="Scene/style signals that matched this item")
    is_compatible: bool = Field(default=True, description="Whether item is free from conflicting concepts")
    conflict_notes: List[str] = Field(default_factory=list, description="Specific conflicts detected if incompatible")
    is_selected: bool = Field(default=False, description="Whether item was selected within budget")
    exclusion_reason: Optional[str] = Field(default=None, description="Detailed reason if candidate was not selected")

    model_config = ConfigDict(extra="forbid")


class KnowledgeRetrievalResult(BaseModel):
    """
    Auditable result of deterministic knowledge catalogue retrieval.
    Records selected records, provenance pointers, budget consumption,
    and a stable selection hash for downstream context fingerprinting.
    """
    scene_id: str = Field(...)
    catalogue_version: str = Field(..., description="Version of the taxonomy register used")
    selection_hash: str = Field(..., description="Deterministic SHA-256 hash of query and selected records")
    selected_group_ids: List[str] = Field(default_factory=list, description="Distinct taxonomy groups contributing knowledge")
    selected_rules: List[GenerationRule] = Field(default_factory=list, description="Selected generation rules")
    selected_recipes: List[RecipeRecord] = Field(default_factory=list, description="Selected prompt recipes")
    selected_claims: List[ResearchClaim] = Field(default_factory=list, description="Selected research claims")
    provenance_sources: List[SourceRecord] = Field(default_factory=list, description="Source records supporting selected items")
    all_evaluations: List[CandidateEvaluation] = Field(default_factory=list, description="Complete evaluation audit log")
    selected_evaluations: List[CandidateEvaluation] = Field(default_factory=list, description="Evaluations of selected items")
    excluded_candidates: List[CandidateEvaluation] = Field(default_factory=list, description="Evaluations of rejected items")
    positive_prompt_clauses: List[str] = Field(default_factory=list, description="Formatted positive clauses for prompt injection")
    negative_prompt_clauses: List[str] = Field(default_factory=list, description="Formatted negative clauses to merge with prohibitions")
    selection_rationale: Dict[str, str] = Field(default_factory=dict, description="Explainable selection rationale per item")
    budget_consumed: Dict[str, Any] = Field(default_factory=dict, description="Summary of budget utilization")
    retrieved_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    @property
    def selected_record_ids(self) -> List[str]:
        """Returns sorted list of all selected item IDs (rules, recipes, claims)."""
        ids = [r.rule_id for r in self.selected_rules]
        ids.extend([r.recipe_id for r in self.selected_recipes])
        ids.extend([c.claim_id for c in self.selected_claims])
        return sorted(ids)

    @property
    def provenance_source_ids(self) -> List[str]:
        """Returns sorted list of supporting source IDs."""
        return sorted([s.source_id for s in self.provenance_sources])
