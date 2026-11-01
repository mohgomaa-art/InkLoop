"""
InkLoop AI Creative Director & Character Maker Contracts and Schemas.
Provides typed, validated, and versioned models for Creative Briefs,
Story Bibles, Character Identity Profiles, Ensemble Relationships,
World Systems, Narrative Arcs, Visual Styles, Reference Sheet Plans,
Machine-Readable Production Contracts, and Cross-Document Coherence Findings.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict, computed_field

# =============================================================================
# 1. Creative Brief & Fact Classification
# =============================================================================

class CreativeMode(str, Enum):
    QUICK_CONCEPT = "quick_concept"
    FULL_PRODUCTION_BIBLE = "full_production_bible"
    DEVELOP_ONE_CHARACTER = "develop_one_character"
    CHARACTER_DEEP_DIVE = "character_deep_dive"
    BUILD_ENSEMBLE = "build_ensemble"
    ENSEMBLE_BUILDER = "ensemble_builder"
    DEVELOP_STORY_ARC = "develop_story_arc"
    VISUAL_DEVELOPMENT = "visual_development"
    VISUAL_WORLDBUILDING = "visual_worldbuilding"
    CONTINUE_EXISTING_WORK = "continue_existing_work"

class FactCategory(str, Enum):
    EXPLICIT_USER_FACT = "explicit_user_fact"  # Directly provided by user
    AGENT_PROPOSAL = "agent_proposal"          # Creative suggestion needing review
    UNKNOWN = "unknown"                        # Unresolved ambiguity

class FactItem(BaseModel):
    fact_id: str
    category: FactCategory
    field: str
    content: str
    provenance: str = Field(..., description="Source text, attachment ID, or canon record")
    confidence: float = 1.0
    needs_review: bool = False

    @property
    def fact_statement(self) -> str:
        return self.content

class VisualReferenceRole(str, Enum):
    CHARACTER_SILHOUETTE = "character_silhouette"
    FACE_EXPRESSION = "face_expression"
    HAIR_OR_FEATURE = "hair_or_feature"
    COSTUME_OUTFIT = "costume_outfit"
    LINEWORK_STYLE = "linework_style"
    COLOR_PALETTE = "color_palette"
    LIGHTING_MOOD = "lighting_mood"
    ENVIRONMENT_LOCATION = "environment_location"
    PROP_OBJECT = "prop_object"
    GENERAL_MOOD = "general_mood"

class BriefVisualReference(BaseModel):
    asset_id: str
    url: Optional[str] = None
    role: VisualReferenceRole = VisualReferenceRole.GENERAL_MOOD
    notes: Optional[str] = None
    assigned_character_id: Optional[str] = None

class CreativeBrief(BaseModel):
    brief_id: str
    project_id: str
    mode: CreativeMode = CreativeMode.FULL_PRODUCTION_BIBLE
    user_prompt: str
    title: Optional[str] = None
    format: str = "webtoon"  # manga, webtoon, manhwa, graphic_novel, comic
    genre: str = "Dark Fantasy"
    tone: str = "Emotionally grounded, atmospheric, tense"
    target_audience: str = "Young Adult / Mature"
    premise: str = ""
    central_dramatic_question: str = ""
    intended_emotional_experience: str = ""
    themes: List[str] = Field(default_factory=list)
    motifs: List[str] = Field(default_factory=list)
    protagonist_concept: str = ""
    desired_cast_size: Optional[int] = None
    setting_world_premise: str = ""
    visual_references: List[BriefVisualReference] = Field(default_factory=list)
    scope: str = "season_1"  # standalone, short_arc, season_1, ongoing
    constraints_must_have: List[str] = Field(default_factory=list)
    constraints_must_not_have: List[str] = Field(default_factory=list)
    boundaries_and_preferences: List[str] = Field(default_factory=list)
    explicit_facts: List[FactItem] = Field(default_factory=list)
    agent_proposals: List[FactItem] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @computed_field
    @property
    def explicit_user_facts(self) -> List[FactItem]:
        return self.explicit_facts

    @computed_field
    @property
    def open_questions_and_unknowns(self) -> List[str]:
        return self.unknowns

    @computed_field
    @property
    def primary_genre(self) -> str:
        if "dark fantasy" in self.genre.lower():
            return "dark fantasy"
        return self.genre.lower()

    @computed_field
    @property
    def target_medium(self) -> str:
        return self.format

# =============================================================================
# 2. Project & Story Bible
# =============================================================================

class CreativeStoryBible(BaseModel):
    project_id: str
    title: str
    logline: str
    premise: str
    synopsis_short: str
    synopsis_expanded: str
    genre: str
    tone: str
    format: str
    themes: List[str] = Field(default_factory=list)
    subthemes: List[str] = Field(default_factory=list)
    motifs: List[str] = Field(default_factory=list)
    central_dramatic_question: str
    stakes: str
    conflict_engine: str
    narrative_promise: str
    point_of_view: str = "Third-person close"
    narrative_voice: str = "Introspective, observant"
    pacing_and_rhythm: str = "Deliberate pacing with sudden sharp emotional spikes"
    story_boundaries: List[str] = Field(default_factory=list)
    content_constraints: List[str] = Field(default_factory=list)
    core_world_premise: str
    world_rules_summary: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    canon_version: int = 1
    approved_facts: List[str] = Field(default_factory=list)
    proposed_facts: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def theme(self) -> str:
        return self.themes[0] if self.themes else "Memory and Identity"

# =============================================================================
# 3. Character Identity Profile (Character Copier Compatible)
# =============================================================================

class CharacterArcCheckpoint(BaseModel):
    phase: str  # starting_state, inciting_choice, midpoint_crisis, climax_cost, resolution_state
    description: str
    emotional_shift: str

class OutfitVariant(BaseModel):
    outfit_id: str
    name: str
    description: str
    garments: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)
    materials: List[str] = Field(default_factory=list)
    is_base: bool = False


class CharacterVisualFeature(BaseModel):
    feature_id: str
    label: str
    description: str
    stability: Literal["stable", "state", "unknown"] = "stable"
    provenance: Literal["user_authored", "model_observation", "model_inference", "unknown"] = "user_authored"
    evidence_asset_ids: List[str] = Field(default_factory=list)

class CharacterIdentityProfile(BaseModel):
    character_id: str
    name: str
    role: str = "Character or entity"
    narrative_function: str = ""
    age_range: str = Field(default="unspecified / not applicable", description="Only use when age is meaningful for this entity and supported by the creator or source")
    entity_kind: str = Field(default="unspecified being", description="Open vocabulary, not restricted to humans or animals")
    morphology: str = Field(default="", description="Overall shape/body plan, including non-humanoid, object-like, abstract, and hybrid forms")
    surface_description: str = Field(default="", description="Materials, colors, texture, and patterns without assuming skin, fur, or hair")
    appendages_or_parts: List[str] = Field(default_factory=list)
    sensory_features: List[str] = Field(default_factory=list, description="Face-like features, eyes, sensors, symbols, or an explicit lack of them")
    locomotion: str = ""
    face_check_applicable: bool = False
    identity_features: List[CharacterVisualFeature] = Field(default_factory=list)
    # Psychological / Narrative Design
    external_goal: str = ""
    internal_need: str = ""
    core_fear: str = ""
    wound_or_ghost: str = ""
    core_contradiction: str = ""
    misbelief: str = ""
    stakes_personal: str = ""
    strengths: List[str] = Field(default_factory=list)
    flaws: List[str] = Field(default_factory=list)
    coping_mechanisms: List[str] = Field(default_factory=list)
    vulnerabilities: List[str] = Field(default_factory=list)
    voice_and_speech: str = ""
    values_and_morals: List[str] = Field(default_factory=list)
    pressure_response: str = ""
    backstory: str = ""
    secrets: List[str] = Field(default_factory=list)
    arc_checkpoints: List[CharacterArcCheckpoint] = Field(default_factory=list)
    # Visual Identity & Silhouette Design
    silhouette_and_proportions: str = ""
    face_design: str = ""
    hair_silhouette_and_color: str = ""
    distinctive_features: List[str] = Field(default_factory=list)  # e.g. white streak on left, small scar
    base_outfit: Optional[OutfitVariant] = None
    outfit_variants: List[OutfitVariant] = Field(default_factory=list)
    palette_and_values: List[str] = Field(default_factory=list)
    posture_and_movement: str = ""
    visual_motifs: List[str] = Field(default_factory=list)
    visual_invariants: List[str] = Field(default_factory=list)  # MANDATORY INVARIANTS NEVER COMPROMISED
    allowed_variations: List[str] = Field(default_factory=list)
    forbidden_visual_drift: List[str] = Field(default_factory=list)
    # Production Reference Sheet Data
    reference_asset_ids: List[str] = Field(default_factory=list)
    reference_sheet_specs: List[str] = Field(default_factory=list)
    generated_prompts: Dict[str, str] = Field(default_factory=dict)
    approval_status: Literal["draft", "needs_review", "approved", "superseded"] = "draft"
    version: int = 1

# =============================================================================
# 4. Ensemble & Relationship Map
# =============================================================================

class RelationshipEdge(BaseModel):
    source_character_id: str
    target_character_id: str
    relationship_type: str  # ally, rival, protector, dependent, distrusted_partner, enemy
    what_source_wants_from_target: str
    what_target_wants_from_source: str
    trust_level: str  # high_trust, guarded_trust, mutual_suspicion, adversarial
    conflict_dynamic: str
    power_asymmetry: str  # source_dominant, target_dominant, balanced, volatile
    shared_secrets: List[str] = Field(default_factory=list)
    information_asymmetry: str = ""
    shared_history_and_disputes: str = ""
    current_status: str
    potential_pivot_events: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def status(self) -> str:
        return self.current_status

    @computed_field
    @property
    def core_dynamic(self) -> str:
        return self.conflict_dynamic

class RelationshipNode(BaseModel):
    character_id: str

class RelationshipGraph(BaseModel):
    project_id: str
    characters: List[str] = Field(default_factory=list)
    edges: List[RelationshipEdge] = Field(default_factory=list)
    ensemble_differentiators: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def nodes(self) -> List[str]:
        return self.characters

# =============================================================================
# 5. World / Location / Object Bible
# =============================================================================

class MagicOrTechAbilityRule(BaseModel):
    name: str
    ability_id: Optional[str] = None
    practitioners: List[str] = Field(default_factory=list)
    mechanism: str = ""
    description: str = ""
    trigger_condition: str = ""
    sensory_manifestation: str = ""
    cost_or_strain: str = ""  # Cost is strictly mandatory to prevent god-mode
    failure_mode_or_risk: str = ""
    absolute_limit: str = ""
    narrative_consequence: str = ""

class LocationStateVariant(BaseModel):
    """A temporary, reusable scene condition that never overwrites the location canon."""
    variant_id: str
    name: str
    time_of_day: Optional[str] = None
    season: Optional[str] = None
    weather: Optional[str] = None
    lighting: Optional[str] = None
    visible_changes: List[str] = Field(default_factory=list)
    scene_condition: Optional[str] = None


class LocationSpec(BaseModel):
    location_id: str
    name: str
    atmosphere: str
    spatial_layout: str
    visual_anchors: List[str] = Field(default_factory=list)
    lighting_conditions: str
    narrative_use: str
    continuity_rules: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    location_type: str = ""
    geographic_context: str = ""
    scale: str = ""
    parent_location_id: Optional[str] = None
    zones: List[str] = Field(default_factory=list)
    environment_details: Dict[str, str] = Field(default_factory=dict)
    state_variants: List[LocationStateVariant] = Field(default_factory=list)
    source_location_id: Optional[str] = None
    version: int = Field(default=1, ge=1)
    version_history: List[Dict[str, Any]] = Field(default_factory=list)

class PropArtifactSpec(BaseModel):
    prop_id: str
    name: str
    description: str
    current_owner: Optional[str] = None
    historical_origin: str
    narrative_function: str
    state_and_damage: str
    visual_invariants: List[str] = Field(default_factory=list)

class WorldBible(BaseModel):
    project_id: str
    world_name: str
    core_laws_and_physics: List[str] = Field(default_factory=list)
    geography_and_climate: str
    culture_and_society: str
    institutions_and_factions: List[str] = Field(default_factory=list)
    supernatural_or_tech_rules: List[MagicOrTechAbilityRule] = Field(default_factory=list)
    locations: Dict[str, LocationSpec] = Field(default_factory=dict)
    props: Dict[str, PropArtifactSpec] = Field(default_factory=dict)
    continuity_timeline_rules: List[str] = Field(default_factory=list)
    version: int = 1

    @computed_field
    @property
    def magic_or_tech_rules(self) -> List[MagicOrTechAbilityRule]:
        return self.supernatural_or_tech_rules

# =============================================================================
# 6. Narrative Structure & Episode Outlines
# =============================================================================

class SceneCandidate(BaseModel):
    scene_id: str
    title: str
    narrative_purpose: str
    participating_character_ids: List[str] = Field(default_factory=list)
    location_id: str
    key_action_or_revelation: str
    emotional_beat: str
    estimated_panel_count: int = 5

class ChapterOutline(BaseModel):
    chapter_number: int
    title: str
    purpose_in_arc: str
    turning_point: str
    emotional_shift: str
    ending_hook_or_cliffhanger: str
    scene_candidates: List[SceneCandidate] = Field(default_factory=list)

    @computed_field
    @property
    def emotional_turning_point(self) -> str:
        return self.turning_point or self.emotional_shift or "Turning point"

class SetupPayoffItem(BaseModel):
    setup_id: str
    setup_event: str
    setup_chapter: int
    payoff_event: str
    payoff_chapter: int
    status: Literal["planned", "unresolved", "paid_off"] = "planned"

class NarrativeStructure(BaseModel):
    project_id: str
    central_conflict: str
    opposition_engine: str
    macro_arc_beats: Dict[str, str] = Field(default_factory=dict)  # inciting_incident, midpoint, crisis, climax
    chapters: List[ChapterOutline] = Field(default_factory=list)
    setup_payoff_ledger: List[SetupPayoffItem] = Field(default_factory=list)
    unresolved_threads: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def chapter_outlines(self) -> List[ChapterOutline]:
        return self.chapters

    @computed_field
    @property
    def act_breakdown(self) -> List[Dict[str, Any]]:
        return [
            {"act": 1, "name": "Departure / Inciting Incident", "beat": self.macro_arc_beats.get("inciting_incident", "")},
            {"act": 2, "name": "Confrontation / Midpoint", "beat": self.macro_arc_beats.get("midpoint", "")},
            {"act": 3, "name": "Resolution / Climax", "beat": self.macro_arc_beats.get("climax", "")},
        ]

# =============================================================================
# 7. Visual Style Profile (Style Copier Compatible)
# =============================================================================

class VisualStyleProfile(BaseModel):
    style_id: str
    name: str
    medium: str = "Stylized Comic & Graphic Novel Illustration"
    line_art_rules: List[str] = Field(default_factory=list)
    shape_language: str = "Defined contours with expressive character anatomy"
    facial_drawing_conventions: str = "Consistent facial proportions, clean expressive features"
    tonal_value_rules: List[str] = Field(default_factory=list)
    lighting_rules: List[str] = Field(default_factory=list)
    palette_and_accent_rules: List[str] = Field(default_factory=list)
    surface_texture_and_grain: str = "Clean illustration finish with natural surface texture"
    background_detail_density: str = "Balanced background environment complementing character focus"
    screentones_and_fx: List[str] = Field(default_factory=list)
    negative_constraints: List[str] = Field(default_factory=list)
    reference_asset_ids: List[str] = Field(default_factory=list)
    approval_status: Literal["draft", "needs_review", "approved", "superseded"] = "draft"
    version: int = 1

# =============================================================================
# 8. Character Sheet Plans (E1 Generation Jobs)
# =============================================================================

class SheetViewSpec(BaseModel):
    view_type: str  # identity_overview, form_turnaround, identity_feature_detail, approved_variation; extensible for any being
    prompt: str
    negative_prompt: str
    aspect_ratio: str = "1:1"
    width: int = 1024
    height: int = 1024
    status: Literal["pending", "queued", "generating", "completed", "failed"] = "pending"
    generated_asset_id: Optional[str] = None
    generated_image_url: Optional[str] = None
    error: Optional[str] = None

class CharacterSheetPlan(BaseModel):
    plan_id: str
    project_id: str
    character_id: str
    character_name: str
    views: List[SheetViewSpec] = Field(default_factory=list)
    estimated_cost_usd: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @computed_field
    @property
    def required_views(self) -> List[SheetViewSpec]:
        return self.views

# =============================================================================
# 9. Machine-Readable Creative Contracts (Downstream Consumable)
# =============================================================================

class ProjectCanonContract(BaseModel):
    contract_id: str
    project_id: str
    version: int = 1
    canon_hash: str
    status: Literal["draft", "needs_review", "approved", "superseded"] = "draft"
    approved_facts: List[str] = Field(default_factory=list)
    proposed_facts: List[str] = Field(default_factory=list)
    content_boundaries: List[str] = Field(default_factory=list)
    provenance: Dict[str, str] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CharacterIdentityContract(BaseModel):
    contract_id: str
    character_id: str
    version: int = 1
    status: Literal["draft", "needs_review", "approved", "superseded"] = "draft"
    mandatory_visual_invariants: List[str] = Field(default_factory=list)
    allowed_variations: List[str] = Field(default_factory=list)
    forbidden_drift: List[str] = Field(default_factory=list)
    reference_asset_roles: Dict[str, str] = Field(default_factory=dict)
    verifier_tolerances: Dict[str, Any] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @computed_field
    @property
    def mandatory_invariants(self) -> List[str]:
        return self.mandatory_visual_invariants

    @computed_field
    @property
    def forbidden_visual_drift(self) -> List[str]:
        return self.forbidden_drift

    @computed_field
    @property
    def character_name(self) -> str:
        return self.character_id.capitalize()

class VisualStyleContract(BaseModel):
    contract_id: str
    style_id: str
    version: int = 1
    status: Literal["draft", "needs_review", "approved", "superseded"] = "draft"
    style_dimensions: Dict[str, Any] = Field(default_factory=dict)
    negative_constraints: List[str] = Field(default_factory=list)
    reference_asset_roles: Dict[str, str] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @computed_field
    @property
    def target_medium(self) -> str:
        return self.style_dimensions.get("medium") or self.style_dimensions.get("target_medium") or "digital ink"

    @computed_field
    @property
    def medium(self) -> str:
        return self.target_medium

    @computed_field
    @property
    def rendering_invariants(self) -> List[str]:
        return self.style_dimensions.get("rendering_invariants") or ["clean ink linework", "halftone screentones"]

    @computed_field
    @property
    def negative_prompt_additions(self) -> List[str]:
        return self.negative_constraints

class WorldRuleContract(BaseModel):
    contract_id: str
    project_id: str
    version: int = 1
    supernatural_limits: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    continuity_consequences: List[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class GenerationConstraintContract(BaseModel):
    contract_id: str
    project_id: str
    target_character_ids: List[str] = Field(default_factory=list)
    required_tokens: List[str] = Field(default_factory=list)
    negative_tokens: List[str] = Field(default_factory=list)
    reference_asset_ids: List[str] = Field(default_factory=list)
    quality_gates: List[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CreativeContractsPackage(BaseModel):
    project_id: str
    canon_contract: ProjectCanonContract
    character_contracts: Dict[str, CharacterIdentityContract] = Field(default_factory=dict)
    style_contract: VisualStyleContract
    world_contract: WorldRuleContract
    generation_constraints: GenerationConstraintContract
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @computed_field
    @property
    def canon(self) -> ProjectCanonContract:
        return self.canon_contract

    @computed_field
    @property
    def characters(self) -> Dict[str, CharacterIdentityContract]:
        return self.character_contracts

    @computed_field
    @property
    def style(self) -> VisualStyleContract:
        return self.style_contract

    @computed_field
    @property
    def world(self) -> WorldRuleContract:
        return self.world_contract

# =============================================================================
# 10. Coherence Finding & Validation Report
# =============================================================================

class FindingSeverity(str, Enum):
    ERROR = "ERROR"              # Contradiction or broken rule (Blocks approval)
    WARNING = "WARNING"          # Incomplete attribute or ambiguous trait
    SUGGESTION = "SUGGESTION"    # Creative opportunity to deepen character/world

class FindingCategory(str, Enum):
    CHARACTER = "CHARACTER"
    STORY = "STORY"
    VISUAL = "VISUAL"
    WORLD = "WORLD"
    CONTRACT = "CONTRACT"
    CANON_CONFLICT = "CANON_CONFLICT"

class CoherenceFinding(BaseModel):
    finding_id: str
    severity: FindingSeverity
    category: FindingCategory
    message: str
    affected_artefact: str
    evidence: str
    suggested_correction: str
    entity_id: str = ""
    title: str = ""

class ValidationResult(BaseModel):
    project_id: str
    is_coherent: bool
    findings: List[CoherenceFinding] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# =============================================================================
# 11. Complete Aggregated Creative Package
# =============================================================================

class CreativePackage(BaseModel):
    project_id: str
    version: int = 1
    package_hash: str = ""
    brief: CreativeBrief
    story_bible: CreativeStoryBible
    characters: Dict[str, CharacterIdentityProfile] = Field(default_factory=dict)
    relationship_graph: RelationshipGraph
    world_bible: WorldBible
    narrative_structure: NarrativeStructure
    style_profile: VisualStyleProfile
    character_sheet_plans: Dict[str, CharacterSheetPlan] = Field(default_factory=dict)
    contracts: CreativeContractsPackage
    validation: ValidationResult
    completed_stages: List[str] = Field(default_factory=list)
    current_stage: str = "COMPLETE_WITH_RECEIPT"
    synthesis_source: str = "dynamic_procedural"  # "live_ai" or "dynamic_procedural"
    has_pending_approval: bool = False
    pending_proposal_diff: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
