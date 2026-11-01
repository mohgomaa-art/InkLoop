"""
InkLoop Style & Character Copier Domain Models and Contracts.
Provides typed, validated data models for:
- Semantic Reference Roles and GenerationReferenceSet
- StyleProfile with structured evidence-backed analysis
- CharacterIdentityProfile with invariants, variations, and Canon linkage
- StyleIdentityQA findings and honest quality evaluation
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict


class SemanticReferenceRole(str, Enum):
    """Semantic role that an input reference image plays in generation/editing."""
    STYLE_REFERENCE = "style_reference"          # Linework, shading, screentones, palette ONLY
    CHARACTER_REFERENCE = "character_reference"  # Any creator-selected stable identity features for a being
    COMPOSITION_REFERENCE = "composition_reference"  # Frame geometry, layout, blocking ONLY
    TARGET_TO_EDIT = "target_to_edit"            # Base image undergoing selective targeted refinement
    POSE_REFERENCE = "pose_reference"            # Body gesture or action reference ONLY
    BACKGROUND_REFERENCE = "background_reference"# Scenery or architectural reference ONLY


class CharacterViewRole(str, Enum):
    """View angle or content specialization for character reference images."""
    FRONT = "front"
    SIDE = "side"
    THREE_QUARTER = "three_quarter"
    FULL_BODY = "full_body"
    FULL_FORM = "full_form"
    CLOSE_UP = "close_up"
    EXPRESSION = "expression"
    OUTFIT = "outfit"
    ACTION_POSE = "action_pose"
    OTHER = "other"


class ProfileStatus(str, Enum):
    """Lifecycle status of a Style or Character Profile."""
    DRAFT = "draft"
    ANALYZING = "analyzing"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class IdentityFeature(BaseModel):
    """A typed identity or state cue for any visual being, with provenance."""
    feature_id: str
    label: str
    description: str
    stability: Literal["stable", "state", "unknown"] = "stable"
    provenance: Literal["user_authored", "model_observation", "model_inference", "unknown"] = "user_authored"
    evidence_asset_ids: List[str] = Field(default_factory=list)


class ReferenceBinding(BaseModel):
    """Binding of a managed asset to a profile with role, weight, and provenance."""
    asset_id: str = Field(..., description="Unique AssetRegistry ID")
    role: SemanticReferenceRole = Field(
        default=SemanticReferenceRole.STYLE_REFERENCE,
        description="Semantic role of this reference image"
    )
    view_role: Optional[CharacterViewRole] = Field(
        default=None,
        description="Camera view or purpose for character references"
    )
    character_id: Optional[str] = Field(
        default=None,
        description="Associated character ID if character reference"
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Heuristic prompt weight (documented as heuristic, not provider numeric weight)"
    )
    notes: Optional[str] = Field(default=None, description="User notes or specific focus instructions")
    source_origin: Optional[str] = Field(default=None, description="Original file name or provenance")
    license_notes: Optional[str] = Field(default=None, description="License or usage permission notes")


class StyleDimensionTrait(BaseModel):
    """A structured trait extracted from style reference images with evidence and confidence."""
    dimension: str = Field(..., description="e.g. linework, shading, palette, screentones, texture")
    summary: str = Field(..., description="Clear human-readable summary of the observed style trait")
    rules: List[str] = Field(default_factory=list, description="Concrete prompt directives derived from this trait")
    source: Literal["model_observation", "model_inference", "computed_measurement", "user_authored", "unknown"] = "unknown"
    review_status: Literal["unreviewed", "user_confirmed", "rejected"] = "unreviewed"
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Calibrated confidence, when the provider supplies one; otherwise unknown"
    )
    is_user_confirmed: bool = Field(
        default=False,
        description="Whether the user explicitly reviewed and confirmed this trait"
    )
    evidence_asset_ids: List[str] = Field(
        default_factory=list,
        description="Reference asset IDs demonstrating this trait"
    )
    uncertainty_notes: Optional[str] = Field(
        default=None,
        description="Explanations of ambiguities or conflicting observations"
    )


class StyleAnalysisRecord(BaseModel):
    """Structured analysis produced from one or more style reference images."""
    medium: str = Field(default="Unclassified", description="Art medium returned by analysis")
    analysis_status: Literal["unknown", "completed", "partial"] = "unknown"
    analysis_source: str = "unknown"
    model_id: Optional[str] = None
    traits: Dict[str, StyleDimensionTrait] = Field(
        default_factory=dict,
        description="Trait observations keyed by dimension name"
    )
    measured_palette: Optional[List[str]] = Field(
        default=None,
        description="Measured dominant colors or value clusters (distinguished from semantic interpretation)"
    )
    screentones_and_fx: List[str] = Field(default_factory=list, description="Screentone densities and special effects")
    negative_constraints: List[str] = Field(default_factory=list, description="Stylistic traits strictly forbidden")
    analysis_summary: str = Field(default="", description="High-level overview of the learned visual style")
    user_directives: Optional[str] = Field(default=None, description="Creator-authored notes, kept separate from model observations")
    analyzed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StyleControlVariable(BaseModel):
    """Creator-editable rendering variable; pinned values are emphasized at generation time."""
    value: str = Field(default="", max_length=1200)
    pinned: bool = False
    source: Literal["model_observation", "user_authored"] = "user_authored"


class StyleProfile(BaseModel):
    """
    Reusable, persistent visual-style profile learned from reference images.
    Applies style rules without transferring subject matter or layout.
    """
    profile_id: str = Field(..., description="Unique profile identifier, e.g. 'style_manga_noir_v1'")
    project_id: str = Field(..., description="Project boundary for isolation")
    name: str = Field(..., description="User-facing style profile name")
    version: int = Field(default=1, description="Monotonic integer version")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ProfileStatus = Field(default=ProfileStatus.DRAFT)
    references: List[ReferenceBinding] = Field(default_factory=list)
    analysis: Optional[StyleAnalysisRecord] = Field(default=None)
    style_prompt_core: str = Field(
        default="",
        description="Concise model-facing style description synthesized from approved traits"
    )
    negative_constraints: List[str] = Field(
        default_factory=list,
        description="Stylistic aspects to avoid (e.g. 'no 3D render', 'no blurry gradients')"
    )
    control_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Relative emphasis weights for linework, shading, screentones, etc."
    )
    style_variables: Dict[str, StyleControlVariable] = Field(
        default_factory=dict,
        description="Editable rendering dimensions; pinned values are included as high-priority generation guidance"
    )
    approved_by_user: bool = Field(default=False)
    approved_at: Optional[str] = Field(default=None)
    version_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def visual_invariants(self) -> List[str]:
        return self.identity_invariants


class CharacterIdentityProfile(BaseModel):
    """
    Reusable, persistent character identity profile backed by multi-view references.
    Guarantees stable invariants while explicitly encouraging dynamic pose/expression variation.
    """
    profile_id: str = Field(..., description="Unique profile identifier, e.g. 'char_nour_v1'")
    project_id: str = Field(..., description="Project boundary for isolation")
    character_id: str = Field(..., description="Stable character ID linked to Story Bible/Canon")
    name: str = Field(..., description="Character display name")
    version: int = Field(default=1, description="Monotonic integer version")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ProfileStatus = Field(default=ProfileStatus.DRAFT)
    references: List[ReferenceBinding] = Field(default_factory=list)
    entity_kind: str = Field(default="unspecified being", description="Open vocabulary: human, animal, monster, object-like, abstract, hybrid, or any creator-defined kind")
    morphology: str = Field(default="", description="Overall form and body plan; may be non-humanoid, object-like, abstract, or unknown")
    surface_description: str = Field(default="", description="Color, material, texture, pattern, and surface cues without assuming skin or hair")
    appendages_or_parts: List[str] = Field(default_factory=list, description="Creator-defined parts, limbs, tentacles, projections, ornaments, or none")
    sensory_features: List[str] = Field(default_factory=list, description="Eyes, marks, symbols, sensors, face-like features, or explicit absence")
    locomotion: str = Field(default="", description="How this being moves, if applicable")
    face_check_applicable: bool = Field(default=False, description="Enable face-specific checks only when this being has relevant face features")
    identity_features: List[IdentityFeature] = Field(default_factory=list, description="Typed stable and mutable visual features with provenance")
    identity_invariants: List[str] = Field(
        default_factory=list,
        description="Creator-approved identity traits that should remain stable, including non-human or abstract forms"
    )
    allowed_variations: List[str] = Field(
        default_factory=list,
        description="Dimensions encouraged to vary (dynamic pose, facial expression, camera angle, lighting)"
    )
    contextual_traits: List[str] = Field(
        default_factory=list,
        description="Scene/arc specific traits (e.g. battle damage, rain-soaked, alternate jacket)"
    )
    uncertain_traits: List[str] = Field(
        default_factory=list,
        description="Observed but under-specified traits not yet confirmed as canonical"
    )
    analysis_status: Literal["unknown", "completed", "partial", "not_run"] = "unknown"
    analysis_source: str = "unknown"
    trait_provenance: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-field provenance: model_observation, model_inference, user_authored, copied, or unknown"
    )
    forbidden_drift: List[str] = Field(
        default_factory=list,
        description="Explicit negative identity drift instructions (e.g. 'never draw round chin or blonde hair')"
    )
    prompt_identity_core: str = Field(
        default="",
        description="Concise model-facing character likeness prompt"
    )
    reference_selection_strategy: str = Field(
        default="diverse_views",
        description="Heuristic for selecting representative references (e.g. 'diverse_views', 'angle_match')"
    )
    evidence_links: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Mapping from trait description to source asset IDs"
    )
    base_outfit: Optional[Dict[str, Any]] = Field(default=None)
    outfit_variants: List[Dict[str, Any]] = Field(default_factory=list)
    approved_by_user: bool = Field(default=False)
    approved_at: Optional[str] = Field(default=None)
    canon_version: Optional[int] = Field(default=None, description="Story Bible Canon version when approved")
    version_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def visual_invariants(self) -> List[str]:
        return self.identity_invariants


class GenerationReferenceItem(BaseModel):
    """An individual reference image with explicit semantic role for a generation/edit job."""
    asset_id: str
    role: SemanticReferenceRole
    view_role: Optional[CharacterViewRole] = None
    character_id: Optional[str] = None
    profile_id: Optional[str] = None
    profile_version: Optional[int] = None
    weight: float = 1.0
    notes: Optional[str] = None
    include_exclude_rules: Optional[str] = None
    description: Optional[str] = None


class GenerationReferenceSet(BaseModel):
    """
    Structured set of reference images passed to generation or editing.
    Differentiates style, character identity, and composition roles cleanly.
    """
    project_id: str
    references: List[GenerationReferenceItem] = Field(default_factory=list)
    style_profile_id: Optional[str] = None
    style_profile_version: Optional[int] = None
    character_profile_ids: List[str] = Field(default_factory=list)
    target_to_edit_asset_id: Optional[str] = None

    def get_style_references(self) -> List[GenerationReferenceItem]:
        return [r for r in self.references if r.role == SemanticReferenceRole.STYLE_REFERENCE]

    def get_character_references(self, character_id: Optional[str] = None) -> List[GenerationReferenceItem]:
        if character_id:
            return [r for r in self.references if r.role == SemanticReferenceRole.CHARACTER_REFERENCE and r.character_id == character_id]
        return [r for r in self.references if r.role == SemanticReferenceRole.CHARACTER_REFERENCE]

    def get_target_to_edit(self) -> Optional[GenerationReferenceItem]:
        for r in self.references:
            if r.role == SemanticReferenceRole.TARGET_TO_EDIT:
                return r
        return None


class QASeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class QACategory(str, Enum):
    STYLE = "STYLE"
    IDENTITY = "IDENTITY"
    VARIATION = "VARIATION"
    LEAKAGE = "LEAKAGE"
    COMPOSITION = "COMPOSITION"


class QAFinding(BaseModel):
    """Individual QA finding describing a stylistic, identity, or variation observation."""
    finding_id: str
    severity: QASeverity
    category: QACategory
    message: str
    affected_dimension: str
    evidence: str
    suggested_repair: Optional[str] = None


class StyleIdentityQAResult(BaseModel):
    """
    Comprehensive, honest QA report evaluating generated artwork against
    Style and Character profiles. Never invents fake precision or false guarantees.
    """
    run_id: str
    asset_id: str
    passed: bool
    status: Literal["pass", "needs_review", "fail", "not_verified"]
    overall_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Calibrated composite score; null when the available checks cannot support one"
    )
    score_explanation: str = Field(
        ...,
        description="Human-readable breakdown explaining how the rubric score was computed"
    )
    style_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    identity_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    variation_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Score measuring whether the pose/composition genuinely varies rather than copy-pasting reference"
    )
    leakage_detected: Optional[bool] = Field(
        default=None,
        description="Null unless subject/composition leakage was actually checked"
    )
    checked_dimensions: List[str] = Field(default_factory=list)
    not_checked_dimensions: List[str] = Field(default_factory=list)
    findings: List[QAFinding] = Field(default_factory=list)
    targeted_repair_prompt: Optional[str] = Field(
        default=None,
        description="Focused corrective prompt if targeted single-pass repair is recommended"
    )
    evaluator_version: str = Field(default="inkloop-style-qa-v1.0")
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
