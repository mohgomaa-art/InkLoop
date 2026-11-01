/**
 * InkLoop Centralized Typed API Client.
 * Connects the frontend to all backend REST endpoints without duplicate logic.
 */
import { ErrorCode } from '../types/contracts';
import {
  AgentAttachmentDto,
  AgentChatRequest,
  AgentLiveActivityDto,
  AgentMessageDto,
  AgentStatusResponse,
  ToolDefinitionDto,
  AgentPlanDto,
  AgentSessionSummaryDto,
  AgentSessionDto,
  ApprovalRequestDto,
} from '../types/agent';
import {
  CreativeMode,
  CreativePackage,
  ValidationResult,
  CreativeContractsPackage,
  StyleProfile,
  QuickStyleTemplateDto,
  CharacterCopierProfile,
  StyleAnalysisRecord,
  ProviderCapabilities,
  CreativeGenerationResult,
  ReferenceBinding,
  LocationSpec,
  ObjectStudioProfile,
} from '../types/creative';

const API_BASE = '/api/v1';
const MAX_STYLE_ANALYSIS_REFERENCES = 3;

export interface ApiErrorPayload {
  error_code?: ErrorCode | string;
  message: string;
  detail?: any;
  status: number;
}

export interface EditorLayerDto {
  layer_id: string; kind: 'panel' | 'image' | 'text' | 'line'; label: string; parent_id?: string | null;
  visible: boolean; locked: boolean; z_index: number; source_asset_id?: string | null;
  source_sha256?: string | null; panel_id?: string | null;
  transform?: { scale_x: number; scale_y: number; translate_x: number; translate_y: number; rotation_deg: number; anchor_x: number; anchor_y: number } | null;
  fit_mode: 'cover' | 'contain'; metadata: Record<string, unknown>;
}
export interface EditablePageDto {
  schema_version: string; page_id: string; project_id: string; revision: number;
  layout: any; layers: EditorLayerDto[]; source_artifact_ids: string[];
}
export interface PanelLayoutPresetDto {
  id: string; name: string; category: string; use_case: string; reading_rhythm: string;
  template_id: string; template_parameters: Record<string, unknown>; agent_guidance: string;
  pinterest_search_url: string; version: number;
}
export interface BubblePresetDto {
  id: string; name: string; category: string; use_case: string; shape: string; tail_type: string;
  accent: string; halftone_shadow: boolean; inverted_dark_mode: boolean; fill_color: string;
  stroke_color: string; text_color: string; stroke_width: number; stroke_dash: string;
  agent_guidance: string; pinterest_search_url: string; version: number;
}

export class ApiError extends Error {
  payload: ApiErrorPayload;
  constructor(payload: ApiErrorPayload) {
    super(payload.message || 'API request failed');
    this.name = 'ApiError';
    this.payload = payload;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  const isFormData =
    (typeof FormData !== 'undefined' && options.body instanceof FormData) ||
    (options.body && typeof (options.body as any).append === 'function');

  if (!headers.has('Content-Type') && !isFormData) {
    headers.set('Content-Type', 'application/json');
  }
  if (isFormData) {
    // Crucial: Let the browser generate multipart/form-data boundary automatically
    headers.delete('Content-Type');
  }

  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let payload: ApiErrorPayload;
    try {
      const json = await response.json();
      const detail = json.detail;
      const validationMessages = Array.isArray(detail)
        ? detail.map((issue: any) => {
            const location = Array.isArray(issue?.loc)
              ? issue.loc.filter((part: unknown) => part !== 'body').join('.')
              : '';
            return [location, issue?.msg].filter(Boolean).join(': ');
          }).filter(Boolean).join('; ')
        : undefined;
      payload = {
        error_code: json.detail?.error_code || json.error_code || ErrorCode.ENGINE_CRASH,
        message: json.detail?.message || json.message || validationMessages || response.statusText,
        detail: json.detail,
        status: response.status,
      };
    } catch {
      payload = {
        message: response.statusText || `Request failed with status ${response.status}`,
        status: response.status,
      };
    }
    throw new ApiError(payload);
  }

  // Handle empty responses
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const apiClient = {
  // --- Health & Diagnostics ---
  getHealth: () => request<{ status: string; service: string; version: string; timestamp: string }>('/health'),
  getDiagnostics: () => request<any>('/config/diagnostics'),

  // --- Projects & Story Bible ---
  listProjects: () => request<Array<{ project_id: string; title: string; bible_version: number; canon_hash: string; characters: string[]; path: string }>>('/projects'),
  createProject: (title: string) => request<{ project_id: string; title: string; bible_version: number; canon_hash: string; characters: string[] }>('/projects', { method: 'POST', body: JSON.stringify({ title }) }),
  renameProject: (projectId: string, title: string, expectedVersion: number) => request<any>(`/projects/${encodeURIComponent(projectId)}/details`, { method: 'PUT', body: JSON.stringify({ title, expected_version: expectedVersion }) }),
  archiveProject: (projectId: string) => request<{ project_id: string; archived: boolean; history_retained: boolean }>(`/projects/${encodeURIComponent(projectId)}`, { method: 'DELETE' }),
  getProjectBible: (projectId: string) => request<any>(`/projects/${projectId}/bible`),
  updateProjectBible: (projectId: string, payload: { bible: any; expected_canon_hash?: string; expected_version?: number }) =>
    request<any>(`/projects/${projectId}/bible`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  proposeMutation: (projectId: string, payload: { target_type: string; target_id: string; change_description: string; proposed_changes: any }) =>
    request<any>(`/projects/${projectId}/bible/propose-mutation`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  applyMutation: (projectId: string, payload: { proposal?: any; proposal_id?: string; caller_authorized?: boolean }) =>
    request<any>(`/projects/${projectId}/bible/apply-mutation`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listProposals: (projectId: string) =>
    request<any[]>(`/projects/${projectId}/bible/proposals`),
  rejectMutation: (projectId: string, payload: { proposal_id: string; reason?: string }) =>
    request<any>(`/projects/${projectId}/bible/reject-mutation`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // --- Narrative Timeline ---
  getTimeline: (projectId: string) => request<any[]>(`/projects/${projectId}/timeline`),
  appendStateEvent: (projectId: string, payload: { event_id: string; panel_id: string; target_entity: string; state_delta: any; description: string; timestamp?: string }) =>
    request<any>(`/projects/${projectId}/timeline/event`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  resolvePanelState: (projectId: string, panelId: string) =>
    request<{ panel_id: string; resolved_state: any; deterministic: boolean }>(`/projects/${projectId}/timeline/resolve/${panelId}`),

  // --- Generation & Orchestration ---
  compileContext: (payload: { project_id: string; story_id: string; panel_id: string; scene: any }) =>
    request<any>('/generation/compile-context', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  startBatch: (payload: {
    batch_id?: string;
    project_id: string;
    story_id: string;
    scenes: any[];
    model?: string;
    max_retries_per_panel?: number;
    spend_cap_usd?: number;
    is_simulated?: boolean;
    require_verification?: boolean;
  }) =>
    request<any>('/generation/batches', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listBatches: () => request<any[]>('/generation/batches'),
  getBatch: (batchId: string) => request<any>(`/generation/batches/${batchId}`),
  resumeBatch: (batchId: string) =>
    request<any>(`/generation/batches/${batchId}/resume`, {
      method: 'POST',
    }),

  // --- Visual Verification ---
  getVerificationRules: () => request<any>('/verification/rules'),
  verifyAsset: (payload: { file_path?: string; asset_id?: string; project_id?: string; character_id?: string; mode?: 'live' | 'simulated' }) =>
    request<any>('/verification/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // --- Asset Registry & Lineage ---
  listAssets: (params?: { project_id?: string; asset_type?: string; lifecycle_status?: string }) => {
    const query = new URLSearchParams();
    const pid = params?.project_id ?? (typeof localStorage !== 'undefined' ? localStorage.getItem('inkloop_current_project') : null) ?? undefined;
    if (pid) query.set('project_id', pid);
    if (params?.asset_type) query.set('asset_type', params.asset_type);
    if (params?.lifecycle_status) query.set('lifecycle_status', params.lifecycle_status);
    const qs = query.toString();
    return request<any[]>(`/assets${qs ? `?${qs}` : ''}`);
  },
  uploadFont: async (projectId: string, file: File): Promise<any> => {
    const form = new FormData();
    form.set('project_id', projectId);
    form.set('file', file);
    return request<any>('/assets/fonts', { method: 'POST', body: form });
  },
  uploadImageAsset: async (file: File, projectId = 'inkloop', assetType = 'image_reference', name?: string): Promise<any> => {
    const form = new FormData();
    form.append('file', file);
    form.append('project_id', projectId);
    form.append('asset_type', assetType);
    if (name) form.append('name', name);
    return request<any>('/assets/upload', { method: 'POST', body: form });
  },
  getAsset: (assetId: string) => request<any>(`/assets/${assetId}`),
  getAssetLineage: (assetId: string) => request<any>(`/assets/${assetId}/lineage`),
  verifyAssetIntegrity: (assetId: string) =>
    request<{ asset_id: string; integrity_verified: boolean; content_sha256: string }>(`/assets/${assetId}/verify-integrity`, {
      method: 'POST',
    }),
  exportManifest: (projectId = 'inkloop') => request<any>(`/assets/manifest/export?project_id=${projectId}`),
  getAssetFileUrl: (assetId: string) => {
    if (!assetId) return '';
    if (assetId.startsWith('http://') || assetId.startsWith('https://') || assetId.startsWith('data:') || assetId.startsWith('blob:')) {
      return assetId;
    }
    if (assetId.startsWith('/api/v1/assets/') && assetId.endsWith('/file')) {
      return assetId;
    }
    if (assetId.startsWith('/api/')) {
      return assetId;
    }
    const cleanId = assetId.replace(/^\/api\/v1\/assets\//, '').replace(/\/file$/, '');
    return `${API_BASE}/assets/${cleanId}/file`;
  },
  getAgentAttachmentFileUrl: (attachmentId: string, projectId: string) =>
    `${API_BASE}/agent/attachments/${encodeURIComponent(attachmentId)}/file?project_id=${encodeURIComponent(projectId)}`,

  // --- Manual page editor ---
  generateEditableLayout: (payload: any) => request<any>('/canvas/layout', { method: 'POST', body: JSON.stringify(payload) }),
  listPanelLayoutPresets: (query = '', limit = 100) => request<{ presets: PanelLayoutPresetDto[]; count: number; total: number }>(
    `/canvas/panel-layout-presets?query=${encodeURIComponent(query)}&limit=${limit}`,
  ),
  listBubblePresets: (query = '', limit = 50) => request<{ presets: BubblePresetDto[]; count: number; total: number }>(
    `/canvas/bubble-presets?query=${encodeURIComponent(query)}&limit=${limit}`,
  ),
  createEditablePage: (payload: { project_id: string; layout: any; source_artifact_ids?: string[] }) =>
    request<EditablePageDto>('/editor/pages', { method: 'POST', body: JSON.stringify(payload) }),
  listEditablePages: (projectId?: string) => request<any[]>(`/editor/pages${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`),
  listDeletedEditablePages: (projectId?: string) => request<any[]>(`/editor/pages/deleted${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`),
  deleteEditablePage: (pageId: string) => request<{ page_id: string; deleted: boolean; revisions_retained: boolean }>(`/editor/pages/${encodeURIComponent(pageId)}`, { method: 'DELETE' }),
  restoreDeletedEditablePage: (pageId: string) => request<{ page_id: string; deleted: boolean }>(`/editor/pages/${encodeURIComponent(pageId)}/restore-deleted`, { method: 'POST' }),
  getEditablePage: (pageId: string) => request<EditablePageDto>(`/editor/pages/${encodeURIComponent(pageId)}`),
  saveEditablePage: (pageId: string, expectedRevision: number, document: EditablePageDto) =>
    request<EditablePageDto>(`/editor/pages/${encodeURIComponent(pageId)}`, { method: 'PUT', body: JSON.stringify({ expected_revision: expectedRevision, document }) }),
  getEditablePageRevisions: (pageId: string) => request<any[]>(`/editor/pages/${encodeURIComponent(pageId)}/revisions`),
  restoreEditablePage: (pageId: string, expectedRevision: number, revisionToRestore: number) =>
    request<EditablePageDto>(`/editor/pages/${encodeURIComponent(pageId)}/restore`, { method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision, revision_to_restore: revisionToRestore }) }),
  validateEditablePage: (document: EditablePageDto) => request<{ valid: boolean; diagnostics: any[] }>('/editor/pages/validate', { method: 'POST', body: JSON.stringify(document) }),
  generateInPanelArt: (pageId: string, panelId: string, payload: {
    prompt: string;
    character_ids?: string[];
    location_id?: string;
    style_profile_id?: string;
    style_profile_version?: number;
    camera_angle?: string;
    fit_mode?: 'cover' | 'contain';
    is_simulated?: boolean;
  }) => request<{
    success: boolean;
    page_id: string;
    panel_id: string;
    new_revision: number;
    asset_id: string;
    image_url: string;
    generation_provenance: {
      character_ids: string[];
      character_reference_asset_ids: string[];
      style_profile_id?: string | null;
      style_profile_version?: number | null;
      style_reference_asset_ids: string[];
      reference_image_roles: Array<{ asset_id?: string | null; role: string; character_id?: string | null }>;
      visual_verification_status: string;
      context_fingerprint?: string | null;
    };
    updated_page: EditablePageDto;
  }>(`/editor/pages/${encodeURIComponent(pageId)}/panels/${encodeURIComponent(panelId)}/generate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  quickStartProject: (payload: {
    title: string;
    genre: 'shonen' | 'seinen' | 'webtoon' | 'scifi' | 'comedy';
    premise: string;
    reading_direction?: 'rtl' | 'ltr';
    language?: 'ar' | 'en';
  }) => request<{
    success: boolean;
    project_id: string;
    bible_id: string;
    page_1_id: string;
    title: string;
    genre: string;
    summary: string;
    reading_direction: string;
    language: string;
    canon_hash: string;
    layout_template: string;
    starter_characters: any[];
  }>('/projects/quick_start', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  renderEditableImageLayer: async (pageId: string, layerId: string, transform: NonNullable<EditorLayerDto['transform']>, layout: any): Promise<string> => {
    const response = await fetch(`${API_BASE}/editor/pages/${encodeURIComponent(pageId)}/layers/${encodeURIComponent(layerId)}/preview`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ transform, layout }),
    });
    if (!response.ok) {
      let message = `E3 render failed (${response.status})`;
      try { const payload = await response.json(); message = payload.detail?.message || payload.message || message; } catch { /* Keep status-based detail. */ }
      throw new Error(message);
    }
    return URL.createObjectURL(await response.blob());
  },

  compositeEditablePage: (pageId: string) => request<{
    success: boolean;
    page_id: string;
    revision: number;
    composite_artifact_id: string;
    image_url: string;
    output_file_path: string;
    dimensions: { width: number; height: number };
    dpi: number;
    layer_count: number;
    sha256: string;
  }>(`/editor/pages/${encodeURIComponent(pageId)}/composite`, { method: 'POST' }),

  exportEditablePage: (pageId: string, options?: { target_format?: 'pdf' | 'png'; reading_direction?: 'rtl' | 'ltr' }) => request<{
    success: boolean;
    page_id: string;
    export_artifact_id: string;
    file_path: string;
    download_url: string;
    target_format: string;
    page_count: number;
    byte_size: number;
    sha256: string;
  }>(`/editor/pages/${encodeURIComponent(pageId)}/export`, {
    method: 'POST',
    body: JSON.stringify(options || {}),
  }),

  // --- Knowledge Catalogue & Governance ---
  getCatalogueSummary: () => request<any>('/catalogue/summary'),
  listTaxonomyGroups: () => request<any[]>('/catalogue/groups'),
  getTaxonomyGroup: (groupId: string) => request<any>(`/catalogue/groups/${groupId}`),
  listLicenses: () => request<any[]>('/catalogue/licenses'),
  promoteGroup: (payload: {
    group_id: string;
    target_status: string;
    reviewer_id: string;
    reviewer_role: string;
    rationale: string;
    verified_evidence_ids: string[];
  }) =>
    request<any>('/catalogue/reviews/promote', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listReviews: () => request<any[]>('/catalogue/reviews'),

  // --- Execution & Budgets ---
  getBudgets: (projectId?: string) => request<any>(`/execution/budgets${projectId ? `?project_id=${projectId}` : ''}`),
  listExecutionRuns: () => request<any[]>('/execution/runs'),
  getExecutionRun: (runId: string) => request<any>(`/execution/runs/${encodeURIComponent(runId)}`),
  cancelExecutionRun: (runId: string, reason = 'user_cancelled') =>
    request<any>(`/execution/runs/${encodeURIComponent(runId)}/cancel`, { method: 'POST', body: JSON.stringify({ reason }) }),
  resumeExecutionRun: (runId: string) => request<any>(`/execution/runs/${encodeURIComponent(runId)}/resume`, { method: 'POST' }),
  getExecutionEventsStreamUrl: (runId: string, after = 0) => `${API_BASE}/execution/runs/${encodeURIComponent(runId)}/events/stream?after=${after}`,
  listExecutionEvents: (params?: { run_id?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.run_id) query.set('run_id', params.run_id);
    if (params?.limit) query.set('limit', String(params.limit));
    const qs = query.toString();
    return request<any[]>(`/execution/events${qs ? `?${qs}` : ''}`);
  },
  recoverExecution: () => request<any>('/execution/recover', { method: 'POST' }),

  // --- Evaluation & Benchmarks ---
  getM0Benchmark: () => request<any>('/evaluation/benchmarks/m0'),
  getRegressions: () => request<{ readiness_inventory: any; cases: any[] }>('/evaluation/regressions'),
  getEngineReadiness: () => request<any>('/evaluation/readiness'),

  // --- Agent Coordinator (S9 Runtime) ---
  getAgentStatus: () => request<AgentStatusResponse>('/agent/status'),
  listCapabilities: (domain?: string, chatOnly = false) => {
    const query = new URLSearchParams();
    if (domain) query.set('domain', domain);
    if (chatOnly) query.set('chat_only', 'true');
    const qs = query.toString();
    return request<ToolDefinitionDto[]>(`/agent/capabilities${qs ? `?${qs}` : ''}`);
  },
  sendAgentChat: (payload: AgentChatRequest) =>
    request<AgentMessageDto>('/agent/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getAgentActivity: (activityId: string): Promise<AgentLiveActivityDto> =>
    request<AgentLiveActivityDto>(`/agent/activity/${encodeURIComponent(activityId)}`),
  uploadAttachment: (file: File, projectId = 'default_project'): Promise<AgentAttachmentDto> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);
    return request<AgentAttachmentDto>('/agent/attachments/upload', {
      method: 'POST',
      body: formData,
    });
  },
  createAgentPlan: (payload: { project_id: string; goal: string; spend_limit_usd?: number }): Promise<AgentPlanDto> =>
    request<AgentPlanDto>('/agent/plans', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getAgentPlan: (planId: string): Promise<AgentPlanDto> => request<AgentPlanDto>(`/agent/plans/${planId}`),
  submitApproval: (approvalId: string, decision: 'APPROVE' | 'REJECT', rationale?: string) =>
    request<ApprovalRequestDto>(`/agent/approvals/${approvalId}`, {
      method: 'POST',
      body: JSON.stringify({ decision, rationale }),
    }),
  getApproval: (approvalId: string): Promise<ApprovalRequestDto> => request<ApprovalRequestDto>(`/agent/approvals/${approvalId}`),
  listApprovals: (projectId?: string): Promise<ApprovalRequestDto[]> =>
    request<ApprovalRequestDto[]>(`/agent/approvals${projectId ? `?project_id=${projectId}` : ''}`),
  getRunTrace: (runId: string) => request<any>(`/agent/traces/${runId}`),
  listSessions: (projectId?: string): Promise<AgentSessionSummaryDto[]> =>
    request<AgentSessionSummaryDto[]>(`/agent/sessions${projectId ? `?project_id=${projectId}` : ''}`),
  createSession: (payload: { project_id: string; title?: string }): Promise<AgentSessionDto> =>
    request<AgentSessionDto>('/agent/sessions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getSession: (sessionId: string): Promise<AgentSessionDto> => request<AgentSessionDto>(`/agent/sessions/${sessionId}`),
  retryLastAgentTurn: (sessionId: string, projectId: string) =>
    request<AgentMessageDto>(`/agent/sessions/${encodeURIComponent(sessionId)}/retry-last`, {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId }),
    }),
  deleteLastAgentTurn: (sessionId: string, projectId: string) =>
    request<{ session_id: string; removed_message_ids: string[]; message_count: number }>(
      `/agent/sessions/${encodeURIComponent(sessionId)}/last-turn?project_id=${encodeURIComponent(projectId)}`,
      { method: 'DELETE' },
    ),

  // Creative Director & Universe Builder
  developCreativeUniverse: (payload: {
    project_id: string;
    user_prompt: string;
    mode?: CreativeMode;
    visual_references?: any[];
    offline_mode?: boolean;
  }): Promise<CreativePackage> =>
    request<CreativePackage>('/creative/develop', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getCreativePackage: (projectId: string): Promise<CreativePackage> =>
    request<CreativePackage>(`/creative/package/${projectId}`),
  saveCreativeLocation: (
    projectId: string,
    locationId: string,
    expectedPackageVersion: number,
    expectedLocationVersion: number | undefined,
    location: LocationSpec,
  ): Promise<CreativePackage> =>
    request<CreativePackage>(`/creative/package/${encodeURIComponent(projectId)}/locations/${encodeURIComponent(locationId)}`, {
      method: 'PUT',
      body: JSON.stringify({ expected_package_version: expectedPackageVersion, expected_location_version: expectedLocationVersion ?? null, location }),
    }),
  deleteCreativeLocation: (projectId: string, locationId: string, expectedPackageVersion: number): Promise<CreativePackage> =>
    request<CreativePackage>(`/creative/package/${encodeURIComponent(projectId)}/locations/${encodeURIComponent(locationId)}?expected_package_version=${expectedPackageVersion}`, {
      method: 'DELETE',
    }),
  validateCreativeCoherence: (projectId: string): Promise<ValidationResult> =>
    request<ValidationResult>(`/creative/validate/${projectId}`, {
      method: 'POST',
    }),
  addCreativeCharacter: (payload: {
    project_id: string;
    name: string;
    role?: string;
    age_range?: string;
    narrative_function?: string;
    visual_invariants?: string[];
    garments?: string[];
    commit_to_canon?: boolean;
  }): Promise<CreativePackage> =>
    request<CreativePackage>('/creative/character/add', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  approveCreativeCanon: (payload: {
    project_id: string;
    character_ids_to_commit?: string[];
    commit_style?: boolean;
  }): Promise<{ success: boolean; project_id: string; bible_version: number; canon_hash: string; message: string }> =>
    request<{ success: boolean; project_id: string; bible_version: number; canon_hash: string; message: string }>('/creative/approve', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getCreativeContracts: (projectId: string): Promise<CreativeContractsPackage> =>
    request<CreativeContractsPackage>(`/creative/contracts/${projectId}`),
  compileCreativePrompt: (payload: {
    project_id: string;
    character_id?: string;
    scene_description: string;
    emotion?: string;
    outfit_id?: string;
    is_action_shot?: boolean;
  }): Promise<{ project_id: string; character_id?: string; positive_prompt: string; negative_prompt: string }> =>
    request<{ project_id: string; character_id?: string; positive_prompt: string; negative_prompt: string }>('/creative/compile-prompt', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // --- Style Copier & Character Copier ---
  getCreativeCapabilities: (projectId: string): Promise<ProviderCapabilities> =>
    request<ProviderCapabilities>(`/projects/${projectId}/creative/capabilities`),

  analyzeStyleReferences: (
    projectId: string,
    req: { asset_ids: string[]; user_instructions?: string }
  ): Promise<StyleAnalysisRecord> => {
    if (!Array.isArray(req.asset_ids) || req.asset_ids.length === 0 || req.asset_ids.some((assetId) => typeof assetId !== 'string' || !assetId.trim())) {
      return Promise.reject(new ApiError({
        error_code: 'ERR_INVALID_STYLE_REFERENCES',
        message: 'Choose at least one registered style reference image before analyzing.',
        status: 422,
      }));
    }
    if (req.asset_ids.length > MAX_STYLE_ANALYSIS_REFERENCES) {
      return Promise.reject(new ApiError({
        error_code: 'ERR_TOO_MANY_STYLE_REFERENCES',
        message: `Style analysis accepts up to ${MAX_STYLE_ANALYSIS_REFERENCES} reference images per request.`,
        status: 422,
      }));
    }
    return request<StyleAnalysisRecord>(`/projects/${projectId}/creative/styles/analyze`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  saveStyleProfile: (projectId: string, profile: StyleProfile): Promise<StyleProfile> =>
    request<StyleProfile>(`/projects/${projectId}/creative/styles`, {
      method: 'POST',
      body: JSON.stringify(profile),
    }),

  listStyleProfiles: (projectId: string, includeArchived = false): Promise<StyleProfile[]> =>
    request<StyleProfile[]>(`/projects/${projectId}/creative/styles?include_archived=${includeArchived}`),

  listQuickStyleTemplates: (projectId: string): Promise<QuickStyleTemplateDto[]> =>
    request<QuickStyleTemplateDto[]>(`/projects/${projectId}/creative/style-templates`),

  applyQuickStyleTemplate: (projectId: string, templateId: string): Promise<StyleProfile> =>
    request<StyleProfile>(`/projects/${projectId}/creative/style-templates/${encodeURIComponent(templateId)}/apply`, {
      method: 'POST',
    }),

  getStyleProfile: (projectId: string, profileId: string): Promise<StyleProfile> =>
    request<StyleProfile>(`/projects/${projectId}/creative/styles/${profileId}`),

  approveStyleProfile: (projectId: string, profileId: string): Promise<StyleProfile> =>
    request<StyleProfile>(`/projects/${projectId}/creative/styles/${profileId}/approve`, {
      method: 'POST',
    }),

  archiveStyleProfile: (projectId: string, profileId: string): Promise<StyleProfile> =>
    request<StyleProfile>(`/projects/${projectId}/creative/styles/${profileId}/archive`, {
      method: 'POST',
    }),

  analyzeCharacterReferences: (
    projectId: string,
    req: { character_id: string; name: string; references: ReferenceBinding[]; known_canon_facts?: string[] }
  ): Promise<CharacterCopierProfile> =>
    request<CharacterCopierProfile>(`/projects/${projectId}/creative/characters/analyze`, {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  saveCharacterProfile: (projectId: string, profile: CharacterCopierProfile): Promise<CharacterCopierProfile> =>
    request<CharacterCopierProfile>(`/projects/${projectId}/creative/characters/profiles`, {
      method: 'POST',
      body: JSON.stringify(profile),
    }),

  listCharacterProfiles: (projectId: string, includeArchived = false): Promise<CharacterCopierProfile[]> =>
    request<CharacterCopierProfile[]>(`/projects/${projectId}/creative/characters/profiles?include_archived=${includeArchived}`),

  getCharacterProfile: (projectId: string, profileId: string): Promise<CharacterCopierProfile> =>
    request<CharacterCopierProfile>(`/projects/${projectId}/creative/characters/profiles/${profileId}`),

  approveCharacterProfile: (projectId: string, profileId: string): Promise<CharacterCopierProfile> =>
    request<CharacterCopierProfile>(`/projects/${projectId}/creative/characters/profiles/${profileId}/approve`, {
      method: 'POST',
    }),

  archiveCharacterProfile: (projectId: string, profileId: string): Promise<CharacterCopierProfile> =>
    request<CharacterCopierProfile>(`/projects/${projectId}/creative/characters/profiles/${profileId}/archive`, {
      method: 'POST',
    }),

  // --- Object Studio (Story Bible props are the single source of truth) ---
  listObjectProfiles: (projectId: string): Promise<ObjectStudioProfile[]> =>
    request<ObjectStudioProfile[]>(`/projects/${projectId}/creative/objects`),

  analyzeObjectReferences: (projectId: string, payload: {
    prop_id: string; name: string; asset_ids: string[]; creator_notes?: string;
  }): Promise<ObjectStudioProfile> =>
    request<ObjectStudioProfile>(`/projects/${projectId}/creative/objects/analyze`, {
      method: 'POST', body: JSON.stringify(payload),
    }),

  createObjectDraft: (projectId: string, payload: {
    prop: ObjectStudioProfile; expected_bible_version: number; reference_asset_ids?: string[];
  }): Promise<{ prop: ObjectStudioProfile; bible_version: number }> =>
    request<{ prop: ObjectStudioProfile; bible_version: number }>(`/projects/${projectId}/creative/objects/drafts`, {
      method: 'POST', body: JSON.stringify(payload),
    }),

  updateObjectDraft: (projectId: string, propId: string, payload: {
    prop: ObjectStudioProfile; expected_bible_version: number; reference_asset_ids?: string[];
  }): Promise<{ prop: ObjectStudioProfile; bible_version: number }> =>
    request<{ prop: ObjectStudioProfile; bible_version: number }>(`/projects/${projectId}/creative/objects/drafts/${encodeURIComponent(propId)}`, {
      method: 'PUT', body: JSON.stringify(payload),
    }),

  proposeObjectCanon: (projectId: string, propId: string, changeDescription?: string): Promise<any> =>
    request<any>(`/projects/${projectId}/creative/objects/${encodeURIComponent(propId)}/propose-canon`, {
      method: 'POST', body: JSON.stringify({ change_description: changeDescription }),
    }),

  generateCharacterSheetPlan: (projectId: string, profileId: string): Promise<any> =>
    request<any>(`/projects/${projectId}/creative/characters/profiles/${profileId}/sheet-plan`, {
      method: 'POST',
    }),

  generateCharacterTurnaroundSheet: (
    projectId: string,
    profileId: string,
    req: { style_profile_id?: string; max_attempts?: number } = {}
  ): Promise<any> =>
    request<any>(`/projects/${projectId}/creative/characters/profiles/${profileId}/generate-sheet`, {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  proposeCharacterInvariantsToCanon: (
    projectId: string,
    profileId: string,
    req: { change_description?: string } = {}
  ): Promise<{ status: string; proposal: any; message: string }> =>
    request<{ status: string; proposal: any; message: string }>(
      `/projects/${projectId}/creative/characters/profiles/${profileId}/propose-canon`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    ),

  generateWithCreativeProfiles: (
    projectId: string,
    req: {
      scene_action: string;
      shot_type?: string;
      style_profile_id?: string;
      character_profile_ids?: string[];
      panel_id?: string;
      scene_id?: string;
      max_attempts?: number;
      composition_notes?: string;
      lighting_intent?: string;
    }
  ): Promise<CreativeGenerationResult> =>
    request<CreativeGenerationResult>(`/projects/${projectId}/creative/generate`, {
      method: 'POST',
      body: JSON.stringify(req),
    }),
};
