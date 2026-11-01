/**
 * InkLoop S9 Agent Runtime TypeScript Contracts.
 * Strictly aligned with backend/app/agent/schemas.py and backend/app/api/routers/agent.py.
 */

export type CapabilityStatus = 'AVAILABLE' | 'EXPERIMENTAL' | 'BLOCKED' | 'NOT_IMPLEMENTED';

export type ToolResultStatus = 'success' | 'failed' | 'gated' | 'blocked';

export interface AgentAttachmentDto {
  attachment_id: string;
  filename: string;
  mime_type: string;
  byte_size: number;
  content_sha256: string;
  width?: number;
  height?: number;
  asset_id?: string;
  is_canonical_anchor?: boolean;
  created_at?: string;
}

export interface AgentToolCallDto {
  call_id: string;
  tool_id: string;
  arguments: Record<string, unknown>;
}

export interface AgentToolResultDto {
  call_id: string;
  tool_id: string;
  status: ToolResultStatus | string;
  output?: Record<string, unknown> | string;
  error?: string;
  error_code?: string;
  duration_seconds: number;
  artifacts?: Record<string, unknown>[];
  cost_usd?: number;
  requires_approval?: boolean;
  approval_id?: string;
}

export interface AgentStepDto {
  step_id: string;
  title: string;
  engine_id: string;
  tool_name: string;
  dependencies: string[];
  required_inputs: Record<string, unknown>;
  expected_outputs: string[];
  requires_approval: boolean;
  estimated_cost_usd?: number;
  status: string;
}

export interface AgentPlanDto {
  plan_id: string;
  plan_version: number;
  plan_hash: string;
  project_id: string;
  goal: string;
  acceptance_criteria: string[];
  status: string;
  steps: AgentStepDto[];
  canon_version: number;
  canon_hash?: string;
  created_at: string;
  budget_limit_usd?: number;
  project_available_budget_usd: number;
  requested_run_budget_cap_usd?: number;
  effective_run_budget_cap_usd: number;
  is_cost_unknown: boolean;
  dispatched: boolean;
  dispatch_blocked_reason?: string;
}

export interface ApprovalRequestDto {
  approval_id: string;
  plan_id?: string;
  step_id?: string;
  operation: string;
  scope: string;
  affected_resources: string[];
  reversibility: 'REVERSIBLE' | 'IRREVERSIBLE' | string;
  consequence: string;
  cost_exposure_usd?: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'INVALIDATED' | string;
  canon_hash_at_request?: string;
  arguments_hash: string;
  created_at: string;
  decided_at?: string;
  decision?: string;
  decision_rationale?: string;
}

export interface PendingStoryActionDto {
  schema_version: string;
  action_type: string;
  source_message_id: string;
  source_story_hash: string;
  source_title: string;
  status: 'planning' | 'offer_made' | 'plan_ready' | 'running' | 'needs_attention' | 'completed' | 'skipped' | string;
  panel_count: number;
  page_count?: number | null;
  total_panel_count?: number | null;
  page_panel_counts?: Record<string, number>;
  estimated_cost_usd?: number | null;
  assumptions?: string[];
  plan?: StoryPlanDto;
  plan_call_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface StoryPlanPageDto {
  page_number: number;
  summary: string;
  panel_ids: string[];
  panel_count: number;
  beats: Array<{
    panel_id: string;
    story_event: string;
    visual_focus: string;
    character_ids: string[];
    characterless: boolean;
    text?: {
      content_kind?: string;
      carrier?: string;
      text_content?: string | null;
      speaker_id?: string | null;
      speaker_name?: string | null;
    };
  }>;
}

export interface StoryBlueprintDto {
  page_count: number;
  title: string;
  premise: string;
  audience_tone?: string | null;
  world_rules: string[];
  story_arc: string;
  assumptions: string[];
  pages: StoryPlanPageDto[];
  selected_character_ids: string[];
  story_cast_is_canon: false;
}

export interface StoryPlanDto {
  page_count?: number;
  total_panel_count?: number;
  page_panel_counts?: Record<string, number>;
  assumptions?: string[];
  story_blueprint?: StoryBlueprintDto;
  story_local_cast?: Array<{ speaker_id: string; name: string; kind_and_form?: string | null; visual_description: string; personality?: string | null }>;
  plans?: Array<Record<string, unknown>>;
}

export interface AgentMessageDto {
  message_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  text: string;
  timestamp: string;
  attachments?: AgentAttachmentDto[];
  request_context?: Record<string, unknown>;
  tool_calls?: AgentToolCallDto[];
  tool_results?: AgentToolResultDto[];
  activity_state?: string;
  activity_label?: string;
  plan?: AgentPlanDto;
  pending_approval?: ApprovalRequestDto;
  project_available_budget_usd?: number;
  model_usage?: {
    status: 'reported' | 'partial' | 'unavailable';
    model_calls: number;
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  };
  production_job?: StoryProductionJobDto;
  pending_story_action?: PendingStoryActionDto;
}

export interface StoryProductionJobDto {
  schema_version: string;
  job_id: string;
  run_id: string;
  project_id: string;
  goal?: string;
  target_page_count?: number | null;
  page_panel_counts?: Record<string, number>;
  stage?: string;
  source_request_message_id?: string;
  status: 'preflight' | 'generating' | 'assembling' | 'verifying' | 'needs_attention' | 'completed' | 'failed' | string;
  updated_at: string;
  export_artifact_id?: string | null;
  export_download_url?: string | null;
  export_file_path?: string | null;
  pages: Array<{
    page_number: number;
    page_id: string;
    panel_ids: string[];
    revision?: number | null;
    status: 'pending' | 'created' | 'assembled' | 'needs_attention' | 'failed' | string;
    composite_artifact_id?: string | null;
    composite_image_url?: string | null;
    verification?: { passed?: boolean; visual_verification?: string; failures?: string[] };
  }>;
  panels: Record<string, {
    panel_id: string;
    page_number: number;
    status: string;
    asset_id?: string | null;
    generation_attempts: number;
    automatic_retries: number;
    manual_retries: number;
    error?: string | null;
  }>;
  errors: string[];
}

export interface AgentChatRequest {
  project_id: string;
  message: string;
  attachments?: AgentAttachmentDto[];
  session_id?: string;
  approval_id?: string;
  spend_limit_usd?: number;
  selected_character_ids?: string[];
  selected_style_profile_id?: string;
  selected_style_version?: number;
  selected_location_id?: string;
  selected_location_version?: number;
  activity_id?: string;
  canvas_page_id?: string;
  canvas_panel_id?: string;
  canvas_expected_revision?: number;
  model?: string;
}

export interface AgentLiveActivityDto {
  tools: Array<{
    call_id: string;
    tool_id: string;
    status: string;
    duration_seconds?: number;
    error?: string;
    approval_id?: string;
  }>;
  production_job?: StoryProductionJobDto | null;
  finished: boolean;
}

export interface AgentStatusResponse {
  status: string;
  phase: string;
  spec: string;
  runtime_ready: boolean;
  mode: 'live_configured' | 'offline_explicit' | 'provider_unavailable';
  model_credentials_configured: boolean;
  tools_registered: number;
  model_name?: string;
  image_model?: string;
  sam_model?: string;
  provider?: string;
}

export interface ToolDefinitionDto {
  tool_id: string;
  version: string;
  name: string;
  domain: string;
  owning_service: string;
  purpose: string;
  status: CapabilityStatus;
  status_reason?: string;
  parameters_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  side_effect: string;
  requires_approval: boolean;
  cost_semantics: string;
  estimated_cost_usd?: number;
  is_idempotent: boolean;
  timeout_seconds: number;
  is_callable: boolean;
}

export interface AgentSessionSummaryDto {
  session_id: string;
  project_id: string;
  title: string;
  message_count: number;
  updated_at: string;
}

export interface AgentSessionDto {
  session_id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: AgentMessageDto[];
  metadata?: Record<string, unknown>;
}
