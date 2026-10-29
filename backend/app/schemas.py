from enum import Enum
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# M0 Foundation Schemas (Preserved without modification)
# ---------------------------------------------------------------------------

class AttributeCheck(BaseModel):
    id: str = Field(..., description="Unique attribute identifier (e.g. hair, glasses, jacket)")
    text: str = Field(..., description="Canonical description of the attribute")
    required: bool = Field(default=True, description="Whether this attribute is mandatory for panel acceptance")

class Tolerances(BaseModel):
    min_face_px_for_check: int = Field(default=80, description="Minimum face pixel size required to run identity check")

class CharacterSpec(BaseModel):
    id: str = Field(..., description="Character identifier in lowercase (e.g. nour)")
    attributes: List[AttributeCheck] = Field(..., description="List of declared attributes to verify")
    tolerances: Tolerances = Field(default_factory=Tolerances)

class AttributeVerdict(BaseModel):
    attr_id: str
    verdict: Literal["pass", "fail", "unsure"]
    evidence: str

class VerificationResult(BaseModel):
    passed: bool = Field(..., description="True only if all required attributes have verdict 'pass'")
    verdicts: List[AttributeVerdict]
    rejection_reason: Optional[str] = None

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

class StoryBible(BaseModel):
    """External structured Story Bible — the single source of truth for canon."""
    bible_id: str = Field(..., description="Unique Story Bible identifier")
    version: str = Field(default="1.0.0", description="Story Bible version string or content hash")
    project_id: str = Field(default="inkloop", description="Project identifier")
    style: StyleBible = Field(default_factory=StyleBible)
    characters: Dict[str, CharacterSpec] = Field(default_factory=dict, description="Declared characters keyed by id")
    character_assets: Dict[str, ReferenceAsset] = Field(default_factory=dict, description="Canonical reference assets keyed by character id")
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
    scene_state: Dict[str, Any] = Field(default_factory=dict, description="Explicit narrative state deltas (e.g. outfit variations, props held)")
    panel_instructions: Optional[str] = Field(default=None, description="Panel-specific composition directives")
    dimensions: Optional[List[int]] = Field(default=None, description="Target pixel dimensions [width, height]")
    aspect_ratio: Optional[str] = Field(default=None, description="Aspect ratio constraint (e.g. 2:3, 3:2, 1:1)")
    previous_panel_id: Optional[str] = Field(default=None, description="Preceding panel ID if applicable")
    previous_panel_summary: Optional[str] = Field(default=None, description="Explicit summary of prior panel beat")

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
    scene_description: str
    generation_prompt: str
    character_ids: List[str]
    character_specs: List[CharacterSpec]
    reference_assets: List[ReferenceAsset]
    dimensions: Optional[List[int]] = None
    aspect_ratio: Optional[str] = None
    previous_panel_continuity: Optional[str] = None
    scene_state: Dict[str, Any] = Field(default_factory=dict)
    visual_invariants: List[str] = Field(default_factory=list)
    prohibited_deviations: List[str] = Field(default_factory=list)
    model: str
    generation_params: Dict[str, Any] = Field(default_factory=dict)
    context_fingerprint: str = Field(..., description="Deterministic SHA-256 hash of canonical packet content")

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

class BatchSummary(BaseModel):
    """Auditable batch execution summary with complete attempt provenance."""
    batch_id: str
    status: BatchStatus
    story_id: str
    bible_version: str
    total_panels: int
    successful_panels: int
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
