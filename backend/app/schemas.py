from enum import Enum
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.planning.panel_planner import PanelPlan

# ---------------------------------------------------------------------------
# M0 Foundation Schemas (Preserved without modification)
# ---------------------------------------------------------------------------

class AttributeCheck(BaseModel):
    id: str = Field(..., description="Unique attribute identifier (e.g. hair, glasses, jacket)")
    text: str = Field(..., description="Canonical description of the attribute")
    required: bool = Field(default=True, description="Whether this attribute is mandatory for panel acceptance")

class Tolerances(BaseModel):
    min_face_px_for_check: int = Field(default=80, description="Minimum face pixel size required to run identity check")
    face_check_applicable: bool = Field(default=True, description="Whether this identity has face-specific landmarks that should be checked")

    @property
    def min_face_resolution_px(self) -> int:
        """Backwards compatibility alias for min_face_px_for_check."""
        return self.min_face_px_for_check

    def __init__(self, **data: Any):
        if "min_face_resolution_px" in data and "min_face_px_for_check" not in data:
            data["min_face_px_for_check"] = data.pop("min_face_resolution_px")
        super().__init__(**data)

class CharacterSpec(BaseModel):
    id: str = Field(..., description="Character identifier in lowercase (e.g. nour)")
    name: Optional[str] = Field(default=None, description="Character display name")
    entity_kind: str = Field(default="unspecified being", description="Open vocabulary for any human, creature, object-like, abstract, or hybrid identity")
    morphology: str = Field(default="", description="Declared overall form/body plan; no human anatomy is implied")
    surface_description: str = Field(default="", description="Declared colors, material, texture, or pattern")
    physical_height_cm: Optional[float] = Field(default=None, description="Canonical physical height in centimeters")
    proportion_constraints: Optional[Dict[str, Any]] = Field(default=None, description="Structured proportion guidelines (e.g. {'head_ratio': 0.60, 'body_ratio': 0.40})")
    attributes: List[AttributeCheck] = Field(..., description="List of declared attributes to verify")
    tolerances: Tolerances = Field(default_factory=lambda: Tolerances(face_check_applicable=False))
    visual_invariants: List[str] = Field(default_factory=list, description="Explicit character visual invariants")
    restrictions: List[str] = Field(default_factory=list, description="Character-specific negative constraints")
    clothing_attributes: List[str] = Field(default_factory=list, description="Canonical clothing traits")

class AttributeVerdict(BaseModel):
    attr_id: str
    verdict: Literal["pass", "fail", "unsure"]
    evidence: str

class VerificationResult(BaseModel):
    passed: bool = Field(..., description="True only if all required attributes have verdict 'pass'")
    verdicts: List[AttributeVerdict]
    rejection_reason: Optional[str] = None
    l0_passed: Optional[bool] = None
    l1_passed: Optional[bool] = None
    l2_passed: Optional[bool] = None
    is_simulated: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float
    label: str
    confidence: float

    def to_rect(self):
        from app.contracts.geometry import Rect
        return Rect(x=self.x, y=self.y, width=self.width, height=self.height)

    @classmethod
    def from_rect(cls, rect, label: str = "subject", confidence: float = 1.0):
        return cls(x=rect.x, y=rect.y, width=rect.width, height=rect.height, label=label, confidence=confidence)

class SegmentationResult(BaseModel):
    subject_count: int
    boxes: List[BoundingBox]
    mask_available: bool = False
    mask_sha256: Optional[str] = None

# ---------------------------------------------------------------------------
# M1 Orchestration & Story Bible Schemas (Task 4)
# ---------------------------------------------------------------------------

class ReferenceAsset(BaseModel):
    """Canonical visual reference asset anchored in the Story Bible."""
    asset_id: str = Field(..., description="Stable asset identifier (e.g. nour_reference)")
    file_path: str = Field(..., description="Relative or absolute filesystem path to asset")
    content_hash: str = Field(..., description="SHA-256 hash of the asset bytes")
    mime_type: str = Field(default="image/png", description="MIME type of the asset")
    description: Optional[str] = Field(default=None, description="Descriptive label of the reference image")

class StyleBible(BaseModel):
    """Visual style rules and negative constraints for the production run."""
    id: str = Field(default="bw_screentone", description="Style identifier")
    name: str = Field(default="B&W Ink & Screentone", description="Human-readable style name")
    medium: str = Field(default="black and white comic ink", description="Visual medium")
    line_and_tone: str = Field(default="clean linework with screentone shading", description="Linework and tone description")
    palette: str = Field(default="monochrome", description="Color palette specification")
    negative_rules: List[str] = Field(default_factory=lambda: [
        "no dialogue text",
        "no speech bubbles",
        "no watermarks",
        "no signatures",
        "no blurry artifacts"
    ], description="Negative constraints for the style")
    version: str = Field(default="1.0.0", description="Semantic version of the style specification")
    line_art_rules: List[str] = Field(default_factory=list, description="Rules governing line weight and contours")
    tonal_rules: List[str] = Field(default_factory=list, description="Rules for screentone density, hatching, and solid blacks")
    positive_constraints: List[str] = Field(default_factory=list, description="Required positive visual tokens/rules")
    lighting_constraints: List[str] = Field(default_factory=list, description="Canonical lighting rules")
    background_detail_rules: str = Field(default="", description="Guidance on background density vs subject focus")

class LocationSpec(BaseModel):
    """Specification of a narrative location/setting."""
    location_id: str = Field(..., description="Unique location identifier")
    name: str = Field(..., description="Location display name")
    description: str = Field(default="", description="Visual and narrative description")
    required_attributes: List[str] = Field(default_factory=list, description="Mandatory visual attributes")
    version: str = Field(default="1.0.0", description="Specification version")

class PropSpec(BaseModel):
    """Specification of a narrative prop."""
    prop_id: str = Field(..., description="Unique prop identifier")
    name: str = Field(..., description="Prop display name")
    description: str = Field(default="", description="Visual and physical description")
    required_attributes: List[str] = Field(default_factory=list, description="Mandatory visual attributes")
    reference_assets: List[ReferenceAsset] = Field(default_factory=list, description="Verified visual identity references")
    form_and_proportions: str = ""
    materials: List[str] = Field(default_factory=list)
    palette: List[str] = Field(default_factory=list)
    components: List[str] = Field(default_factory=list)
    distinctive_marks: List[str] = Field(default_factory=list)
    stable_invariants: List[str] = Field(default_factory=list)
    allowed_states: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0", description="Specification version")

class StoryBible(BaseModel):
    """External structured Story Bible — the single source of truth for canon."""
    bible_id: str = Field(..., description="Unique Story Bible identifier")
    version: str = Field(default="1.0.0", description="Story Bible version string or content hash")
    canon_hash: Optional[str] = Field(default=None, description="Cryptographic hash of canon definitions")
    project_id: str = Field(default="inkloop", description="Project identifier")
    style: StyleBible = Field(default_factory=StyleBible)
    characters: Dict[str, CharacterSpec] = Field(default_factory=dict, description="Declared characters keyed by id")
    character_assets: Dict[str, ReferenceAsset] = Field(default_factory=dict, description="Canonical reference assets keyed by character id")
    locations: Dict[str, LocationSpec] = Field(default_factory=dict, description="Declared locations keyed by id")
    props: Dict[str, PropSpec] = Field(default_factory=dict, description="Declared props keyed by id")
    story_facts: List[str] = Field(default_factory=list, description="Story-wide canonical facts")

class SceneSpec(BaseModel):
    """Specification of a single narrative scene/beat within a story."""
    scene_id: str = Field(..., description="Unique scene identifier (e.g. scene_01)")
    scene_index: int = Field(..., description="Sequential position in canonical story order (0-indexed)")
    title: str = Field(..., description="Scene title or slug")
    shot_type: str = Field(..., description="Camera framing and shot scale (e.g. medium close-up, front view)")
    action: str = Field(..., description="Subject action and behavior description")
    camera_angle: Optional[str] = Field(default=None, description="Camera perspective or angle")
    lighting: Optional[str] = Field(default=None, description="Scene lighting description")
    character_ids: List[str] = Field(default_factory=list, description="List of character IDs present in this scene")
    prop_ids: List[str] = Field(default_factory=list, description="Stable IDs of recurring objects visible in this panel")
    prop_states: Dict[str, str] = Field(default_factory=dict, description="Panel-specific state for selected recurring objects")
    scene_state: Dict[str, Any] = Field(default_factory=dict, description="Explicit narrative state deltas (e.g. outfit variations, props held)")
    panel_instructions: Optional[str] = Field(default=None, description="Panel-specific composition directives")
    dimensions: Optional[List[int]] = Field(default=None, description="Target pixel dimensions [width, height]")
    aspect_ratio: Optional[str] = Field(default=None, description="Aspect ratio constraint (e.g. 2:3, 3:2, 1:1)")
    previous_panel_id: Optional[str] = Field(default=None, description="Preceding panel ID if applicable")
    previous_panel_summary: Optional[str] = Field(default=None, description="Explicit summary of prior panel beat")
    panel_plan: Optional[PanelPlan] = Field(
        default=None,
        description="Accepted S5 plan for this panel; when supplied, its shot/composition/event fields are authoritative for context compilation.",
    )

class PanelContextPacket(BaseModel):
    """
    Independent per-panel continuity packet assembled purely by code.
    No conversational memory or implicit context is carried between API calls.
    """
    story_id: str
    project_id: str
    bible_id: str
    bible_version: str
    panel_id: str
    scene_id: str
    scene_index: int
    panel_plan: Optional[Dict[str, Any]] = Field(default=None, description="Accepted S5 plan included in prompt compilation and fingerprinting")
    scene_description: str
    generation_prompt: str
    character_ids: List[str]
    character_specs: List[CharacterSpec]
    reference_assets: List[ReferenceAsset]
    prop_ids: List[str] = Field(default_factory=list)
    prop_specs: Dict[str, PropSpec] = Field(default_factory=dict)
    prop_reference_assets: List[ReferenceAsset] = Field(default_factory=list)
    prop_states: Dict[str, str] = Field(default_factory=dict)
    dimensions: Optional[List[int]] = None
    aspect_ratio: Optional[str] = None
    previous_panel_continuity: Optional[str] = None
    scene_state: Dict[str, Any] = Field(default_factory=dict)
    visual_invariants: List[str] = Field(default_factory=list)
    prohibited_deviations: List[str] = Field(default_factory=list)
    model: str
    generation_params: Dict[str, Any] = Field(default_factory=dict)
    context_fingerprint: str = Field(..., description="Deterministic SHA-256 hash of canonical packet content")
    catalogue_version: Optional[str] = None
    knowledge_selection_hash: Optional[str] = None
    selected_knowledge_ids: List[str] = Field(default_factory=list, description="IDs of knowledge rules/recipes selected from catalogue")
    knowledge_provenance_ids: List[str] = Field(default_factory=list, description="IDs of supporting bibliographic/experimental sources")
    knowledge_rationale: Dict[str, str] = Field(default_factory=dict, description="Explainable selection rationale per item")

class ErrorCategory(str, Enum):
    CONTENT_POLICY_VIOLATION = "CONTENT_POLICY_VIOLATION"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    BAD_REQUEST = "BAD_REQUEST"
    SERVER_ERROR = "SERVER_ERROR"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    UNKNOWN = "UNKNOWN"

class RetryDecision(str, Enum):
    RETRY_WITH_CORRECTION = "RETRY_WITH_CORRECTION"
    RETRY_SIMPLIFY = "RETRY_SIMPLIFY"
    DO_NOT_RETRY_PERMANENT = "DO_NOT_RETRY_PERMANENT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    MAX_RETRIES_REACHED = "MAX_RETRIES_REACHED"
    NONE_SUCCESS = "NONE_SUCCESS"

class PanelStatus(str, Enum):
    """
    Status of an individual panel slot.
    - PENDING: Generation not yet attempted.
    - GENERATED_PENDING_VERIFICATION: Image generation succeeded, but visual verification has not passed or is pending.
    - ACCEPTED: Image generated AND passed verification gate (or accepted by downstream pipeline).
    - REJECTED_BY_VERIFIER: Image generated but failed visual checklist check.
    - FAILED: Generation error or budget exceeded.
    - NEEDS_HUMAN: Bounded retries exhausted or verifier returned inconclusive judgment.
    """
    PENDING = "PENDING"
    GENERATED_PENDING_VERIFICATION = "GENERATED_PENDING_VERIFICATION"
    ACCEPTED = "ACCEPTED"
    REJECTED_BY_VERIFIER = "REJECTED_BY_VERIFIER"
    FAILED = "FAILED"
    NEEDS_HUMAN = "NEEDS_HUMAN"

class BatchStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_FAILURES = "COMPLETED_WITH_FAILURES"
    FAILED = "FAILED"

class GenerationAttemptRecord(BaseModel):
    """Immutable structured audit record for an individual generation attempt."""
    batch_id: str
    panel_id: str
    scene_id: str
    attempt_id: str
    attempt_number: int
    retry_count: int = Field(default=0, description="0-based retry counter (0 for initial call)")
    is_simulated: bool = Field(default=False, description="True if simulated test adapter; False for live Meta API calls")
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    story_bible_version: str
    context_fingerprint: str
    reference_asset_ids: List[str] = Field(default_factory=list)
    reference_asset_hashes: Dict[str, str] = Field(default_factory=dict)
    model: str
    endpoint: str
    sanitized_request_metadata: Dict[str, Any] = Field(default_factory=dict)
    http_status: Optional[int] = None
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    retry_decision: Optional[str] = None
    retry_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    cost_usd: Optional[float] = None
    output_asset_path: Optional[str] = None
    output_asset_id: Optional[str] = None
    output_content_hash: Optional[str] = None
    verification_status: Optional[str] = None
    verification_result: Optional[VerificationResult] = None
    final_panel_status: str = Field(default=PanelStatus.PENDING)

class PanelResult(BaseModel):
    """Final accepted or unresolved outcome for a single panel slot."""
    panel_id: str
    scene_id: str
    scene_index: int
    status: PanelStatus
    attempts_count: int
    accepted_attempt_id: Optional[str] = None
    output_asset_path: Optional[str] = None
    output_content_hash: Optional[str] = None
    context_fingerprint: str
    verification_status: str = Field(default="UNVERIFIED", description="Verification outcome: 'PASSED', 'FAILED', 'UNSURE', or 'UNVERIFIED'")
    verification_result: Optional[VerificationResult] = None

class BatchSpec(BaseModel):
    """Input specification for orchestrating multi-panel generation."""
    batch_id: str = Field(..., description="Stable batch identifier")
    project_id: str = Field(default="inkloop")
    story_id: str = Field(default="story_01")
    story_bible: Any = Field(..., description="Story Bible specification (app.schemas.StoryBible or app.project.StoryBible)")
    scenes: List[SceneSpec]
    model: str = Field(default="muse-image-1.0")
    max_retries_per_panel: int = Field(default=2)
    spend_cap_usd: float = Field(default=25.0)
    output_dir: Optional[str] = None
    require_verification: bool = Field(default=False, description="If True, panels without passing verifier verdict stay in GENERATED_PENDING_VERIFICATION")
    request_fingerprint: Optional[str] = Field(default=None, description="Stable hash used to make batch submission retries idempotent")

class BatchSummary(BaseModel):
    """Auditable batch execution summary with complete attempt provenance."""
    batch_id: str
    status: BatchStatus
    project_id: str = "default_project"
    story_id: str
    bible_version: str
    total_panels: int
    successful_panels: int
    generated_panels: int = Field(default=0, description="Total panels rendered by image generation adapter")
    verified_panels: int = Field(default=0, description="Total panels that passed visual verification")
    failed_panels: int
    unresolved_panels: int
    unverified_panels: int = Field(default=0, description="Panels generated but awaiting visual verification")
    total_attempts: int
    attempts_per_panel: Dict[str, int]
    total_duration_seconds: float
    started_at: str
    completed_at: Optional[str] = None
    is_simulated: bool = Field(default=False, description="True if simulated test run; False if executed against live provider")
    cost_mode: str = Field(default="real", description="Cost accounting mode: 'real', 'synthetic_simulated', or 'unknown'")
    known_cost_usd: Optional[float] = None
    simulated_cost_usd: Optional[float] = None
    missing_cost_information: bool = False
    known_usage: Dict[str, Any] = Field(default_factory=dict)
    simulated_usage: Optional[Dict[str, Any]] = None
    missing_usage_information: bool = False
    panel_results: List[PanelResult] = Field(default_factory=list)
    attempt_history: List[GenerationAttemptRecord] = Field(default_factory=list)
    source_scenes: List[SceneSpec] = Field(default_factory=list, description="Original typed scene inputs required for truthful job resume")
    model: str = "muse-image-1.0"
    max_retries_per_panel: int = 2
    spend_cap_usd: Optional[float] = None
    require_verification: bool = False
    request_fingerprint: Optional[str] = None
