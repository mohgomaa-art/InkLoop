/**
 * InkLoop Canonical Shared Contracts (TypeScript Mirror).
 * Auto-aligned with backend/app/contracts/*.py schemas.
 * 
 * Rules:
 * - Origin: Top-Left (0.0, 0.0)
 * - Positive axes: +X right, +Y down
 * - Primary units: Screen/Render Pixels (px) at 300 DPI (print) or 96/72 DPI (web)
 * - Rasterization interval: Half-open [x, x + width) x [y, y + height)
 * - Rotation: Degrees (deg), clockwise positive
 * - Color spaces: sRGB, Display P3, CMYK (FOGRA39 / SWOP), Grayscale
 * - Alpha modes: Straight, Premultiplied, Opaque
 */

// --- Error and Validation Contracts ---

export enum ErrorSeverity {
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
}

export enum ErrorCode {
  // Schema & Contract Errors (1000s)
  INVALID_SCHEMA = 'ERR_1001_INVALID_SCHEMA',
  MISSING_REQUIRED_FIELD = 'ERR_1002_MISSING_REQUIRED_FIELD',
  INVALID_FIELD_TYPE = 'ERR_1003_INVALID_FIELD_TYPE',
  INVALID_IDENTIFIER_FORMAT = 'ERR_1004_INVALID_IDENTIFIER_FORMAT',
  UNKNOWN_ENTITY_REFERENCE = 'ERR_1005_UNKNOWN_ENTITY_REFERENCE',
  VERSION_MISMATCH = 'ERR_1006_VERSION_MISMATCH',

  // Geometry & Spatial Errors (2000s)
  ZERO_OR_NEGATIVE_DIMENSION = 'ERR_2001_ZERO_OR_NEGATIVE_DIMENSION',
  NON_FINITE_COORDINATE = 'ERR_2002_NON_FINITE_COORDINATE',
  OUT_OF_BOUNDS = 'ERR_2003_OUT_OF_BOUNDS',
  PANEL_UNINTENDED_OVERLAP = 'ERR_2004_PANEL_UNINTENDED_OVERLAP',
  INVALID_TRANSFORM_MATRIX = 'ERR_2005_INVALID_TRANSFORM_MATRIX',
  ASPECT_RATIO_DISTORTION = 'ERR_2006_ASPECT_RATIO_DISTORTION',
  IMPOSSIBLE_FIT = 'ERR_2007_IMPOSSIBLE_FIT',

  // Story Bible & Canon Errors (3000s)
  UNDECLARED_CHARACTER = 'ERR_3001_UNDECLARED_CHARACTER',
  UNDECLARED_PROP = 'ERR_3002_UNDECLARED_PROP',
  UNDECLARED_LOCATION = 'ERR_3003_UNDECLARED_LOCATION',
  CANON_MUTATION_REJECTED = 'ERR_3004_CANON_MUTATION_REJECTED',
  CHRONOLOGY_VIOLATION = 'ERR_3005_CHRONOLOGY_VIOLATION',
  SPEAKER_MISMATCH = 'ERR_3006_SPEAKER_MISMATCH',

  // External Provider & Network Errors (4000s)
  PROVIDER_AUTH_FAILED = 'ERR_4001_PROVIDER_AUTH_FAILED',
  PROVIDER_RATE_LIMITED = 'ERR_4002_PROVIDER_RATE_LIMITED',
  PROVIDER_TIMEOUT = 'ERR_4003_PROVIDER_TIMEOUT',
  CONTENT_POLICY_VIOLATION = 'ERR_4004_CONTENT_POLICY_VIOLATION',
  PROVIDER_SERVICE_UNAVAILABLE = 'ERR_4005_PROVIDER_SERVICE_UNAVAILABLE',
  BUDGET_EXCEEDED = 'ERR_4006_BUDGET_EXCEEDED',

  // Verification & Quality Gate Errors (5000s)
  VERIFICATION_FAILED = 'ERR_5001_VERIFICATION_FAILED',
  VERIFICATION_UNSURE = 'ERR_5002_VERIFICATION_UNSURE',
  FACE_TOO_SMALL_FOR_VERIFICATION = 'ERR_5003_FACE_TOO_SMALL_FOR_VERIFICATION',
  TEXT_INTEGRITY_MISMATCH = 'ERR_5004_TEXT_INTEGRITY_MISMATCH',
  TEXT_OVERFLOW_COLLISION = 'ERR_5005_TEXT_OVERFLOW_COLLISION',

  // Engine Execution & Lifecycle States (6000s)
  ENGINE_NOT_IMPLEMENTED_YET = 'ERR_6001_ENGINE_NOT_IMPLEMENTED_YET',
  ENGINE_EXPERIMENTAL_FEATURE = 'ERR_6002_ENGINE_EXPERIMENTAL_FEATURE',
  ENGINE_CRASH = 'ERR_6003_ENGINE_CRASH',
  MAX_RETRIES_EXCEEDED = 'ERR_6004_MAX_RETRIES_EXCEEDED',
  RUN_CANCELLED = 'ERR_6005_RUN_CANCELLED',
}

export interface ValidationErrorDetail {
  code: ErrorCode;
  message: string;
  field?: string | null;
  entity_id?: string | null;
  severity: ErrorSeverity;
  retryable: boolean;
  diagnostic_data?: Record<string, unknown>;
}

export interface EngineFailure {
  code: ErrorCode;
  message: string;
  stage: string;
  retryable: boolean;
  http_status?: number | null;
  raw_provider_error?: string | null;
  validation_details: ValidationErrorDetail[];
}

// --- Identity and Entity Reference Contracts ---

export enum IdPrefix {
  PROJECT = 'proj',
  STORY = 'story',
  CHAPTER = 'ch',
  SCENE = 'scene',
  PAGE = 'page',
  PANEL = 'panel',
  CHARACTER = 'char',
  CHARACTER_VERSION = 'char_ver',
  ASSET = 'asset',
  ARTIFACT = 'art',
  RUN = 'run',
  ATTEMPT = 'att',
  QA = 'qa',
  FONT = 'font',
  TEXT = 'txt',
  BUBBLE = 'bbl',
  EFFECT = 'fx',
  CANVAS = 'canvas',
  TAXONOMY = 'tax',
}

export interface EntityRef {
  id: string;
  prefix: IdPrefix;
  version?: string | null;
}

export interface ProjectRef {
  project_id: string;
}

export interface StoryRef {
  project_id: string;
  story_id: string;
  story_version: number;
}

export interface ChapterRef {
  story_id: string;
  chapter_id: string;
  order: number;
}

export interface SceneRef {
  story_id: string;
  scene_id: string;
  order: number;
}

export interface PageRef {
  project_id: string;
  page_id: string;
  page_number: number;
}

export interface PanelRef {
  page_id: string;
  panel_id: string;
  order_in_page: number;
  scene_id?: string | null;
}

// --- Geometry Contracts ---

export enum CoordinateSpace {
  PAGE = 'page',
  PANEL_SLOT = 'panel_slot',
  SOURCE_IMAGE = 'source_image',
  TEXT_LAYER = 'text_layer',
  BUBBLE = 'bubble',
  EFFECT_MASK = 'effect_mask',
  VIEWPORT = 'viewport',
  NORMALIZED = 'normalized',
}

export enum FitMode {
  CONTAIN = 'contain',
  COVER = 'cover',
  CROP_TO_FRAME = 'crop_to_frame',
  STRETCH = 'stretch',
  MANUAL = 'manual',
}

export enum ColorSpace {
  SRGB = 'srgb',
  DISPLAY_P3 = 'display_p3',
  CMYK_FOGRA39 = 'cmyk_fogra39',
  CMYK_SWOP = 'cmyk_swop',
  GRAYSCALE = 'grayscale',
}

export enum AlphaMode {
  STRAIGHT = 'straight',
  PREMULTIPLIED = 'premultiplied',
  OPAQUE = 'opaque',
}

export enum BlendMode {
  NORMAL = 'normal',
  MULTIPLY = 'multiply',
  SCREEN = 'screen',
  OVERLAY = 'overlay',
  DARKEN = 'darken',
  LIGHTEN = 'lighten',
  COLOR_DODGE = 'color_dodge',
  COLOR_BURN = 'color_burn',
  HARD_LIGHT = 'hard_light',
  SOFT_LIGHT = 'soft_light',
}

export enum AssetFormat {
  PNG = 'png',
  WEBP = 'webp',
  JPEG = 'jpeg',
  SVG = 'svg',
  PDF = 'pdf',
  TIFF = 'tiff',
}

export enum ClipMode {
  CLIP_TO_PANEL = 'clip_to_panel',
  BLEED_TO_PAGE_EDGE = 'bleed_to_page_edge',
  BREAK_FRAME = 'break_frame',
}

export interface Point {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Transform2D {
  scale_x: number;
  scale_y: number;
  translate_x: number;
  translate_y: number;
  rotation_deg: number;
  anchor_x: number;
  anchor_y: number;
}

// --- Artifact and Asset Contracts ---

export enum AssetType {
  IMAGE_REFERENCE = 'image_reference',
  IMAGE_GENERATED = 'image_generated',
  CANVAS_SPEC = 'canvas_spec',
  PANEL_LAYER = 'panel_layer',
  TEXT_BLOCK = 'text_block',
  FONT_FILE = 'font_file',
  LETTERING_LAYER = 'lettering_layer',
  BUBBLE_LAYER = 'bubble_layer',
  EFFECT_LAYER = 'effect_layer',
  COMPOSITE_PAGE = 'composite_page',
  QA_REPORT = 'qa_report',
  EXPORT_PDF = 'export_pdf',
  EXPORT_PNG = 'export_png',
}

export enum LifecycleStatus {
  DRAFT = 'draft',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  ARCHIVED = 'archived',
  DELETED = 'deleted',
}

export interface StorageRef {
  backend: string;
  relative_path: string;
  uri?: string | null;
}

export interface ArtifactManifest {
  artifact_id: string;
  asset_type: AssetType;
  version: number;
  mime_type: string;
  file_path: string;
  content_sha256: string;
  byte_size: number;
  dimensions?: Size | null;
  dpi?: number | null;
  created_at: string;
  run_id: string;
  parent_artifact_ids: string[];
  metadata: Record<string, unknown>;
  lifecycle_status: LifecycleStatus;
}

// --- Engine Execution Contracts ---

export enum EngineId {
  E1_IMAGE_GENERATION = 'e1_image_generation',
  E2_CANVAS_GENERATION = 'e2_canvas_generation',
  E3_IMAGE_CANVAS_INTEGRATION = 'e3_image_canvas_integration',
  E4_TEXT_GENERATION = 'e4_text_generation',
  E5_TYPOGRAPHY_FONT = 'e5_typography_font',
  E6_SPEECH_BUBBLE = 'e6_speech_bubble',
  E7_EFFECTS_MOTION = 'e7_effects_motion',
  S6_COMPOSITOR = 's6_compositor',
  S7_QUALITY_VERIFICATION = 's7_quality_verification',
  S8_EXPORT_DELIVERY = 's8_export_delivery',
  S9_AGENT_COORDINATOR = 's9_agent_coordinator',
}

export enum EngineStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  SUCCESS = 'success',
  FAILED = 'failed',
  BLOCKED = 'blocked',
  CANCELLED = 'cancelled',
  NOT_IMPLEMENTED = 'not_implemented',
  NOT_IMPLEMENTED_YET = 'not_implemented_yet',
  EXPERIMENTAL = 'experimental',
  NEEDS_REVIEW = 'needs_review',
}

export enum QualityVerdict {
  PENDING = 'pending',
  PASSED = 'passed',
  FAILED = 'failed',
  UNSURE = 'unsure',
  NEEDS_REVIEW = 'needs_review',
  BLOCKED = 'blocked',
}

export interface UsageMetrics {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  image_ops: number;
  compute_seconds: number;
  estimated_cost_usd: number;
  provider_reported_cost_usd?: number | null;
}

export interface ProvenanceRecord {
  engine_id: EngineId;
  engine_version: string;
  schema_version: string;
  config_hash: string;
  input_artifact_ids: string[];
  story_bible_version?: string | null;
  taxonomy_rule_ids: string[];
  created_at: string;
}

export interface EngineRunRequest<TParams = unknown> {
  run_id: string;
  attempt_id: string;
  engine_id: EngineId;
  engine_version: string;
  schema_version: string;
  project_id: string;
  scope_id?: string | null;
  input_artifact_ids: string[];
  parameters: TParams;
  config_hash: string;
  budget_limit_usd?: number | null;
  dry_run?: boolean;
}

export interface EngineRunResponse<TOutput = unknown> {
  run_id: string;
  attempt_id: string;
  engine_id: EngineId;
  engine_version: string;
  schema_version: string;
  status: EngineStatus;
  quality_verdict?: QualityVerdict | null;
  created_at: string;
  completed_at: string;
  latency_seconds: number;
  output_artifact_ids: string[];
  output?: TOutput | null;
  usage: UsageMetrics;
  provenance: ProvenanceRecord;
  validation_errors: ValidationErrorDetail[];
  error?: EngineFailure | null;
  retryable: boolean;
}

// --- Agent & Coordinator Contracts (ADR / Specification Phase) ---

export enum AgentPlanStatus {
  DRAFT = 'DRAFT',
  PLANNED = 'PLANNED',
  VALIDATING = 'VALIDATING',
  AWAITING_APPROVAL = 'AWAITING_APPROVAL',
  READY = 'READY',
  RUNNING = 'RUNNING',
  VERIFYING = 'VERIFYING',
  COMPLETED = 'COMPLETED',
  REJECTED = 'REJECTED',
  BLOCKED = 'BLOCKED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
  INTERRUPTED = 'INTERRUPTED',
  NEEDS_HUMAN = 'NEEDS_HUMAN',
  NEEDS_REPAIR = 'NEEDS_REPAIR',
}

export enum AgentCapabilityStatus {
  AVAILABLE = 'AVAILABLE',
  EXPERIMENTAL = 'EXPERIMENTAL',
  BLOCKED = 'BLOCKED',
  NOT_IMPLEMENTED = 'NOT_IMPLEMENTED',
}

export interface AgentStep {
  step_id: string;
  title: string;
  engine_id: EngineId | string;
  tool_name: string;
  dependencies: string[];
  required_inputs: Record<string, unknown>;
  expected_outputs: string[];
  requires_approval: boolean;
  estimated_cost_usd?: number | null;
  status: EngineStatus;
}

export interface AgentPlan {
  plan_id: string;
  plan_version: number;
  plan_hash: string;
  project_id: string;
  goal: string;
  acceptance_criteria: string[];
  status: AgentPlanStatus;
  steps: AgentStep[];
  canon_version: number;
  canon_hash: string;
  created_at: string;
  budget_limit_usd?: number | null;
}

export interface ApprovalRequest {
  approval_id: string;
  plan_id: string;
  step_id: string;
  operation: string;
  scope: string;
  affected_resources: string[];
  reversibility: 'REVERSIBLE' | 'IRREVERSIBLE';
  consequence: string;
  cost_exposure_usd?: number | null;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'INVALIDATED';
}
