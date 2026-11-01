/**
 * InkLoop AI Creative Director & Universe Builder TypeScript Interfaces.
 */

export type CreativeMode =
  | 'quick_concept'
  | 'full_production_bible'
  | 'character_deep_dive'
  | 'ensemble_builder'
  | 'visual_worldbuilding';

export type FactCategory =
  | 'EXPLICIT_USER_FACT'
  | 'AGENT_PROPOSAL'
  | 'OPEN_QUESTION';

export interface FactItem {
  fact_id: string;
  category: FactCategory;
  field: string;
  content: string;
  provenance: string;
  needs_review: boolean;
}

export interface BriefVisualReference {
  asset_id: string;
  url?: string;
  role: string;
  notes?: string;
  assigned_character_id?: string;
}

export interface CreativeBrief {
  brief_id: string;
  project_id: string;
  mode: CreativeMode;
  user_prompt: string;
  title?: string;
  format: string;
  genre: string;
  tone: string;
  target_audience: string;
  premise: string;
  central_dramatic_question: string;
  intended_emotional_experience: string;
  themes: string[];
  motifs: string[];
  protagonist_concept: string;
  desired_cast_size?: number;
  setting_world_premise: string;
  visual_references: BriefVisualReference[];
  scope: string;
  constraints_must_have: string[];
  constraints_must_not_have: string[];
  boundaries_and_preferences: string[];
  explicit_facts: FactItem[];
  agent_proposals: FactItem[];
  unknowns: string[];
  created_at: string;
  explicit_user_facts?: FactItem[];
  open_questions_and_unknowns?: string[];
  primary_genre?: string;
  target_medium?: string;
}

export interface CreativeStoryBible {
  project_id: string;
  title: string;
  logline: string;
  premise: string;
  synopsis_short: string;
  synopsis_expanded: string;
  genre: string;
  tone: string;
  format: string;
  themes: string[];
  subthemes: string[];
  motifs: string[];
  central_dramatic_question: string;
  stakes: string;
  conflict_engine: string;
  narrative_promise: string;
  point_of_view: string;
  narrative_voice: string;
  pacing_and_rhythm: string;
  story_boundaries: string[];
  content_constraints: string[];
  core_world_premise: string;
  world_rules_summary: string[];
  unresolved_questions: string[];
  assumptions: string[];
  canon_version: number;
  approved_facts: string[];
  proposed_facts: string[];
  theme?: string;
}

export interface CharacterArcCheckpoint {
  chapter_or_episode: number;
  internal_state: string;
  belief_about_world: string;
  relational_status: string;
}

export interface OutfitVariant {
  outfit_id: string;
  name: string;
  narrative_context: string;
  garments: string[];
  color_palette: string[];
  distinguishing_props: string[];
}

export interface CharacterIdentityProfile {
  character_id: string;
  name: string;
  role: string;
  narrative_function: string;
  age_range: string;
  external_goal: string;
  internal_need: string;
  core_fear: string;
  wound_or_ghost: string;
  flaws: string[];
  moral_line_they_wont_cross: string;
  visual_invariants: string[];
  distinguishing_silhouette_elements: string[];
  base_outfit: OutfitVariant;
  outfit_variants: OutfitVariant[];
  forbidden_visual_drift: string[];
  voice_traits: string[];
  dialogue_rhythm: string;
  arc_checkpoints: CharacterArcCheckpoint[];
  relationships_summary: Record<string, string>;
  backstory: string;
  approval_status: 'draft' | 'needs_review' | 'approved' | 'rejected';
}

export interface RelationshipEdge {
  source_character_id: string;
  target_character_id: string;
  relationship_type: string;
  core_dynamic: string;
  point_of_tension: string;
  secret_or_unspoken_truth: string;
  status: 'allies' | 'rivals' | 'mentor_student' | 'distrustful' | 'estranged' | 'enemies';
}

export interface RelationshipGraph {
  project_id: string;
  characters: string[];
  edges: RelationshipEdge[];
  ensemble_differentiators: string[];
  nodes?: string[];
}

export interface MagicOrTechAbilityRule {
  name: string;
  ability_id?: string;
  practitioners: string[];
  mechanism: string;
  description: string;
  trigger_condition: string;
  sensory_manifestation: string;
  cost_or_strain: string;
  failure_mode_or_risk: string;
  absolute_limit: string;
  narrative_consequence: string;
}

export interface LocationSpec {
  location_id: string;
  name: string;
  atmosphere: string;
  spatial_layout: string;
  visual_anchors: string[];
  lighting_conditions: string;
  narrative_use: string;
  continuity_rules: string[];
  aliases?: string[];
  location_type?: string;
  geographic_context?: string;
  scale?: string;
  parent_location_id?: string | null;
  zones?: string[];
  environment_details?: Record<string, string>;
  state_variants?: LocationStateVariant[];
  source_location_id?: string | null;
  version?: number;
  version_history?: Record<string, any>[];
}

export interface ObjectStudioProfile {
  prop_id: string;
  version: number;
  name: string;
  description: string;
  required_attributes: string[];
  reference_assets: Array<{
    asset_id: string;
    path: string;
    asset_type: string;
    expected_hash: string;
    mime_type?: string;
    file_size_bytes?: number | null;
    provenance?: Record<string, unknown> | null;
  }>;
  form_and_proportions: string;
  materials: string[];
  palette: string[];
  components: string[];
  distinctive_marks: string[];
  stable_invariants: string[];
  allowed_states: string[];
  uncertain_traits: string[];
  identity_features: Array<{
    feature_id: string;
    label: string;
    description: string;
    stability: 'stable' | 'state' | 'unknown';
    provenance: 'user_authored' | 'model_observation' | 'model_inference' | 'unknown';
    evidence_asset_ids: string[];
  }>;
  trait_provenance: Record<string, 'user_authored' | 'model_observation' | 'model_inference' | 'unknown'>;
  analysis: {
    analysis_status: 'unknown' | 'completed' | 'partial' | 'not_run';
    analysis_source: string;
    model_id?: string | null;
    observed_summary: string;
    inferred_purpose: string;
    unknown_or_occluded: string[];
    creator_authored_facts: string[];
    analyzed_at?: string | null;
  };
  creator_notes: string;
  draft_origin: 'creator' | 'object_studio' | 'agent_story_plan' | 'unknown';
  draft_job_id?: string | null;
  approval_status: 'approved' | 'draft' | 'deprecated';
}

export interface LocationStateVariant {
  variant_id: string;
  name: string;
  time_of_day?: string | null;
  season?: string | null;
  weather?: string | null;
  lighting?: string | null;
  visible_changes: string[];
  scene_condition?: string | null;
}

export interface PropArtifactSpec {
  prop_id: string;
  name: string;
  description: string;
  current_owner?: string;
  historical_origin: string;
  narrative_function: string;
  state_and_damage: string;
  visual_invariants: string[];
}

export interface WorldBible {
  project_id: string;
  world_name: string;
  core_laws_and_physics: string[];
  geography_and_climate: string;
  culture_and_society: string;
  institutions_and_factions: string[];
  supernatural_or_tech_rules: MagicOrTechAbilityRule[];
  locations: Record<string, LocationSpec>;
  props: Record<string, PropArtifactSpec>;
  continuity_timeline_rules: string[];
  version: number;
  magic_or_tech_rules?: MagicOrTechAbilityRule[];
}

export interface SceneCandidate {
  scene_id: string;
  title: string;
  narrative_purpose: string;
  participating_character_ids: string[];
  location_id: string;
  key_action_or_revelation: string;
  emotional_beat: string;
  estimated_panel_count: number;
}

export interface ChapterOutline {
  chapter_number: number;
  title: string;
  purpose_in_arc: string;
  turning_point: string;
  emotional_shift: string;
  ending_hook_or_cliffhanger: string;
  scene_candidates: SceneCandidate[];
  emotional_turning_point?: string;
}

export interface SetupPayoffItem {
  setup_id: string;
  setup_event: string;
  setup_chapter: number;
  payoff_event: string;
  payoff_chapter: number;
  status: 'planned' | 'unresolved' | 'paid_off';
}

export interface NarrativeStructure {
  project_id: string;
  central_conflict: string;
  opposition_engine: string;
  macro_arc_beats: Record<string, string>;
  chapters: ChapterOutline[];
  setup_payoff_ledger: SetupPayoffItem[];
  unresolved_threads: string[];
  chapter_outlines?: ChapterOutline[];
  act_breakdown?: Array<{ act: number; name: string; beat: string }>;
}

export interface VisualStyleProfile {
  style_id: string;
  name: string;
  target_format: string;
  medium: string;
  shape_language: string;
  line_art_rules: string[];
  tonal_value_rules: string[];
  palette_and_accent_rules: string[];
  lighting_rules: string[];
  background_detail_density: string;
  camera_shot_habits: string[];
  negative_constraints: string[];
  approval_status: 'draft' | 'needs_review' | 'approved' | 'superseded';
}

export interface SheetViewSpec {
  view_id: string;
  view_type: string;
  pose_description: string;
  required_features_visible: string[];
  camera_angle: string;
}

export interface CharacterSheetPlan {
  plan_id: string;
  character_id: string;
  character_name: string;
  views: SheetViewSpec[];
  required_views?: SheetViewSpec[];
  turnaround_requirements: string[];
  facial_expression_anchors: string[];
  color_callout_labels: string[];
}

export interface ProjectCanonContract {
  contract_id: string;
  project_id: string;
  version: number;
  canon_hash: string;
  status: 'draft' | 'needs_review' | 'approved' | 'superseded';
  approved_facts: string[];
  proposed_facts: string[];
  content_boundaries: string[];
  provenance: Record<string, string>;
  updated_at: string;
}

export interface CharacterIdentityContract {
  contract_id: string;
  character_id: string;
  version: number;
  status: 'draft' | 'needs_review' | 'approved' | 'superseded';
  mandatory_visual_invariants: string[];
  allowed_variations: string[];
  forbidden_drift: string[];
  reference_asset_roles: Record<string, string>;
  verifier_tolerances: Record<string, any>;
  updated_at: string;
  mandatory_invariants?: string[];
  forbidden_visual_drift?: string[];
  character_name?: string;
}

export interface VisualStyleContract {
  contract_id: string;
  style_id: string;
  version: number;
  status: 'draft' | 'needs_review' | 'approved' | 'superseded';
  style_dimensions: Record<string, any>;
  negative_constraints: string[];
  reference_asset_roles: Record<string, string>;
  updated_at: string;
  target_medium?: string;
  medium?: string;
  rendering_invariants?: string[];
  negative_prompt_additions?: string[];
}

export interface WorldRuleContract {
  contract_id: string;
  project_id: string;
  version: number;
  supernatural_limits: Record<string, Record<string, string>>;
  continuity_consequences: string[];
  updated_at: string;
}

export interface GenerationConstraintContract {
  contract_id: string;
  project_id: string;
  target_character_ids: string[];
  required_tokens: string[];
  negative_tokens: string[];
  reference_asset_ids: string[];
  quality_gates: string[];
  updated_at: string;
}

export interface CreativeContractsPackage {
  project_id: string;
  canon_contract: ProjectCanonContract;
  character_contracts: Record<string, CharacterIdentityContract>;
  style_contract: VisualStyleContract;
  world_contract: WorldRuleContract;
  generation_constraints: GenerationConstraintContract;
  created_at: string;
  canon?: ProjectCanonContract;
  characters?: Record<string, CharacterIdentityContract>;
  style?: VisualStyleContract;
  world?: WorldRuleContract;
}

export type FindingSeverity = 'ERROR' | 'WARNING' | 'SUGGESTION';

export type FindingCategory =
  | 'CHARACTER'
  | 'STORY'
  | 'VISUAL'
  | 'WORLD'
  | 'CONTRACT'
  | 'CANON_CONFLICT';

export interface CoherenceFinding {
  finding_id: string;
  severity: FindingSeverity;
  category: FindingCategory;
  message: string;
  affected_artefact: string;
  evidence: string;
  suggested_correction: string;
  entity_id?: string;
  title?: string;
}

export interface ValidationResult {
  project_id: string;
  is_coherent: boolean;
  findings: CoherenceFinding[];
  timestamp: string;
}

export interface CreativePackage {
  project_id: string;
  version: number;
  package_hash?: string;
  brief: CreativeBrief;
  story_bible: CreativeStoryBible;
  characters: Record<string, CharacterIdentityProfile>;
  relationship_graph: RelationshipGraph;
  world_bible: WorldBible;
  narrative_structure: NarrativeStructure;
  style_profile: VisualStyleProfile;
  character_sheet_plans: Record<string, CharacterSheetPlan>;
  contracts: CreativeContractsPackage;
  validation: ValidationResult;
  completed_stages: string[];
  current_stage: string;
  synthesis_source?: 'live_ai' | 'dynamic_procedural';
  has_pending_approval: boolean;
  pending_proposal_diff?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

// =============================================================================
// Style Copier & Character Copier Interactive Profile Types
// =============================================================================

export type SemanticReferenceRole =
  | 'style_reference'
  | 'character_reference'
  | 'composition_reference'
  | 'target_to_edit'
  | 'pose_reference'
  | 'background_reference';

export type CharacterViewRole =
  | 'front'
  | 'side'
  | 'three_quarter'
  | 'full_body'
  | 'full_form'
  | 'close_up'
  | 'expression'
  | 'outfit'
  | 'action_pose'
  | 'other';

export type ProfileStatus =
  | 'draft'
  | 'analyzing'
  | 'ready'
  | 'needs_review'
  | 'approved'
  | 'archived';

export interface ReferenceBinding {
  asset_id: string;
  role: SemanticReferenceRole;
  view_role?: CharacterViewRole | null;
  character_id?: string | null;
  weight: number;
  notes?: string | null;
  source_origin?: string | null;
  license_notes?: string | null;
}

export interface StyleDimensionTrait {
  dimension: string;
  summary: string;
  rules: string[];
  confidence: number;
  is_user_confirmed: boolean;
  evidence_asset_ids: string[];
  uncertainty_notes?: string | null;
}

export interface StyleAnalysisRecord {
  medium: string;
  traits: Record<string, StyleDimensionTrait>;
  measured_palette?: string[] | null;
  screentones_and_fx: string[];
  negative_constraints: string[];
  analysis_summary: string;
  analyzed_at: string;
}

export interface StyleControlVariable {
  value: string;
  pinned: boolean;
  source: 'model_observation' | 'user_authored';
}

export interface QuickStyleTemplateDto {
  template_id: string;
  version: string;
  name: string;
  description: string;
  style_prompt_core: string;
  variables: Record<string, string>;
  negative_constraints: string[];
  sample_prompt: string;
  preview_asset_id?: string | null;
    preview_url?: string | null;
  preview_provider?: string | null;
  preview_prompt?: string | null;
}

export interface StyleProfile {
  profile_id: string;
  project_id: string;
  name: string;
  version: number;
  created_at?: string;
  updated_at?: string;
  status: ProfileStatus;
  references: ReferenceBinding[];
  analysis?: StyleAnalysisRecord | null;
  style_prompt_core: string;
  negative_constraints: string[];
  control_weights?: Record<string, number>;
  style_variables?: Record<string, StyleControlVariable>;
  approved_by_user?: boolean;
  approved_at?: string | null;
  version_history?: any[];
  metadata?: Record<string, any>;
}

export interface CharacterCopierProfile {
  profile_id: string;
  project_id: string;
  character_id: string;
  name: string;
  entity_kind?: string;
  morphology?: string;
  surface_description?: string;
  appendages_or_parts?: string[];
  sensory_features?: string[];
  locomotion?: string;
  face_check_applicable?: boolean;
  identity_features?: Array<{ feature_id: string; label: string; description: string; stability: 'stable' | 'state' | 'unknown'; provenance: string; evidence_asset_ids: string[] }>;
  version: number;
  created_at?: string;
  updated_at?: string;
  status: ProfileStatus;
  references: ReferenceBinding[];
  identity_invariants: string[];
  allowed_variations: string[];
  contextual_traits?: string[];
  uncertain_traits?: string[];
  forbidden_drift: string[];
  prompt_identity_core: string;
  reference_selection_strategy?: string;
  evidence_links?: Record<string, string[]>;
  base_outfit?: any;
  outfit_variants?: any[];
  approved_by_user?: boolean;
  approved_at?: string | null;
  canon_version?: number | null;
  version_history?: any[];
  metadata?: Record<string, any>;
}

export interface ProviderCapabilities {
  provider_name: string;
  multi_image_reference: boolean;
  max_reference_images: number;
  reference_conditioning_mode: string;
  supports_reference_roles: boolean;
  supported_roles: string[];
  identity_lock_guarantee: boolean;
  notes: string;
}

export interface CreativeGenerationResult {
  run_id?: string;
  project_id?: string;
  output_asset_id: string;
  asset_id?: string;
  initial_asset_id?: string | null;
  file_path?: string;
  preview_url?: string;
  panel_id?: string;
  scene_id?: string;
  success?: boolean;
  status?: string;
  attempts_performed?: number;
  prompt?: string;
  positive_prompt?: string;
  negative_prompt?: string;
  style_profile_id?: string | null;
  style_version?: number | null;
  character_profiles_used?: any[];
  cost_usd?: number | null;
  is_simulated?: boolean;
  created_at?: string;
  used_references?: Array<{
    asset_id: string;
    role: string;
    character_id?: string | null;
    view_role?: string | null;
  }>;
  qa_result: {
    passed?: boolean;
    overall_passed?: boolean;
    status?: string;
    overall_score?: number | null;
    score_explanation?: string;
    style_score?: number | null;
    identity_score?: number | null;
    variation_score?: number | null;
    leakage_detected?: boolean | null;
    checked_dimensions?: string[];
    not_checked_dimensions?: string[];
    style_fidelity_score?: number;
    character_fidelity_score?: number;
    dynamic_variation_score?: number;
    findings: Array<{
      finding_id?: string;
      rule_name?: string;
      category?: string;
      severity?: string;
      message: string;
      affected_dimension?: string;
      evidence?: any;
      suggested_repair?: string | null;
      repair_suggestion?: string | null;
    }>;
    targeted_repair_prompt?: string | null;
    repaired?: boolean;
    repair_count?: number;
  };
  lineage_metadata?: Record<string, any>;
}

