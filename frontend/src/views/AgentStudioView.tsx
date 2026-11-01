import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Paperclip,
  Sparkles,
  Bot,
  User,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Coins,
  Database,
  ShieldCheck,
  ShieldAlert,
  X,
  FileText,
  Download,
  ChevronRight,
  ChevronDown,
  Copy,
  Check,
  Activity,
  RefreshCw,
  FileImage,
  ArrowUp,
  Loader2,
  Trash2,
  MessageSquare,
  Plus,
  Compass,
  History,
  Sliders,
  Palette,
  Users,
  FolderOpen,
  ImagePlus,
  ScanSearch,
  LayoutGrid,
  ClipboardList,
  Layers,
  type LucideIcon,
} from 'lucide-react';
import { Badge, BadgeVariant } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { useToast } from '../components/common/Toast';
import { MarkdownRenderer } from '../components/agent/MarkdownRenderer';
import { ImageLightbox, LightboxImage } from '../components/agent/ImageLightbox';
import { apiClient } from '../api/client';
import { AgentAttachmentDto, AgentLiveActivityDto, AgentToolResultDto, AgentSessionSummaryDto, AgentSessionDto, ApprovalRequestDto, StoryProductionJobDto, ToolDefinitionDto, PendingStoryActionDto } from '../types/agent';
import { AgentCharacter } from '../components/agent/character/AgentCharacter';
import { TabCharacterIcon } from '../components/agent/character/TabCharacterIcon';
import { AgentLoader } from '../components/agent/character/AgentLoader';
import { AgentStatus } from '../components/agent/character/AgentStatus';
import { ModelSelector, AVAILABLE_MODELS } from '../components/agent/ModelSelector';
import { LocationSpec, QuickStyleTemplateDto, StyleProfile } from '../types/creative';

interface AgentStudioViewProps {
  currentProject: string;
  projects?: Array<{ project_id: string; title: string }>;
  onSelectProject?: (projectId: string) => void;
}

export interface ChatAttachment {
  id: string;
  name: string;
  src: string;
  sourceType: 'user_upload' | 'registered_asset' | 'canonical_anchor';
  dimensions?: { width: number; height: number };
  sizeBytes?: number;
  sha256?: string;
  mimeType?: string;
  assetId?: string;
  file?: File;
}

export interface ToolCallEvent {
  callId: string;
  toolName: string;
  purpose: string;
  status: 'running' | 'succeeded' | 'failed' | 'gated' | 'blocked' | 'proposed';
  startedAt?: string;
  durationMs?: number;
  sanitizedInputs: Record<string, unknown>;
  outputSummary?: string;
  outputData?: unknown;
  relatedImage?: ChatAttachment;
  approvalId?: string;
}

interface QuickStylePickerProps {
  templates: QuickStyleTemplateDto[];
  open: boolean;
  applyingId: string;
  activeTemplateId?: string;
  onToggle: () => void;
  onApply: (templateId: string) => void;
}

const QuickStylePicker: React.FC<QuickStylePickerProps> = ({
  templates,
  open,
  applyingId,
  activeTemplateId,
  onToggle,
  onApply,
}) => (
  <div className="w-full">
    <button
      type="button"
      aria-expanded={open}
      onClick={onToggle}
      className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-zinc-200 transition hover:border-white/20 hover:bg-white/[0.08]"
    >
      <Palette className="h-3.5 w-3.5" aria-hidden="true" />
      Quick styles
      <span className="text-zinc-500">{templates.length}</span>
      {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
    </button>
    {open && (
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5" aria-label="Quick style templates">
        {templates.map((template) => {
          const isActive = activeTemplateId === template.template_id;
          const isApplying = applyingId === template.template_id;
          return (
            <article key={template.template_id} className={`overflow-hidden rounded-xl border bg-black/25 ${isActive ? 'border-white/50' : 'border-white/10'}`}>
              <div className="aspect-[4/3] bg-zinc-900">
                {template.preview_url || template.preview_asset_id ? (
                  <img
                    src={
                      template.preview_url
                        ? `${template.preview_url}?v=${template.preview_asset_id || '2'}&t=muse_char`
                        : (template.preview_asset_id ? apiClient.getAssetFileUrl(template.preview_asset_id) : '')
                    }
                    alt={`${template.name} generated example`}
                    title={`${template.preview_provider || 'Generated example'} · template ${template.version} · asset ${template.preview_asset_id || 'static preview'}`}
                    decoding="async"
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full flex-col items-center justify-center gap-1 text-zinc-500">
                    <ImagePlus className="h-5 w-5" aria-hidden="true" />
                    <span className="text-[9px]">Example not generated</span>
                  </div>
                )}
              </div>
              <div className="space-y-2 p-2.5 text-left">
                <div>
                  <h3 className="truncate text-[11px] font-semibold text-white">{template.name}</h3>
                  <p className="mt-1 line-clamp-2 min-h-7 text-[9px] leading-3 text-zinc-400">{template.description}</p>
                  {template.preview_asset_id && (
                    <p className="mt-1 truncate text-[8px] text-zinc-500">
                      Style example only · prompt-driven · {template.version}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  disabled={Boolean(applyingId)}
                  onClick={() => onApply(template.template_id)}
                  className="w-full rounded-md border border-white/15 px-2 py-1.5 text-[10px] font-medium text-zinc-100 transition hover:bg-white/10 disabled:cursor-wait disabled:opacity-60"
                >
                  {isApplying ? 'Adding…' : isActive ? 'In use' : 'Use style'}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    )}
  </div>
);

const TOOL_DOMAIN_ICONS: Record<string, LucideIcon> = {
  canon: Users,
  assets: FolderOpen,
  inspection: ScanSearch,
  verification: ShieldCheck,
  generation: ImagePlus,
  canvas: LayoutGrid,
  planning: ClipboardList,
  plan: ClipboardList,
  text: MessageSquare,
  execution: Coins,
};

function getToolIcon(tool?: ToolDefinitionDto): LucideIcon {
  return (tool && TOOL_DOMAIN_ICONS[tool.domain]) || Activity;
}

function getToolLabel(toolId: string, catalog: Record<string, ToolDefinitionDto>): string {
  const tool = catalog[toolId];
  if (tool?.name) return tool.name;
  return toolId.split('.').pop()?.replaceAll('_', ' ') || toolId;
}

export type AgentActivityState =
  | 'idle'
  | 'understanding_request'
  | 'checking_project_context'
  | 'inspecting_images'
  | 'preparing_plan'
  | 'calling_tool'
  | 'reviewing_results'
  | 'waiting_approval'
  | 'gated_s9_design_phase';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  timestamp: string;
  text: string;
  persisted?: boolean;
  attachments?: ChatAttachment[];
  toolCalls?: ToolCallEvent[];
  activityState?: AgentActivityState;
  activityLabel?: string;
  pendingApproval?: ApprovalRequestDto;
  productionJob?: StoryProductionJobDto;
  pendingStoryAction?: PendingStoryActionDto;
  modelUsage?: { status: 'reported' | 'partial' | 'unavailable'; model_calls: number; input_tokens?: number; output_tokens?: number; total_tokens?: number };
}

const projectSessionKey = (projectId: string) => `inkloop_agent_session_${projectId}`;
const projectTranscriptKey = (projectId: string) => `inkloop_agent_transcript_${projectId}`;
function readCachedTranscript(projectId: string): ChatMessage[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(projectTranscriptKey(projectId)) || '[]');
    return Array.isArray(parsed)
      ? parsed.filter((message) => message && typeof message.id === 'string' && ['user', 'assistant'].includes(message.role))
      : [];
  } catch {
    return [];
  }
}

function cacheSafeTranscript(messages: ChatMessage[]): ChatMessage[] {
  return messages.slice(-60).map((message) => ({
    ...message,
    attachments: message.attachments?.map(({ file: _file, ...attachment }) => ({
      ...attachment,
      // Browser-local URLs expire on reload; persisted asset URLs remain usable.
      src: /^(?:data:|blob:)/i.test(attachment.src) ? '' : attachment.src,
    })),
    toolCalls: message.toolCalls?.map(({ outputData: _outputData, ...call }) => ({
      ...call,
      outputSummary: call.outputSummary?.slice(0, 1200),
    })),
  }));
}

const createAgentSessionId = (projectId: string) => {
  const safeProjectId = projectId.replace(/[^a-zA-Z0-9_-]/g, '_');
  return `session_${safeProjectId}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
};
const sessionActivityKey = (projectId: string, sessionId: string) => `inkloop_agent_activity_${projectId}_${sessionId}`;

function visibleAgentSessions(
  sessions: AgentSessionSummaryDto[],
  projects: Array<{ project_id: string; title: string }>,
  currentProject: string,
): AgentSessionSummaryDto[] {
  const allowedProjects = new Set(projects.map((project) => project.project_id));
  allowedProjects.add(currentProject);
  return sessions
    .filter((session) => {
      if (!allowedProjects.has(session.project_id)) return false;
      if (/^(?:test[_-]|session_trace_verify_)/i.test(session.session_id)) return false;
      if (/^(?:test[_-]|api_universe_test$|same_page_production_test$)/i.test(session.project_id)) return false;
      // Exclude the oversized fixture transcript created by the runtime tests;
      // normal creator sessions remain available regardless of message count.
      if (session.session_id === 'session_inkloop' && session.message_count > 500) return false;
      return true;
    })
    .sort((a, b) => Date.parse(b.updated_at || '') - Date.parse(a.updated_at || ''));
}

function mapSessionTranscript(saved: AgentSessionDto, projectId: string): ChatMessage[] {
  const messages: ChatMessage[] = (saved.messages || []).map((message) => ({
    id: message.message_id,
    role: message.role as 'user' | 'assistant',
    timestamp: new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    text: message.text,
    pendingApproval: message.pending_approval,
    modelUsage: message.model_usage,
    productionJob: message.production_job,
    pendingStoryAction: message.pending_story_action,
    attachments: (message.attachments || []).map((attachment) => ({
      id: attachment.attachment_id,
      name: attachment.filename,
      src: attachment.asset_id
        ? apiClient.getAssetFileUrl(attachment.asset_id)
        : apiClient.getAgentAttachmentFileUrl(attachment.attachment_id, projectId),
      sourceType: attachment.is_canonical_anchor ? 'canonical_anchor' : 'registered_asset',
      dimensions: attachment.width && attachment.height
        ? { width: attachment.width, height: attachment.height }
        : undefined,
      sizeBytes: attachment.byte_size,
      sha256: attachment.content_sha256,
      mimeType: attachment.mime_type,
      assetId: attachment.asset_id,
    })),
    toolCalls: (message.tool_calls || []).map((call) => {
      const result = (message.tool_results || []).find((entry) => entry.call_id === call.call_id);
      return {
        callId: call.call_id,
        toolName: call.tool_id,
        purpose: call.tool_id,
        status: result?.status === 'success' ? 'succeeded' : result?.status === 'gated' ? 'gated' : result?.status === 'blocked' ? 'blocked' : 'failed',
        durationMs: Math.round((result?.duration_seconds || 0) * 1000),
        sanitizedInputs: call.arguments || {},
        outputSummary: result?.error || (typeof result?.output === 'string' ? result.output : JSON.stringify(result?.output || {})),
        outputData: result?.output || result?.error,
        approvalId: result?.approval_id,
      } as ToolCallEvent;
    }),
  }));
  return attachRecoveredProductionJob(messages, saved.metadata, projectId);
}

function attachRecoveredProductionJob(messages: ChatMessage[], metadata: Record<string, unknown> | undefined, projectId: string): ChatMessage[] {
  const jobs = metadata?.story_production_jobs;
  if (!jobs || typeof jobs !== 'object' || Array.isArray(jobs)) return messages;
  const candidates = Object.values(jobs as Record<string, unknown>)
    .filter((job): job is StoryProductionJobDto => Boolean(job && typeof job === 'object' && 'job_id' in job && 'panels' in job && (job as StoryProductionJobDto).project_id === projectId))
    .sort((a, b) => Date.parse(b.updated_at || '') - Date.parse(a.updated_at || ''));
  const recovered = candidates[0];
  if (!recovered || messages.some((message) => message.productionJob?.job_id === recovered.job_id)) return messages;
  const sourceIndex = recovered.source_request_message_id
    ? messages.findIndex((message) => message.id === recovered.source_request_message_id)
    : -1;
  // A deleted prompt must not resurrect its old job card. Attach the card to
  // the response for its original request, never to an unrelated later turn.
  if (sourceIndex < 0) return messages;
  const assistantOffset = messages.slice(sourceIndex + 1).findIndex((message) => message.role === 'assistant');
  const assistantIndex = assistantOffset < 0 ? -1 : sourceIndex + 1 + assistantOffset;
  const recoveredMessage: ChatMessage = assistantIndex >= 0
    ? { ...messages[assistantIndex], productionJob: recovered }
    : { id: `recovered_${recovered.job_id}`, role: 'assistant', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), text: 'Recovered saved production run.', persisted: true, productionJob: recovered };
  if (assistantIndex >= 0) return messages.map((message, index) => index === assistantIndex ? recoveredMessage : message);
  return [...messages, recoveredMessage];
}

export const AgentStudioView: React.FC<AgentStudioViewProps> = ({ currentProject, projects = [], onSelectProject }) => {
  const { showToast } = useToast();
  const projectDirectoryKey = projects.map((project) => project.project_id).sort().join('|');

  // Authoritative Context State
  const [bibleMetadata, setBibleMetadata] = useState<{ version: number; canon_hash: string }>({
    version: 1,
    canon_hash: '',
  });
  const [budgetData, setBudgetData] = useState<any | null>(null);
  const [readinessInventory, setReadinessInventory] = useState<any | null>(null);
  const [registeredAssets, setRegisteredAssets] = useState<any[]>([]);
  const [projectCharacters, setProjectCharacters] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedCharacterIds, setSelectedCharacterIds] = useState<string[]>(() => {
    try {
      const remembered = localStorage.getItem(`inkloop_agent_characters_${currentProject}`);
      return remembered ? JSON.parse(remembered) : [];
    } catch {
      return [];
    }
  });
  const [styleProfiles, setStyleProfiles] = useState<StyleProfile[]>([]);
  const [selectedStyleProfileId, setSelectedStyleProfileId] = useState('');
  const [quickStyleTemplates, setQuickStyleTemplates] = useState<QuickStyleTemplateDto[]>([]);
  const [quickStylesOpen, setQuickStylesOpen] = useState(false);
  const [applyingQuickStyleId, setApplyingQuickStyleId] = useState('');
  const [locations, setLocations] = useState<LocationSpec[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState('');
  const [selectionProject, setSelectionProject] = useState('');
  const [coordinatorConnected, setCoordinatorConnected] = useState<boolean>(false);
  const [agentMode, setAgentMode] = useState<'checking' | 'live_configured' | 'offline_explicit' | 'provider_unavailable'>('checking');
  const [selectedModelId, setSelectedModelId] = useState<string>(() => {
    try {
      const stored = localStorage.getItem('inkloop_active_model_id');
      if (stored && AVAILABLE_MODELS.some((m) => m.id === stored)) {
        return stored;
      }
      return AVAILABLE_MODELS.find((m) => m.isDefault)?.id || 'muse-spark-1.3';
    } catch {
      return 'muse-spark-1.3';
    }
  });

  const handleSelectModel = (modelId: string) => {
    setSelectedModelId(modelId);
    try {
      localStorage.setItem('inkloop_active_model_id', modelId);
    } catch {
      // ignore
    }
  };
  const [sessionId, setSessionId] = useState<string>(() => {
    try {
      return localStorage.getItem(projectSessionKey('default_project')) || `session_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    } catch {
      return `session_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    }
  });

  // Sessions and Approvals State
  const [sessions, setSessions] = useState<AgentSessionSummaryDto[]>([]);
  const [loadingSessions, setLoadingSessions] = useState<boolean>(true);
  const pendingSessionIdRef = useRef<string | null>(null);
  const [sessionSidebarOpen, setSessionSidebarOpen] = useState<boolean>(true);
  const [decidingApprovalId, setDecidingApprovalId] = useState<string | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<Record<string, ApprovalRequestDto>>({});

  // Chat Transcript State
  const [messages, setMessages] = useState<ChatMessage[]>(() => readCachedTranscript(currentProject));
  const [inputText, setInputText] = useState<string>('');
  const [attachedFiles, setAttachedFiles] = useState<ChatAttachment[]>([]);
  const [sessionSaveState, setSessionSaveState] = useState<'saved' | 'saving' | 'unsaved' | 'error'>('unsaved');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [activeActivityLabel, setActiveActivityLabel] = useState<string>('');
  const [activeToolSteps, setActiveToolSteps] = useState<AgentLiveActivityDto['tools']>([]);
  const [activeProductionJob, setActiveProductionJob] = useState<StoryProductionJobDto | null>(null);
  const [toolCatalog, setToolCatalog] = useState<Record<string, ToolDefinitionDto>>({});

  // UI Panels State
  const [assetPickerOpen, setAssetPickerOpen] = useState<boolean>(false);
  const [lightboxImage, setLightboxImage] = useState<LightboxImage | null>(null);
  const [expandedToolCalls, setExpandedToolCalls] = useState<Record<string, boolean>>({});

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const transcriptBottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const transcriptProjectRef = useRef(currentProject);
  const transcriptsByProjectRef = useRef<Map<string, ChatMessage[]>>(new Map());

  useEffect(() => {
    transcriptsByProjectRef.current.set(transcriptProjectRef.current, messages);
    try {
      const key = projectTranscriptKey(transcriptProjectRef.current);
      if (messages.length) localStorage.setItem(key, JSON.stringify(cacheSafeTranscript(messages)));
      else localStorage.removeItem(key);
    } catch {
      // The backend session remains authoritative if browser storage is full or disabled.
    }
  }, [messages]);

  // Load Authoritative Project State
  useEffect(() => {
    let isMounted = true;
    if (transcriptProjectRef.current !== currentProject) {
      transcriptsByProjectRef.current.set(transcriptProjectRef.current, messages);
      transcriptProjectRef.current = currentProject;
      setMessages(transcriptsByProjectRef.current.get(currentProject) || readCachedTranscript(currentProject));
    }
    setAttachedFiles([]);
    setInputText('');
    setActiveProductionJob(null);
    setSelectionProject('');
    setSelectedStyleProfileId('');
    setSelectedLocationId('');

    const loadState = async () => {
      // These project-scoped reads are independent. Fetch together so a slow
      // asset or budget endpoint cannot delay transcript restoration.
      const [capabilitiesResult, statusResult, bibleResult, budgetsResult, readinessResult,
        assetsResult, sessionsResult, profilesResult, templatesResult, packageResult, approvalsResult] = await Promise.all([
        apiClient.listCapabilities(undefined, true).catch(() => null),
        apiClient.getAgentStatus().catch(() => null),
        apiClient.getProjectBible(currentProject).catch(() => null),
        apiClient.getBudgets(currentProject).catch(() => null),
        apiClient.getEngineReadiness().catch(() => null),
        apiClient.listAssets({ project_id: currentProject }).catch(() => null),
        apiClient.listSessions().catch(() => null),
        apiClient.listStyleProfiles(currentProject).catch(() => null),
        apiClient.listQuickStyleTemplates(currentProject).catch(() => null),
        apiClient.getCreativePackage(currentProject).catch(() => null),
        apiClient.listApprovals(currentProject).catch(() => null),
      ]);
      // The backend's callable image-chat catalog drives both the model's tool
      // menu and these UI labels, preventing a second hand-maintained list.
      try {
        const capabilities = capabilitiesResult;
        if (isMounted && capabilities) {
          setToolCatalog(Object.fromEntries(capabilities.map((tool) => [tool.tool_id, tool])));
        }
      } catch {
        // Calls remain visible by stable tool ID if capability metadata is offline.
      }

      // 1. Probe Agent Status (Detecting S9 gate honest connection)
      try {
        const agentStatus = statusResult;
        if (isMounted && agentStatus) {
          setCoordinatorConnected(agentStatus.runtime_ready);
          setAgentMode(agentStatus.mode);
        }
      } catch {
        if (isMounted) {
          setCoordinatorConnected(false);
          setAgentMode('provider_unavailable');
        }
      }

      // 2. Fetch Story Bible for canonical hash & version
      try {
        const bible = bibleResult;
        if (isMounted && bible) {
          const characters = Object.entries(bible.characters || {}).map(([id, character]: [string, any]) => ({ id, name: character.name || id }));
          setProjectCharacters(characters);
          let rememberedCharacters: string[] = [];
          try {
            const raw = localStorage.getItem(`inkloop_agent_characters_${currentProject}`);
            if (raw) rememberedCharacters = JSON.parse(raw);
          } catch { /* ignore */ }
          setSelectedCharacterIds((selected) => {
            const pool = selected.length > 0 ? selected : rememberedCharacters;
            return pool.filter((id) => characters.some((character) => character.id === id));
          });
          setBibleMetadata({
            version: bible.version || bible.bible_version || 1,
            canon_hash: bible.canon_hash || '',
          });
        }
      } catch {
        // Leave canon details empty when the active project's Story Bible is unavailable.
      }

      // 3. Fetch Budgets
      try {
        const budgets = budgetsResult;
        if (isMounted) setBudgetData(budgets);
      } catch {
        // Fallback
      }

      // 4. Fetch Engine Readiness
      try {
        const readiness = readinessResult;
        if (isMounted && readiness) setReadinessInventory(readiness);
      } catch {
        // Fallback
      }

      // 5. Fetch Real Registered Assets
      try {
        const assets = assetsResult;
        if (isMounted) setRegisteredAssets(assets || []);
      } catch {
        // Fallback
      }

      // 6. Fetch Sessions List
      try {
        const sessList = sessionsResult;
        if (isMounted && sessList) {
          const visibleSessions = visibleAgentSessions(sessList, projects, currentProject);
          const activeProjectSessions = sessList
            .filter((session) => session.project_id === currentProject)
            .sort((a, b) => Date.parse(b.updated_at || '') - Date.parse(a.updated_at || ''));
          setSessions(visibleSessions);
          setLoadingSessions(false);
          let rememberedSessionId = '';
          try { rememberedSessionId = localStorage.getItem(projectSessionKey(currentProject)) || ''; } catch { /* storage is optional */ }
          const requestedSessionId = pendingSessionIdRef.current;
          const requestedSession = requestedSessionId
            ? activeProjectSessions.find((session) => session.session_id === requestedSessionId)
            : undefined;
          const selectedSession = requestedSession
            || activeProjectSessions.find((session) => session.session_id === rememberedSessionId)
            || activeProjectSessions[0];
          if (selectedSession) {
            const saved = await apiClient.getSession(selectedSession.session_id);
            if (isMounted) {
              if (requestedSession && pendingSessionIdRef.current === requestedSession.session_id) pendingSessionIdRef.current = null;
              setSessionId(saved.session_id);
              try { localStorage.setItem(projectSessionKey(currentProject), saved.session_id); } catch { /* session still loads */ }
              setSessionSaveState('saved');
              setMessages(attachRecoveredProductionJob((saved.messages || []).map((m) => ({
                id: m.message_id,
                role: m.role as 'user' | 'assistant',
                timestamp: new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                text: m.text,
                pendingApproval: m.pending_approval,
                modelUsage: m.model_usage,
                productionJob: m.production_job,
                pendingStoryAction: m.pending_story_action,
                attachments: (m.attachments || []).map((a) => ({
                  id: a.attachment_id,
                  name: a.filename,
                  src: a.asset_id ? apiClient.getAssetFileUrl(a.asset_id) : apiClient.getAgentAttachmentFileUrl(a.attachment_id, currentProject),
                  sourceType: a.is_canonical_anchor ? 'canonical_anchor' : 'registered_asset',
                  dimensions: a.width && a.height ? { width: a.width, height: a.height } : undefined,
                  sizeBytes: a.byte_size,
                  sha256: a.content_sha256,
                  mimeType: a.mime_type,
                  assetId: a.asset_id,
                })),
                toolCalls: (m.tool_calls || []).map((tc) => {
                  const result = (m.tool_results || []).find((entry) => entry.call_id === tc.call_id);
                  return {
                    callId: tc.call_id,
                    toolName: tc.tool_id,
                    purpose: tc.tool_id,
                    status: result?.status === 'success' ? 'succeeded' : result?.status === 'gated' ? 'gated' : result?.status === 'blocked' ? 'blocked' : 'failed',
                    durationMs: Math.round((result?.duration_seconds || 0) * 1000),
                    sanitizedInputs: tc.arguments || {},
                    outputSummary: result?.error || (typeof result?.output === 'string' ? result.output : JSON.stringify(result?.output || {})),
                    outputData: result?.output || result?.error,
                    approvalId: result?.approval_id,
                  } as ToolCallEvent;
                }),
              })), saved.metadata, currentProject));
              // Tool activity is keyed by session and survives a browser reload.
              // Resume polling while the backend is still executing this turn.
              let pendingActivityId = '';
              try { pendingActivityId = localStorage.getItem(sessionActivityKey(currentProject, saved.session_id)) || ''; } catch { /* storage is optional */ }
              if (pendingActivityId) {
                const pollRecoveredActivity = async () => {
                  if (!isMounted) return;
                  try {
                    const activity = await apiClient.getAgentActivity(pendingActivityId);
                    if (!isMounted) return;
                    setActiveToolSteps(activity.tools || []);
                    setActiveProductionJob(activity.production_job || null);
                    if (!activity.finished) {
                      setIsProcessing(true);
                      setActiveActivityLabel('Agent is continuing the saved request…');
                      window.setTimeout(pollRecoveredActivity, 700);
                      return;
                    }
                    try { localStorage.removeItem(sessionActivityKey(currentProject, saved.session_id)); } catch { /* ignore */ }
                    setIsProcessing(false);
                    setActiveActivityLabel('');
                    setActiveProductionJob(null);
                    const completed = await apiClient.getSession(saved.session_id);
                    if (isMounted) {
                      setMessages(attachRecoveredProductionJob((completed.messages || []).map((m) => ({
                        id: m.message_id,
                        role: m.role as 'user' | 'assistant',
                        timestamp: new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                        text: m.text,
                        pendingApproval: m.pending_approval,
                        modelUsage: m.model_usage,
                        productionJob: m.production_job,
                pendingStoryAction: m.pending_story_action,
                        attachments: (m.attachments || []).map((a) => ({
                          id: a.attachment_id,
                          name: a.filename,
                          src: a.asset_id ? apiClient.getAssetFileUrl(a.asset_id) : apiClient.getAgentAttachmentFileUrl(a.attachment_id, currentProject),
                          sourceType: a.is_canonical_anchor ? 'canonical_anchor' : 'registered_asset',
                          dimensions: a.width && a.height ? { width: a.width, height: a.height } : undefined,
                          sizeBytes: a.byte_size,
                          sha256: a.content_sha256,
                          mimeType: a.mime_type,
                          assetId: a.asset_id,
                        })),
                        toolCalls: (m.tool_calls || []).map((tc) => {
                          const result = (m.tool_results || []).find((entry) => entry.call_id === tc.call_id);
                          return {
                            callId: tc.call_id,
                            toolName: tc.tool_id,
                            purpose: tc.tool_id,
                            status: result?.status === 'success' ? 'succeeded' : result?.status === 'gated' ? 'gated' : result?.status === 'blocked' ? 'blocked' : 'failed',
                            durationMs: Math.round((result?.duration_seconds || 0) * 1000),
                            sanitizedInputs: tc.arguments || {},
                            outputSummary: result?.error || (typeof result?.output === 'string' ? result.output : JSON.stringify(result?.output || {})),
                            outputData: result?.output || result?.error,
                            approvalId: result?.approval_id,
                          } as ToolCallEvent;
                        }),
                      })), completed.metadata, currentProject));
                    }
                  } catch {
                    if (isMounted) window.setTimeout(pollRecoveredActivity, 1200);
                  }
                };
                void pollRecoveredActivity();
              }
            }
          } else {
            // Never keep the previous project's in-memory session ID when the
            // active project has no saved chats.
            const freshSessionId = createAgentSessionId(currentProject);
            setSessionId(freshSessionId);
            setSessionSaveState('unsaved');
            try { localStorage.setItem(projectSessionKey(currentProject), freshSessionId); } catch { /* tab state remains usable */ }
          }
        }
      } catch {
        if (isMounted) {
          // If session discovery failed, use a new project-local ID instead of
          // accidentally sending with the last project's session.
          const freshSessionId = createAgentSessionId(currentProject);
          setSessionId(freshSessionId);
          setSessionSaveState('unsaved');
          try { localStorage.setItem(projectSessionKey(currentProject), freshSessionId); } catch { /* tab state remains usable */ }
        }
      }

      try {
        const profiles = profilesResult;
        if (isMounted) {
          setStyleProfiles(profiles || []);
          const remembered = localStorage.getItem(`inkloop_agent_style_${currentProject}`) || '';
          setSelectedStyleProfileId((profiles || []).some((profile) => profile.profile_id === remembered) ? remembered : '');
        }
      } catch {
        if (isMounted) setStyleProfiles([]);
      }

      try {
        const templates = templatesResult;
        if (isMounted) setQuickStyleTemplates(templates || []);
      } catch {
        if (isMounted) setQuickStyleTemplates([]);
      }

      try {
        const creativePackage = packageResult;
        const projectLocations = creativePackage ? Object.values(creativePackage.world_bible?.locations || {}) : [];
        if (isMounted) {
          setLocations(projectLocations);
          const remembered = localStorage.getItem(`inkloop_agent_location_${currentProject}`) || '';
          setSelectedLocationId(projectLocations.some((location) => location.location_id === remembered) ? remembered : '');
        }
      } catch {
        if (isMounted) setLocations([]);
      }
      if (isMounted) setSelectionProject(currentProject);

      // 7. Fetch Pending Approvals
      try {
        const apprs = approvalsResult;
        if (isMounted && apprs) {
          const map: Record<string, ApprovalRequestDto> = {};
          apprs.forEach((a) => {
            map[a.approval_id] = a;
          });
          setPendingApprovals(map);
        }
      } catch {
        // Fallback
      }
    };

    loadState();
    return () => {
      isMounted = false;
    };
  }, [currentProject, projectDirectoryKey]);

  // Keep the Recent Sessions list current across chat turns, project switches,
  // and other tabs. Poll faster while the Agent is actively creating a turn.
  useEffect(() => {
    let active = true;
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    const refreshSessions = async () => {
      try {
        const savedSessions = await apiClient.listSessions();
        if (active) setSessions(visibleAgentSessions(savedSessions, projects, currentProject));
      } catch {
        // Keep the last known history visible if a refresh briefly fails.
      } finally {
        if (active) refreshTimer = window.setTimeout(refreshSessions, isProcessing ? 500 : 2000);
      }
    };
    void refreshSessions();
    return () => {
      active = false;
      if (refreshTimer) clearTimeout(refreshTimer);
    };
  }, [currentProject, projectDirectoryKey, isProcessing]);

  useEffect(() => {
    if (selectionProject !== currentProject || !sessionId) return;
    try { localStorage.setItem(projectSessionKey(currentProject), sessionId); } catch { /* session remains available in this tab */ }
  }, [currentProject, sessionId, selectionProject]);

  useEffect(() => {
    if (selectionProject !== currentProject) return;
    if (selectedStyleProfileId) localStorage.setItem(`inkloop_agent_style_${currentProject}`, selectedStyleProfileId);
    else localStorage.removeItem(`inkloop_agent_style_${currentProject}`);
  }, [currentProject, selectedStyleProfileId, selectionProject]);

  useEffect(() => {
    if (selectionProject !== currentProject) return;
    if (selectedLocationId) localStorage.setItem(`inkloop_agent_location_${currentProject}`, selectedLocationId);
    else localStorage.removeItem(`inkloop_agent_location_${currentProject}`);
  }, [currentProject, selectedLocationId, selectionProject]);

  useEffect(() => {
    if (selectionProject !== currentProject) return;
    try {
      if (selectedCharacterIds.length > 0) {
        localStorage.setItem(`inkloop_agent_characters_${currentProject}`, JSON.stringify(selectedCharacterIds));
      } else {
        localStorage.removeItem(`inkloop_agent_characters_${currentProject}`);
      }
    } catch { /* storage unavailable */ }
  }, [currentProject, selectedCharacterIds, selectionProject]);

  // Auto-scroll to bottom of transcript
  useEffect(() => {
    transcriptBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing, activeActivityLabel]);

  // Compute SHA-256 for local file
  const computeFileSha256 = async (file: File): Promise<string> => {
    try {
      const arrayBuffer = await file.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
    } catch {
      return 'hash_computation_unavailable';
    }
  };

  // Get image dimensions from URL
  const getImageDimensions = (url: string): Promise<{ width: number; height: number }> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
      img.onerror = () => resolve({ width: 0, height: 0 });
      img.src = url;
    });
  };

  const MAX_FILE_BYTES = 15 * 1024 * 1024; // 15MB security ceiling matching backend
  const ALLOWED_MIME_TYPES = [
    'image/png', 'image/jpeg', 'image/webp', 'text/plain', 'text/markdown',
    'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ];

  // Handle Local File Upload
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const extension = file.name.split('.').pop()?.toLowerCase();
      const mimeByExtension: Record<string, string> = {
        png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp',
        txt: 'text/plain', md: 'text/markdown', pdf: 'application/pdf',
        docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      };
      const inferredMime = ALLOWED_MIME_TYPES.includes(file.type) ? file.type : mimeByExtension[extension || ''];
      if (!inferredMime || !ALLOWED_MIME_TYPES.includes(inferredMime)) {
        showToast({
          type: 'warning',
          title: 'Unsupported File Format',
        message: `File format '${file.type || extension || 'unknown'}' is unsupported. Allowed: PNG, JPEG, WebP, TXT, Markdown, PDF, DOCX.`,
        });
        continue;
      }

      if (file.size > MAX_FILE_BYTES) {
        showToast({
          type: 'warning',
          title: 'File Too Large',
          message: `File exceeds 15MB security limit: received ${(file.size / (1024 * 1024)).toFixed(1)}MB.`,
        });
        continue;
      }

      const src = URL.createObjectURL(file);
      const sha256 = await computeFileSha256(file);
      const dimensions = inferredMime.startsWith('image/') ? await getImageDimensions(src) : undefined;

      const attachment: ChatAttachment = {
        id: `att_${Date.now()}_${i}`,
        name: file.name,
        src,
        sourceType: 'user_upload',
        dimensions,
        sizeBytes: file.size,
        sha256,
        mimeType: inferredMime,
        file,
      };

      setAttachedFiles((prev) => [...prev, attachment]);
      setSessionSaveState('unsaved');
    }

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Remove an attached file
  const handleRemoveAttachment = (id: string) => {
    setAttachedFiles((prev) => prev.filter((a) => a.id !== id));
    setSessionSaveState('unsaved');
  };

  // Attach a registered asset directly from the library
  const handleAttachRegisteredAsset = (asset: any) => {
    const isAnchor = asset.metadata?.is_canonical_anchor === true;
    const attachment: ChatAttachment = {
      id: `att_reg_${asset.asset_id}`,
      name: asset.logical_filename || asset.asset_id,
      src: apiClient.getAssetFileUrl(asset.asset_id),
      sourceType: isAnchor ? 'canonical_anchor' : 'registered_asset',
      dimensions: asset.dimensions
        ? { width: asset.dimensions[0], height: asset.dimensions[1] }
        : undefined,
      sizeBytes: asset.size_bytes,
      sha256: asset.content_sha256,
      mimeType: asset.mime_type || 'image/png',
      assetId: asset.asset_id,
    };

    setAttachedFiles((prev) => [...prev, attachment]);
    setSessionSaveState('unsaved');
    setAssetPickerOpen(false);
    showToast({
      type: 'info',
      title: 'Asset Attached',
      message: `Attached ${attachment.name} to conversation.`,
    });
  };

  // Start fresh chat session
  const handleNewChat = () => {
    const newId = createAgentSessionId(currentProject);
    setSessionId(newId);
    try { localStorage.setItem(projectSessionKey(currentProject), newId); } catch { /* session remains available in this tab */ }
    setMessages([]);
    setInputText('');
    setAttachedFiles([]);
    setSessionSaveState('unsaved');
    showToast({ type: 'info', title: 'New Chat Session', message: 'Ready for new creative exploration.' });
  };

  // Hydrate an existing session
  const handleSelectSession = async (targetSessionId: string, forceReload = false) => {
    const sessionSummary = sessions.find((session) => session.session_id === targetSessionId);
    if (sessionSummary && sessionSummary.project_id !== currentProject) {
      if (!onSelectProject) {
        showToast({ type: 'error', title: 'Project unavailable', message: 'Switch to this session’s project to open its chat.' });
        return;
      }
      pendingSessionIdRef.current = targetSessionId;
      onSelectProject(sessionSummary.project_id);
      return;
    }
    if (!forceReload && targetSessionId === sessionId && messages.length > 0) return;
    try {
      setIsProcessing(true);
      setActiveActivityLabel('Hydrating session transcript from backend...');
      const sess = await apiClient.getSession(targetSessionId);
      if (sess.project_id !== currentProject) {
        throw new Error('That chat belongs to a different project. Choose a chat from the active project.');
      }
      setSessionId(sess.session_id);
      try { localStorage.setItem(projectSessionKey(currentProject), sess.session_id); } catch { /* session still loads */ }

      const loadedMessages: ChatMessage[] = (sess.messages || []).map((m) => {
        const toolCalls: ToolCallEvent[] = [];
        if (m.tool_calls && m.tool_calls.length > 0) {
          const resMap = new Map<string, AgentToolResultDto>();
          (m.tool_results || []).forEach((r) => resMap.set(r.call_id, r));
          for (const tc of m.tool_calls) {
            const res = resMap.get(tc.call_id);
            let relatedAtt: ChatAttachment | undefined;
            if (res?.output && typeof res.output === 'object') {
              const out = res.output as any;
              const assetId = out.asset_id || (out.url ? out.url.split('/')[4] : undefined);
              if (assetId || out.url) {
                relatedAtt = {
                  id: assetId || tc.call_id,
                  name: out.filename || out.logical_filename || `${tc.arguments?.panel_id || 'panel'}.png`,
                  src: out.url || apiClient.getAssetFileUrl(assetId),
                  sourceType: 'registered_asset',
                  dimensions: out.width && out.height ? { width: out.width, height: out.height } : undefined,
                  sizeBytes: out.byte_size,
                  sha256: out.content_sha256,
                  mimeType: out.mime_type || 'image/png',
                  assetId: assetId,
                };
              }
            }
            toolCalls.push({
              callId: tc.call_id,
              toolName: tc.tool_id,
              purpose: tc.tool_id,
              status: res?.status === 'success' ? 'succeeded' : res?.status === 'gated' ? 'gated' : res?.status === 'blocked' ? 'blocked' : 'failed',
              durationMs: res ? Math.round((res.duration_seconds || 0) * 1000) : 0,
              sanitizedInputs: tc.arguments || {},
              outputSummary: res?.error || (typeof res?.output === 'string' ? res.output : JSON.stringify(res?.output, null, 2)),
              outputData: res?.output || res?.error,
              relatedImage: relatedAtt,
              approvalId: res?.approval_id,
            });
          }
        }
        return {
          id: m.message_id,
          role: m.role as 'user' | 'assistant',
          persisted: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: m.text,
          toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
          pendingApproval: m.pending_approval,
          productionJob: m.production_job,
          pendingStoryAction: m.pending_story_action,
          attachments: (m.attachments || []).map((a) => ({
            id: a.attachment_id,
            name: a.filename,
            src: a.asset_id ? apiClient.getAssetFileUrl(a.asset_id) : apiClient.getAgentAttachmentFileUrl(a.attachment_id, currentProject),
            sourceType: a.is_canonical_anchor ? 'canonical_anchor' : 'registered_asset',
            dimensions: a.width && a.height ? { width: a.width, height: a.height } : undefined,
            sizeBytes: a.byte_size,
            sha256: a.content_sha256,
            mimeType: a.mime_type,
            assetId: a.asset_id,
          })),
        };
      });

      setMessages(attachRecoveredProductionJob(loadedMessages, sess.metadata, currentProject));
      const lastUserMsg = [...(sess.messages || [])].reverse().find((m) => m.role === 'user' && Array.isArray((m.request_context as any)?.selected_character_ids) && (m.request_context as any).selected_character_ids.length > 0);
      if (lastUserMsg && Array.isArray((lastUserMsg.request_context as any)?.selected_character_ids)) {
        const sessionChars: string[] = (lastUserMsg.request_context as any).selected_character_ids;
        setSelectedCharacterIds((current) => {
          if (current.length > 0) return current;
          try {
            localStorage.setItem(`inkloop_agent_characters_${currentProject}`, JSON.stringify(sessionChars));
          } catch { /* ignore */ }
          return sessionChars;
        });
      }
      setSessionSaveState('saved');
      showToast({ type: 'info', title: 'Session Hydrated', message: `Loaded session ${targetSessionId.slice(0, 16)}...` });
    } catch (err: any) {
      setSessionSaveState('error');
      showToast({ type: 'error', title: 'Load Failed', message: err.message || 'Could not hydrate session.' });
    } finally {
      setIsProcessing(false);
      setActiveActivityLabel('');
    }
  };

  const handleRetryLastTurn = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    setSessionSaveState('saving');
    setActiveActivityLabel('Retrying your last prompt…');
    try {
      await apiClient.retryLastAgentTurn(sessionId, currentProject);
      await handleSelectSession(sessionId, true);
      showToast({ type: 'success', title: 'Prompt retried', message: 'The latest attempt was replaced with the new response.' });
    } catch (error: any) {
      setSessionSaveState('error');
      showToast({
        type: 'error',
        title: 'Retry failed',
        message: error?.payload?.message || error?.message || 'The last prompt could not be retried.',
      });
    } finally {
      setIsProcessing(false);
      setActiveActivityLabel('');
    }
  };

  const handleDeleteLastTurn = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    setSessionSaveState('saving');
    setActiveActivityLabel('Removing the last prompt and reply…');
    try {
      await apiClient.deleteLastAgentTurn(sessionId, currentProject);
      await handleSelectSession(sessionId, true);
      showToast({ type: 'success', title: 'Last attempt deleted', message: 'The prompt and reply were removed from this chat. Completed tool actions and assets remain.' });
      try {
        const sessList = await apiClient.listSessions();
        setSessions(visibleAgentSessions(sessList || [], projects, currentProject));
      } catch { /* transcript deletion already succeeded */ }
    } catch (error: any) {
      setSessionSaveState('error');
      showToast({
        type: 'error',
        title: 'Delete failed',
        message: error?.payload?.message || error?.message || 'The last attempt could not be deleted.',
      });
    } finally {
      setIsProcessing(false);
      setActiveActivityLabel('');
    }
  };

  // Submit human approval decision
  const handleDecision = async (approvalId: string, decision: 'APPROVE' | 'REJECT', rationale?: string) => {
    try {
      setDecidingApprovalId(approvalId);
      const res = await apiClient.submitApproval(approvalId, decision, rationale);
      setPendingApprovals((prev) => ({ ...prev, [approvalId]: res }));
      showToast({
        type: decision === 'APPROVE' ? 'success' : 'info',
        title: decision === 'APPROVE' ? 'Action Approved' : 'Action Rejected',
        message: `Approval ${approvalId} recorded as ${res.status}.`,
      });
    } catch (err: any) {
      showToast({
        type: 'error',
        title: 'Decision Blocked',
        message: err.payload?.message || err.message || 'Failed to submit decision.',
      });
    } finally {
      setDecidingApprovalId(null);
    }
  };

  // Handle Form Submission
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputText).trim();
    if (!query && attachedFiles.length === 0) return;
    if (isProcessing) return;
    if (selectionProject !== currentProject || !sessionId) {
      showToast({
        type: 'info',
        title: 'Project is still loading',
        message: 'Wait for this project’s chat to load, then send your message again.',
      });
      return;
    }

    const userMessageId = `msg_user_${Date.now()}`;
    const assistantMessageId = `msg_ast_${Date.now()}`;
    const sentAttachments = [...attachedFiles];

    // Upload first so a failed attachment stays in the composer and is not shown as submitted.
    const userMessage: ChatMessage = {
      id: userMessageId,
      role: 'user',
      persisted: false,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: query,
      attachments: sentAttachments,
    };

    setIsProcessing(true);
    setActiveActivityLabel('Preparing message...');
    setActiveToolSteps([]);
    setActiveProductionJob(null);

    // 2. Upload attachments if necessary (Fail-closed per Rule C)
    const backendAttachments: AgentAttachmentDto[] = [];
    for (const att of sentAttachments) {
      if (att.file) {
        try {
          setActiveActivityLabel(`Uploading & inspecting ${att.name}...`);
          const uploaded = await apiClient.uploadAttachment(att.file, currentProject);
          backendAttachments.push(uploaded);
        } catch (uploadErr: any) {
          const errMsg = uploadErr.payload?.message || uploadErr.message || `Failed to upload ${att.name}`;
          showToast({
            type: 'error',
            title: 'Attachment Upload Blocked',
            message: errMsg,
          });
          setInputText(query);
          setSessionSaveState('unsaved');
          setIsProcessing(false);
          setActiveActivityLabel('');
          setIsProcessing(false);
          setActiveActivityLabel('');
          return; // Keep the text and files available for retry; no turn was sent.
        }
      } else if (att.assetId) {
        backendAttachments.push({
          attachment_id: att.assetId,
          filename: att.name,
          mime_type: att.mimeType || 'image/png',
          byte_size: att.sizeBytes || 0,
          content_sha256: att.sha256 || '',
          width: att.dimensions?.width,
          height: att.dimensions?.height,
          asset_id: att.assetId,
          is_canonical_anchor: att.sourceType === 'canonical_anchor',
        });
      }
    }

    let canvasTarget: { page_id: string; panel_id: string; expected_revision: number } | undefined;
    let canvasTargetNotice = '';
    const activePageId = localStorage.getItem(`inkloop_active_page_${currentProject}`);
    const activePanelId = localStorage.getItem(`inkloop_active_panel_${currentProject}`);
    if (activePageId) {
      let hasUnsavedCanvasChanges = false;
      try {
        const draft = JSON.parse(localStorage.getItem(`inkloop_editor_draft_${currentProject}`) || 'null');
        hasUnsavedCanvasChanges = draft?.pageId === activePageId && draft?.hasChanges === true;
      } catch {
        // A malformed local draft must not be mistaken for a saved editor state.
        hasUnsavedCanvasChanges = true;
      }
      if (hasUnsavedCanvasChanges) {
        canvasTargetNotice = 'Your Canvas page has unsaved edits, so I kept this picture in your Library and did not change the page. Save the page first to place new artwork there.';
      } else if (!activePanelId) {
        canvasTargetNotice = 'This picture is in your Library. Select a panel in Canvas first if you want the next picture placed directly on the page.';
      } else {
        try {
          const page = await apiClient.getEditablePage(activePageId);
          const selectedPanelExists = page.layout?.panel_slots?.some((panel: any) => panel.panel_id === activePanelId);
          if (page.project_id === currentProject && selectedPanelExists) {
            canvasTarget = { page_id: page.page_id, panel_id: activePanelId, expected_revision: page.revision };
          } else {
            canvasTargetNotice = 'I could not match the selected Canvas page and panel, so this picture will stay in your Library.';
          }
        } catch {
          canvasTargetNotice = 'I could not load the selected Canvas page, so this picture will stay in your Library.';
        }
      }
    } else {
      canvasTargetNotice = 'This picture is in your Library. Select a page and panel in Canvas first if you want it placed directly on the page.';
    }

    // 3. Dispatch to real API endpoint (apiClient.sendAgentChat)
    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setAttachedFiles([]);
    setActiveActivityLabel('Waiting for the Agent response...');
    let activeSessionId = sessionId;
    let activityId = globalThis.crypto?.randomUUID?.() || `activity_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    try {
      localStorage.setItem(projectSessionKey(currentProject), activeSessionId);
      localStorage.setItem(sessionActivityKey(currentProject, activeSessionId), activityId);
    } catch { /* the request still runs; reload recovery is unavailable without browser storage */ }
    let keepPollingActivity = true;
    let activityPollTimer: ReturnType<typeof setTimeout> | undefined;
    const pollActivity = async () => {
      const requestedActivityId = activityId;
      try {
        const activity = await apiClient.getAgentActivity(requestedActivityId);
        if (requestedActivityId !== activityId) return;
        setActiveToolSteps(activity.tools || []);
        setActiveProductionJob(activity.production_job || null);
      } catch {
        // The chat response remains authoritative if live activity polling is unavailable.
      } finally {
        if (keepPollingActivity) activityPollTimer = setTimeout(pollActivity, 500);
      }
    };
    activityPollTimer = setTimeout(pollActivity, 250);
    let assistantReply = '';
    const toolCalls: ToolCallEvent[] = [];
    let receivedApproval: ApprovalRequestDto | undefined = undefined;
    let responseAttachments: ChatAttachment[] = [];
    let response: Awaited<ReturnType<typeof apiClient.sendAgentChat>> | undefined;
    let pageToOpen: string | undefined;

    try {
      const chatPayload: Parameters<typeof apiClient.sendAgentChat>[0] = {
        project_id: currentProject,
        message: query,
        attachments: backendAttachments,
        session_id: activeSessionId,
        selected_character_ids: selectedCharacterIds,
        selected_style_profile_id: selectedStyleProfileId || undefined,
        selected_style_version: styleProfiles.find((profile) => profile.profile_id === selectedStyleProfileId)?.version,
        selected_location_id: selectedLocationId || undefined,
        selected_location_version: locations.find((location) => location.location_id === selectedLocationId)?.version,
        activity_id: activityId,
        canvas_page_id: canvasTarget?.page_id,
        canvas_panel_id: canvasTarget?.panel_id,
        canvas_expected_revision: canvasTarget?.expected_revision,
        model: selectedModelId,
      };
      try {
        response = await apiClient.sendAgentChat(chatPayload);
      } catch (requestError: any) {
        const errorMessage = String(requestError?.payload?.message || requestError?.message || '');
        // The backend rejects a chat ID that belongs to another project before
        // saving or running anything. Recover by retrying this exact request
        // once in a new chat scoped to the active project.
        if (requestError?.payload?.status !== 422 || !errorMessage.toLowerCase().includes('different project')) {
          throw requestError;
        }
        const activeSessions = await apiClient.listSessions();
        setSessions(visibleAgentSessions(activeSessions, projects, currentProject));
        const activeProjectSessions = activeSessions.filter((session) => session.project_id === currentProject);
        const orderedActiveSessions = [...activeProjectSessions].sort(
          (a, b) => Date.parse(b.updated_at || '') - Date.parse(a.updated_at || '')
        );
        let rememberedActiveSession = '';
        try { rememberedActiveSession = localStorage.getItem(projectSessionKey(currentProject)) || ''; } catch { /* optional */ }
        const activeSession = orderedActiveSessions.find((item) => item.session_id === rememberedActiveSession)
          || orderedActiveSessions[0];
        if (activeSession) {
          const savedActiveSession = await apiClient.getSession(activeSession.session_id);
          if (savedActiveSession.project_id !== currentProject) {
            throw new Error('The saved chat list returned a session outside the active project.');
          }
          activeSessionId = savedActiveSession.session_id;
          // The current transcript was already loaded for this project and
          // the just-submitted user message is already appended. Keep it while
          // moving this turn to the correctly scoped session.
        } else {
          activeSessionId = createAgentSessionId(currentProject);
        }
        activityId = globalThis.crypto?.randomUUID?.() || `activity_${Date.now()}_${Math.random().toString(36).slice(2)}`;
        setSessionId(activeSessionId);
        setSessionSaveState('saving');
        setActiveActivityLabel('Opening a fresh chat for this project…');
        try {
          localStorage.removeItem(sessionActivityKey(currentProject, sessionId));
          localStorage.setItem(projectSessionKey(currentProject), activeSessionId);
          localStorage.setItem(sessionActivityKey(currentProject, activeSessionId), activityId);
        } catch { /* the retry still runs without persisted recovery metadata */ }
        chatPayload.session_id = activeSessionId;
        chatPayload.activity_id = activityId;
        response = await apiClient.sendAgentChat(chatPayload);
      }

      assistantReply = response.text || '';
      pageToOpen = response.production_job?.pages?.find((page) =>
        Boolean(page.revision) && ['created', 'assembled', 'needs_attention'].includes(page.status)
      )?.page_id;
      const wroteToCanvas = (response.tool_calls || []).some((call) =>
        call.tool_id === 'canvas.place_panel_artwork' || call.tool_id === 'canvas.assemble_full_page'
      );
      const hasGeneratedAsset = (response.tool_results || []).some((result) =>
        result.tool_id === 'generation.generate_image' && result.status === 'success'
      );
      const placementResult = (response.tool_results || []).find((result) => result.tool_id === 'canvas.place_panel_artwork');
      if (hasGeneratedAsset && placementResult && placementResult.status !== 'success') {
        assistantReply = `${assistantReply}\n\nThe picture was generated, but Canvas could not place it on the page. It is saved in your Library. Open Canvas and retry the placement after resolving the page issue.`;
      } else if (hasGeneratedAsset && !wroteToCanvas && canvasTarget) {
        assistantReply = `${assistantReply}\n\nThe picture was generated, but Canvas did not confirm a placement. It is saved in your Library; check the page before retrying.`;
      } else if (hasGeneratedAsset && !wroteToCanvas && !canvasTarget && canvasTargetNotice) {
        assistantReply = `${assistantReply}\n\n${canvasTargetNotice}`;
      }
      receivedApproval = response.pending_approval;
      setSessionSaveState('saved');

      const responsePendingApproval = response.pending_approval;
      if (responsePendingApproval) {
        setPendingApprovals((prev) => ({
          ...prev,
          [responsePendingApproval.approval_id]: responsePendingApproval,
        }));
      }

      const responseAttachmentDtos = response.attachments;
      if (responseAttachmentDtos && responseAttachmentDtos.length > 0) {
        responseAttachments = responseAttachmentDtos.map((a) => ({
          id: a.attachment_id,
          name: a.filename,
          src: a.asset_id ? apiClient.getAssetFileUrl(a.asset_id) : apiClient.getAgentAttachmentFileUrl(a.attachment_id, currentProject),
          sourceType: a.is_canonical_anchor ? 'canonical_anchor' : 'registered_asset',
          dimensions: a.width && a.height ? { width: a.width, height: a.height } : undefined,
          sizeBytes: a.byte_size,
          sha256: a.content_sha256,
          mimeType: a.mime_type,
          assetId: a.asset_id,
        }));
      }

      if (response.tool_calls && response.tool_calls.length > 0) {
        const resultsByCallId = new Map<string, AgentToolResultDto>();
        if (response.tool_results) {
          for (const res of response.tool_results) {
            resultsByCallId.set(res.call_id, res);
          }
        }

        for (const tc of response.tool_calls) {
          const res = resultsByCallId.get(tc.call_id);
          const isSuccess = res ? res.status === 'success' : false;
          const isGated = res ? res.status === 'gated' : false;
          const isBlocked = res ? res.status === 'blocked' : false;

          let outputSummary = '';
          if (res?.error) {
            outputSummary = `[${res.error_code || 'ERROR'}] ${res.error}`;
          } else if (res?.output) {
            if (typeof res.output === 'string') {
              outputSummary = res.output;
            } else {
              outputSummary = JSON.stringify(res.output, null, 2);
            }
          }

          let relatedAtt: ChatAttachment | undefined;
          if (res?.output && typeof res.output === 'object') {
            const out = res.output as any;
            const assetId = out.asset_id || (out._artifacts && out._artifacts[0]?.asset_id);
            if (assetId || out.url) {
              relatedAtt = {
                id: assetId || tc.call_id,
                name: out.filename || out.logical_filename || `${(tc.arguments as any)?.panel_id || 'panel'}.png`,
                src: out.url || apiClient.getAssetFileUrl(assetId),
                sourceType: 'registered_asset',
                dimensions: out.width && out.height ? { width: out.width, height: out.height } : undefined,
                sizeBytes: out.byte_size,
                sha256: out.content_sha256,
                mimeType: out.mime_type || 'image/png',
                assetId: assetId,
              };
            }
          }
          if (!relatedAtt) {
            relatedAtt = sentAttachments.find(
              (a) => a.id === tc.arguments?.attachment_id || a.name === tc.arguments?.filename
            );
          }

          toolCalls.push({
            callId: tc.call_id,
            toolName: tc.tool_id,
            purpose: toolCatalog[tc.tool_id]?.purpose || tc.tool_id,
            status: isSuccess ? 'succeeded' : isGated ? 'gated' : isBlocked ? 'blocked' : 'failed',
            startedAt: new Date().toISOString(),
            durationMs: res ? Math.round((res.duration_seconds || 0) * 1000) : 0,
            sanitizedInputs: tc.arguments || {},
            outputSummary: outputSummary ? (outputSummary.length > 300 ? outputSummary.slice(0, 300) + '...' : outputSummary) : undefined,
            outputData: res?.output || res?.error,
            relatedImage: relatedAtt,
            approvalId: res?.approval_id || response.pending_approval?.approval_id,
          });
        }
      }

      // Refresh sessions list
      try {
        const sessList = await apiClient.listSessions();
        if (sessList) setSessions(visibleAgentSessions(sessList, projects, currentProject));
      } catch {
        // Fallback
      }
    } catch (err: any) {
      setSessionSaveState('error');
      assistantReply = `**Error contacting InkLoop Agent Coordinator:** ${err.payload?.message || err.message || 'Network request failed'}`;
      showToast({
        type: 'error',
        title: 'Agent Turn Failed',
        message: err.payload?.message || err.message || 'Coordinator communication failed.',
      });
    } finally {
      keepPollingActivity = false;
      if (activityPollTimer) clearTimeout(activityPollTimer);
      try { localStorage.removeItem(sessionActivityKey(currentProject, activeSessionId)); } catch { /* ignore */ }
      setIsProcessing(false);
      setActiveActivityLabel('');
      setActiveProductionJob(null);

      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        persisted: Boolean(response),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: assistantReply,
        modelUsage: response?.model_usage,
        productionJob: response?.production_job,
        pendingStoryAction: response?.pending_story_action,
        attachments: responseAttachments.length > 0 ? responseAttachments : undefined,
        toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
        pendingApproval: receivedApproval,
        activityState: receivedApproval ? 'waiting_approval' : 'idle',
      };

      setMessages((prev) => [...prev, assistantMessage]);
      if (pageToOpen) openCanvasPage(pageToOpen);
    }
  };

  // Starter prompts use the active project's actual cast when one is available.
  const primaryCharacter = projectCharacters.find((character) => selectedCharacterIds.includes(character.id)) || projectCharacters[0];
  const saveStateLabel = sessionSaveState === 'saved' ? 'Saved to this chat' : sessionSaveState === 'saving' ? 'Saving turn…' : sessionSaveState === 'error' ? 'Save failed or unconfirmed' : 'Draft not sent';
  const lastAssistantMessageId = messages[messages.length - 1]?.role === 'assistant'
    ? messages[messages.length - 1].id
    : undefined;
  const latestPageStoryAction = [...messages].reverse()
    .map((message) => message.pendingStoryAction)
    .find((action) => Boolean(action?.page_count));
  const activeQuickStyleTemplateId = styleProfiles.find((profile) => profile.profile_id === selectedStyleProfileId)?.metadata?.quick_style_template_id as string | undefined;

  const applyQuickStyle = async (templateId: string) => {
    setApplyingQuickStyleId(templateId);
    try {
      const profile = await apiClient.applyQuickStyleTemplate(currentProject, templateId);
      setStyleProfiles((current) => [profile, ...current.filter((item) => item.profile_id !== profile.profile_id)]);
      setSelectedStyleProfileId(profile.profile_id);
      localStorage.setItem(`inkloop_agent_style_${currentProject}`, profile.profile_id);
      setQuickStylesOpen(false);
      showToast({ type: 'success', title: 'Style added to Agent', message: `${profile.name} · v${profile.version} is ready to use.` });
    } catch (error: any) {
      showToast({ type: 'error', title: 'Could not add style', message: error?.payload?.message || error?.message || 'The style was not saved.' });
    } finally {
      setApplyingQuickStyleId('');
    }
  };

  const handleToggleCharacter = (charId: string) => {
    setSelectedCharacterIds((prev) => {
      const next = prev.includes(charId) ? prev.filter((id) => id !== charId) : [...prev, charId];
      try {
        if (next.length > 0) {
          localStorage.setItem(`inkloop_agent_characters_${currentProject}`, JSON.stringify(next));
        } else {
          localStorage.removeItem(`inkloop_agent_characters_${currentProject}`);
        }
      } catch { /* ignore */ }
      return next;
    });
  };
  const actionChips = [
    { label: 'Inspect Story', prompt: 'Summarize the active project outline, cast, style, and open story decisions.' },
    { label: 'Check Assets', prompt: 'Review the selected project assets and explain which are ready to use as references.' },
    { label: 'Make a Plan', prompt: 'Draft a six-panel page plan for the current story brief and show any assumptions.' },
    { label: 'Create Image', prompt: `Generate one image${primaryCharacter ? ` featuring ${primaryCharacter.name} (${primaryCharacter.id})` : ' for the current scene'} using the active project's approved visual references.` },
  ];

  const quickFeatureCards = [
    {
      badge: 'Dynamic Layout',
      title: 'Plan a Dynamic Page',
      description: 'Draft a page with varied panel sizes, a clear focal point, and readable flow.',
      prompt: 'Draft a four-panel page plan with varied panel sizes, clear reading flow, and one strong focal panel.',
    },
    {
      badge: 'Expressive Dialogue',
      title: 'Speech & Reaction Bubbles',
      description: 'Plan dialogue and narration with distinct, editable text carriers.',
      prompt: 'Plan a page with editable dialogue and narration, matching each text carrier to the scene tone.',
    },
    {
      badge: 'Story Continuity',
      title: 'Review Project Canon',
      description: 'Check approved character traits, reference links, and visual constraints.',
      prompt: 'Inspect the active Story Bible and summarize approved character traits and linked visual references.',
    },
  ];

  const toggleToolCallExpand = (callId: string) => {
    setExpandedToolCalls((prev) => ({ ...prev, [callId]: !prev[callId] }));
  };

  const openCanvasPage = (pageId: string) => {
    try { localStorage.setItem(`inkloop_active_page_${currentProject}`, pageId); } catch { /* route still opens */ }
    window.location.hash = `#/editor?page=${encodeURIComponent(pageId)}`;
  };

  const getGeneratedArtworkForMessage = (msg: ChatMessage): ChatAttachment[] => {
    const list: ChatAttachment[] = [];
    const seen = new Set<string>();

    const addAttachment = (att: ChatAttachment) => {
      const key = att.assetId || att.id || att.src;
      if (!key || seen.has(key)) return;
      seen.add(key);
      list.push(att);
    };

    // 1. Check tool calls (relatedImage and outputData)
    if (msg.toolCalls) {
      for (const tc of msg.toolCalls) {
        if (tc.relatedImage) {
          addAttachment(tc.relatedImage);
        }
        if (tc.outputData && typeof tc.outputData === 'object') {
          const out = tc.outputData as any;
          const assetId = out.asset_id || out.target_asset_id;
          const fileUrl = out.url || out.preview_url || out.image_url;
          if (assetId || fileUrl) {
            addAttachment({
              id: assetId || tc.callId,
              name: out.filename || out.logical_filename || `${(tc.sanitizedInputs as any)?.panel_id || 'panel'}.png`,
              src: fileUrl || apiClient.getAssetFileUrl(assetId),
              sourceType: 'registered_asset',
              dimensions: out.width && out.height ? { width: out.width, height: out.height } : undefined,
              sizeBytes: out.byte_size,
              sha256: out.content_sha256,
              mimeType: out.mime_type || 'image/png',
              assetId: assetId,
            });
          }
          const artifacts = out._artifacts || out.artifacts || out.panels || out.generated_panels || [];
          if (Array.isArray(artifacts)) {
            for (const art of artifacts) {
              const artAssetId = art.asset_id || (typeof art === 'string' && art.startsWith('art_') ? art : undefined);
              const artUrl = art.url || art.preview_url || (typeof art === 'string' && art.includes('/') ? art : undefined);
              if (artAssetId || artUrl) {
                addAttachment({
                  id: artAssetId || art.filename || String(art),
                  name: art.filename || art.logical_filename || 'artwork.png',
                  src: artUrl || apiClient.getAssetFileUrl(artAssetId!),
                  sourceType: 'registered_asset',
                  dimensions: art.width && art.height ? { width: art.width, height: art.height } : undefined,
                  sizeBytes: art.byte_size,
                  sha256: art.content_sha256 || art.sha256,
                  mimeType: art.mime_type || 'image/png',
                  assetId: artAssetId,
                });
              }
            }
          }
        }
      }
    }

    // 2. Check message attachments (if assistant message)
    if (msg.role === 'assistant' && msg.attachments) {
      for (const att of msg.attachments) {
        const isImg = (att.mimeType && att.mimeType.startsWith('image/')) ||
          att.name.match(/\.(png|jpe?g|webp|gif|svg)$/i);
        if (isImg) {
          addAttachment(att);
        }
      }
    }

    // 3. Check markdown text for ![alt](url), [link](url), and asset IDs (art_*)
    if (msg.text) {
      // 3a. Standard markdown images ![alt](url)
      const mdImgRegex = /!\[(.*?)\]\((.*?)\)/g;
      let m: RegExpExecArray | null;
      while ((m = mdImgRegex.exec(msg.text)) !== null) {
        const alt = m[1];
        const rawUrl = m[2];
        const src = apiClient.getAssetFileUrl(rawUrl);
        const assetId = rawUrl.includes('/assets/')
          ? rawUrl.split('/assets/')[1].split('/')[0]
          : (rawUrl.startsWith('art_') ? rawUrl : undefined);
        addAttachment({
          id: assetId || rawUrl,
          name: alt || 'Generated Artwork',
          src: src,
          sourceType: 'registered_asset',
          assetId: assetId,
        });
      }

      // 3b. Markdown image links [alt](...file)
      const mdLinkRegex = /\[(.*?)\]\((.*?(\.png|\.jpe?g|\.webp|\/file).*?)\)/gi;
      while ((m = mdLinkRegex.exec(msg.text)) !== null) {
        const alt = m[1];
        const rawUrl = m[2];
        const src = apiClient.getAssetFileUrl(rawUrl);
        const assetId = rawUrl.includes('/assets/')
          ? rawUrl.split('/assets/')[1].split('/')[0]
          : (rawUrl.startsWith('art_') ? rawUrl : undefined);
        addAttachment({
          id: assetId || rawUrl,
          name: alt || 'Generated Panel',
          src: src,
          sourceType: 'registered_asset',
          assetId: assetId,
        });
      }

      // 3c. Standalone asset IDs mentioned in text: art_xxxxxxxx or asset_xxxxxxxx
      const assetIdRegex = /\b(art_[a-zA-Z0-9_-]{6,}|asset_[a-zA-Z0-9_-]{6,})\b/g;
      while ((m = assetIdRegex.exec(msg.text)) !== null) {
        const assetId = m[1];
        addAttachment({
          id: assetId,
          name: `${assetId}.png`,
          src: apiClient.getAssetFileUrl(assetId),
          sourceType: 'registered_asset',
          assetId: assetId,
        });
      }
    }

    return list;
  };

  return (
    <div className="agent-studio flex h-full w-full bg-[#141414] text-ink-100 relative overflow-hidden select-text font-sans">
      {/* Background subtle neutral radial vignette */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_50%_15%,rgba(255,255,255,0.02),transparent_70%)] -z-10" />

      {/* =========================================================================
          LEFT SESSIONS SIDEBAR (Zyricon / Beam Dark Style)
         ========================================================================= */}
      <div
        className={`transition-[width] overflow-hidden shrink-0 flex ${
          sessionSidebarOpen ? 'w-64' : 'w-0'
        }`}
        style={{
          transitionDuration: 'var(--motion-duration-slow)',
          transitionTimingFunction: 'var(--motion-ease-standard)',
        }}
        aria-hidden={!sessionSidebarOpen}
      >
        <aside className="w-64 shrink-0 border-r border-white/5 bg-[#191919]/90 backdrop-blur-xl flex flex-col justify-between p-4 z-20 h-full">
          <div className="space-y-4">
            {/* Header / Brand */}
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <div className="flex items-center gap-2.5">
                <TabCharacterIcon tab="agent" size={34} />
                <div>
                  <span className="text-xs font-bold text-white tracking-tight block">InkLoop Agent</span>
                  <span className="text-[10px] text-ink-400 font-mono">S9 Coordinator v1</span>
                </div>
              </div>
              <button
                onClick={() => setSessionSidebarOpen(false)}
                className="text-ink-400 hover:text-white p-1 rounded-md hover:bg-white/5"
                title="Collapse Sidebar"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* + New Chat Button */}
            <button
              onClick={handleNewChat}
              className="w-full py-2.5 px-3.5 rounded-xl bg-white/[0.04] hover:bg-white/10 border border-white/10 hover:border-white/20 text-white text-xs font-medium flex items-center gap-2.5 transition-all group shadow-sm"
            >
              <Plus className="w-4 h-4 text-ink-300 group-hover:text-white" />
              <span>New Conversation</span>
            </button>

            {/* Features Navigation */}
            <div className="space-y-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-500 block px-2 mb-1">
                Features
              </span>
              <button
                onClick={() => {}}
                className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs bg-white/10 text-white font-medium border border-white/15"
              >
                <MessageSquare className="w-3.5 h-3.5 text-white" />
                <span>Chat Transcript</span>
              </button>
              <button
                onClick={() => setAssetPickerOpen(true)}
                className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs text-ink-400 hover:text-white hover:bg-white/5 transition-colors"
              >
                <Database className="w-3.5 h-3.5 text-ink-400" />
                <span>Asset Library</span>
              </button>
            </div>

            {/* Recent Sessions List */}
            <div className="space-y-1 pt-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-500 block px-2 mb-1">
                Recent Sessions
              </span>
              <div className="space-y-1 max-h-[45vh] overflow-y-auto pr-1">
                {loadingSessions ? (
                  <p className="text-[11px] text-ink-500 px-2 italic">Loading saved chats…</p>
                ) : sessions.length === 0 ? (
                  <p className="text-[11px] text-ink-500 px-2 italic">{isProcessing ? 'Saving this chat…' : 'No saved chats yet'}</p>
                ) : (
                  sessions.map((s) => (
                    <button
                      key={s.session_id}
                      onClick={() => handleSelectSession(s.session_id)}
                      className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-all flex items-center gap-2 ${
                        s.session_id === sessionId
                          ? 'bg-white/10 text-white border border-white/20'
                          : 'text-ink-400 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      <History className="w-3 h-3 shrink-0 text-ink-500" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{s.title || s.session_id}</span>
                        <span className="block truncate text-[10px] text-ink-500">
                          {isProcessing && s.session_id === sessionId
                            ? 'Working…'
                            : projects.find((project) => project.project_id === s.project_id)?.title || s.project_id}
                        </span>
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Bottom Project & Budget Card */}
          <div className="p-3 rounded-xl bg-ink-900/80 border border-white/5 space-y-1.5 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-ink-400">Project:</span>
              <span className="font-semibold text-white truncate max-w-[120px]">{currentProject}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-ink-400">Available:</span>
              <span className="font-mono text-emerald-400 font-semibold">
                ${budgetData?.remaining_budget_usd != null ? Number(budgetData.remaining_budget_usd).toFixed(2) : '10.00'}
              </span>
            </div>
          </div>
        </aside>
      </div>

      {/* =========================================================================
          MAIN CHAT CONTAINER
         ========================================================================= */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Navbar Header */}
        <div className="shrink-0 flex items-center justify-between px-5 py-3 border-b border-white/5 bg-[#141414]/80 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            {!sessionSidebarOpen && (
              <button
                onClick={() => setSessionSidebarOpen(true)}
                className="p-1.5 rounded-lg bg-ink-900 text-ink-400 hover:text-white border border-white/5 transition-colors"
                title="Open Sessions Sidebar"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/[0.03] border border-white/10 text-xs text-ink-300">
              <TabCharacterIcon tab="agent" size={16} />
              <span className={`w-2 h-2 rounded-full ${coordinatorConnected ? 'bg-emerald-400' : 'bg-rose-400'}`} />
              <span className="font-mono text-white">InkLoop S9 Coordinator</span>
              <span className="text-ink-500">•</span>
              <span className="text-[11px] text-ink-300 font-mono">v{bibleMetadata.version}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ModelSelector
              selectedModelId={selectedModelId}
              onSelectModel={handleSelectModel}
              agentMode={agentMode}
              coordinatorConnected={coordinatorConnected}
            />
          </div>
        </div>

        {/* Scrollable Conversation View */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
          {messages.length === 0 ? (
            /* =========================================================================
                HERO EMPTY STATE (Exact match to Zyricon / Jason UI Reference)
               ========================================================================= */
            <div className="max-w-2xl mx-auto py-10 flex flex-col items-center text-center space-y-6 animate-in fade-in duration-300">
              {/* Technical Studio Station Emblem */}
              <div className="relative flex items-center justify-center pt-2">
                <div className="hover:scale-110 transition-transform duration-300 cursor-pointer">
                  <AgentCharacter animation="anim-wave-loop" theme="ink-dark" size={108} showFurTexture showGroundShadow={false} />
                </div>
              </div>

              {/* Title & Subtitle */}
              <div className="space-y-1.5">
                <h2 className="text-2xl font-semibold tracking-tight text-white font-sans">
                  InkLoop Production Orchestrator
                </h2>
                <p className="text-xs text-ink-400 max-w-md mx-auto leading-relaxed">
                  Multimodal comic studio engine for story bible consistency, layout planning, and lettering generation.
                </p>
              </div>

              {/* Action Chips */}
              <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                {actionChips.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(chip.prompt)}
                    className="px-3.5 py-1.5 rounded-full bg-white/[0.04] hover:bg-white/10 border border-white/10 hover:border-white/20 text-xs text-ink-200 hover:text-white transition-all shadow-sm flex items-center gap-1.5"
                  >
                    <span>{chip.label}</span>
                  </button>
                ))}
              </div>

              {/* Centered Prompt Composer */}
              <div className="w-full max-w-xl mx-auto pt-2">
                <div className="relative rounded-2xl bg-[#1d1d1d] border border-white/10 focus-within:border-white/30 focus-within:shadow-[0_0_20px_rgba(0,0,0,0.5)] transition-all p-3 text-left">
                  <div className="agent-character-picker">
                    {projectCharacters.length > 0 && <><span>Use characters</span>{projectCharacters.map((character) => <button key={character.id} type="button" aria-pressed={selectedCharacterIds.includes(character.id)} className={selectedCharacterIds.includes(character.id) ? 'selected' : ''} onClick={() => handleToggleCharacter(character.id)}>{character.name}</button>)}</>}
                    {styleProfiles.length > 0 && <label className="flex items-center gap-2 text-[11px] text-ink-400">Style<select aria-label="Agent style context" className="rounded bg-ink-900 border border-white/10 px-2 py-1 text-ink-100" value={selectedStyleProfileId} onChange={(event) => setSelectedStyleProfileId(event.target.value)}><option value="">Project default</option>{styleProfiles.map((profile) => <option key={profile.profile_id} value={profile.profile_id}>{profile.name} · v{profile.version}</option>)}</select></label>}
                    {locations.length > 0 && <label className="flex items-center gap-2 text-[11px] text-ink-400">Location<select aria-label="Agent location context" className="rounded bg-ink-900 border border-white/10 px-2 py-1 text-ink-100" value={selectedLocationId} onChange={(event) => setSelectedLocationId(event.target.value)}><option value="">No location selected</option>{locations.map((location) => <option key={location.location_id} value={location.location_id}>{location.name} · v{location.version}</option>)}</select></label>}
                  </div>
                  {quickStyleTemplates.length > 0 && (
                    <div className="mt-3">
                      <QuickStylePicker
                        templates={quickStyleTemplates}
                        open={quickStylesOpen}
                        applyingId={applyingQuickStyleId}
                        activeTemplateId={activeQuickStyleTemplateId}
                        onToggle={() => setQuickStylesOpen((open) => !open)}
                        onApply={applyQuickStyle}
                      />
                    </div>
                  )}
                  <div className="py-1 text-[10px] text-ink-500" role="status" aria-live="polite">{saveStateLabel}</div>
                  <textarea
                    value={inputText}
                    onChange={(e) => { setInputText(e.target.value); setSessionSaveState('unsaved'); }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder={isProcessing ? "InkLoop is working on your request…" : "+ Ask Anything..."}
                    rows={2}
                    disabled={isProcessing}
                    className="w-full bg-transparent text-sm text-white placeholder:text-ink-500 focus:outline-none resize-none font-sans disabled:cursor-wait"
                  />

                  {/* Attachment previews */}
                  {attachedFiles.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 py-2 border-t border-white/5">
                      {attachedFiles.map((att) => (
                        <div
                          key={att.id}
                          className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-ink-900 border border-white/10 text-xs text-white"
                        >
                          {att.mimeType?.startsWith('image/') ? <img src={att.src} alt={att.name} className="w-5 h-5 object-cover rounded" /> : <FileText className="w-5 h-5 text-ink-300" />}
                          <span className="max-w-[110px] truncate">{att.name}</span>
                          <button onClick={() => handleRemoveAttachment(att.id)}>
                            <X className="w-3.5 h-3.5 text-ink-400 hover:text-rose-400" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2 border-t border-white/5 mt-1">
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isProcessing}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-ink-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-40"
                      >
                        <Paperclip className="w-3.5 h-3.5" />
                        <span>Attach</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setAssetPickerOpen(true)}
                        disabled={isProcessing}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-ink-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-40"
                      >
                        <Database className="w-3.5 h-3.5" />
                        <span>Library</span>
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-ink-500 hidden sm:inline font-mono">
                        {isProcessing ? (
                          <span className="inline-flex items-center gap-1.5 text-zinc-300">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            InkLoop is working…
                          </span>
                        ) : (
                          'Enter to Send • Shift+Enter for newline'
                        )}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleSendMessage()}
                        disabled={isProcessing || (!inputText.trim() && attachedFiles.length === 0)}
                        aria-label={isProcessing ? 'InkLoop is working' : 'Send message'}
                        aria-busy={isProcessing}
                        title={
                          isProcessing
                            ? 'InkLoop is working on your request...'
                            : (!inputText.trim() && attachedFiles.length === 0)
                            ? 'Enter a prompt or attach a file to send'
                            : 'Send message (Enter)'
                        }
                        className={
                          isProcessing
                            ? 'w-8 h-8 rounded-full bg-white/10 border border-white/20 text-white flex items-center justify-center cursor-wait ring-1 ring-white/10 shadow-sm'
                            : (!inputText.trim() && attachedFiles.length === 0)
                            ? 'w-8 h-8 rounded-full bg-white/20 text-ink-500 cursor-not-allowed flex items-center justify-center transition-all opacity-40'
                            : 'w-8 h-8 rounded-full bg-white hover:bg-ink-200 text-black flex items-center justify-center transition-all shadow-sm active:scale-95'
                        }
                      >
                        {isProcessing ? (
                          <Loader2 className="w-4 h-4 animate-spin text-white" />
                        ) : (
                          <ArrowUp className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* 3 Quick Action Starter Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 w-full max-w-xl mx-auto pt-4 text-left">
                {quickFeatureCards.map((card, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleSendMessage(card.prompt)}
                    className="p-3.5 rounded-2xl bg-white/[0.02] hover:bg-white/5 border border-white/5 hover:border-white/15 transition-all cursor-pointer group flex flex-col justify-between space-y-2 shadow-sm"
                  >
                    <div>
                      <span className="inline-block text-[10px] font-medium px-2 py-0.5 rounded-full bg-white/5 text-ink-300 border border-white/10 mb-2">
                        {card.badge}
                      </span>
                      <h4 className="text-xs font-semibold text-white group-hover:text-white transition-colors">
                        {card.title}
                      </h4>
                      <p className="text-[11px] text-ink-400 mt-1 leading-relaxed">{card.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* =========================================================================
                ACTIVE CONVERSATION TRANSCRIPT
               ========================================================================= */
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col space-y-2 motion-slide-up-in ${
                    msg.role === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  {/* Header Tag */}
                  <div className="flex items-center gap-2 px-1 text-[11px] text-ink-400 font-mono">
                    {msg.role === 'user' ? (
                      <>
                        <span>You</span>
                        <span>•</span>
                        <span>{msg.timestamp}</span>
                      </>
                    ) : (
                      <>
                        <span className="text-white font-semibold flex items-center gap-1.5">
                          <AgentCharacter pose="pose-neutral" theme="ink-dark" size={18} />
                          InkLoop Agent
                        </span>
                        <span>•</span>
                        <span>{msg.timestamp}</span>
                      </>
                    )}
                  </div>

                  {/* Message Bubble Card */}
                  <div
                    className={`rounded-2xl p-4 md:p-5 max-w-2xl border transition-all ${
                      msg.role === 'user'
                        ? 'bg-ink-850 text-white border-white/15'
                        : 'bg-[#222222]/90 text-ink-100 border-white/5 shadow-card'
                    }`}
                  >
                    {/* Attached files preview */}
                    {msg.role === 'user' && msg.attachments && msg.attachments.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-3 pb-3 border-b border-white/10">
                        {msg.attachments.map((att) => (
                          <div
                            key={att.id}
                            onClick={() => att.mimeType?.startsWith('image/') &&
                              setLightboxImage({
                                src: att.src,
                                name: att.name,
                                sourceType: att.sourceType,
                                dimensions: att.dimensions,
                                sizeBytes: att.sizeBytes,
                                sha256: att.sha256,
                                mimeType: att.mimeType,
                                assetId: att.assetId,
                              })
                            }
                            className="group relative rounded-lg overflow-hidden border border-white/10 hover:border-white/40 cursor-pointer transition-all bg-ink-950 w-24 h-24 flex items-center justify-center shrink-0"
                          >
                            {att.mimeType?.startsWith('image/') ? <img src={att.src} alt={att.name} className="w-full h-full object-cover" /> : <div className="flex flex-col items-center gap-2 p-2 text-center"><FileText className="w-7 h-7 text-ink-300" /><span className="text-[9px] text-ink-300 break-all">{att.name}</span></div>}
                            <div className="absolute inset-0 bg-ink-950/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-1.5 text-[9px] text-white">
                              <span className="truncate">{att.name}</span>
                              <span className="font-mono text-white/90">Inspect</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {msg.role === 'assistant' && msg.pendingStoryAction && msg.pendingStoryAction.status === 'plan_ready' && !msg.productionJob && (
                      (!msg.pendingStoryAction.page_count || (
                        latestPageStoryAction?.status === 'plan_ready'
                        && latestPageStoryAction.plan_call_id === msg.pendingStoryAction.plan_call_id
                      ))
                    ) && (() => {
                      const action = msg.pendingStoryAction!;
                      const blueprint = action.plan?.story_blueprint;
                      const planPages = Array.isArray(blueprint?.pages) ? blueprint.pages : [];
                      const totalPanels = action.total_panel_count ?? action.panel_count;
                      const pageCount = action.page_count ?? (planPages.length || 1);
                      const panelCounts = action.page_panel_counts || action.plan?.page_panel_counts || {};
                      const cost = action.estimated_cost_usd;
                      return (
                        <div className="mb-4 rounded-xl border border-white/10 bg-ink-950/80 overflow-hidden text-xs">
                          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white/[0.02]">
                            <div className="flex items-center gap-2.5 min-w-0">
                              <Layers className="h-4 w-4 text-zinc-300 shrink-0" aria-hidden="true" />
                              <div className="min-w-0">
                                <span className="font-semibold text-white block truncate">
                                  Story plan ready: {blueprint?.title || action.source_title}
                                </span>
                                <span className="text-[10px] text-zinc-400 block">
                                  {pageCount} {pageCount === 1 ? 'page' : 'pages'} · {totalPanels} planned panels
                                  {cost != null ? ` · estimated $${cost.toFixed(2)}` : ' · cost estimate unavailable'}
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                disabled={isProcessing}
                                onClick={() => handleSendMessage('skip')}
                                className="inline-flex shrink-0 items-center rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-white/5 transition-colors disabled:opacity-40"
                              >
                                Skip
                              </button>
                              <button
                                type="button"
                                disabled={isProcessing}
                                onClick={() => handleSendMessage('start')}
                                className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 transition-colors shadow-sm disabled:opacity-40"
                              >
                                <Sparkles className="h-3.5 w-3.5 text-black" aria-hidden="true" />
                                Start
                              </button>
                            </div>
                          </div>
                          {planPages.length > 0 && (
                            <div className="max-h-56 overflow-y-auto divide-y divide-white/5 px-3">
                              {planPages.map((page: any, index: number) => {
                                const number = Number(page.page_number || index + 1);
                                const count = Number(page.panel_count ?? panelCounts[String(number)] ?? 0);
                                return (
                                  <div key={`story-page-${number}`} className="flex gap-3 py-2">
                                    <span className="w-24 shrink-0 font-mono text-zinc-500">Page {number} · {count} panels</span>
                                    <span className="min-w-0 text-zinc-300">
                                      <span className="block">{page.summary || 'Story beat planned'}</span>
                                      {page.beats?.length > 0 && (
                                        <span className="mt-1 block text-[10px] text-zinc-500">
                                          {page.beats.map((beat: any) => {
                                            const textPlan = beat.text || {};
                                            const kind = textPlan.content_kind;
                                            const line = textPlan.text_content?.trim();
                                            const label = kind === 'spoken_dialogue' || kind === 'emotional_speech'
                                              ? (textPlan.speaker_name || 'Dialogue')
                                              : kind === 'internal_thought' ? 'Thought'
                                                : kind === 'narration' || kind === 'date_or_place' ? 'Caption'
                                                  : kind === 'sfx' ? 'SFX' : '';
                                            return line ? `${beat.story_event} — ${label}: “${line}”` : beat.story_event;
                                          }).join(' · ')}
                                        </span>
                                      )}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                          {(action.assumptions || blueprint?.assumptions || []).length > 0 && (
                            <div className="border-t border-white/5 px-3 py-2 text-[10px] text-zinc-500">
                              Assumptions: {(action.assumptions || blueprint?.assumptions || []).join(' · ')}
                            </div>
                          )}
                          {Array.isArray(action.plan?.story_local_cast) && action.plan.story_local_cast.length > 0 && (
                            <div className="border-t border-white/5 px-3 py-2 text-[10px] text-zinc-500">
                              Story-local cast for this plan only; nothing was added to Canon.
                            </div>
                          )}
                        </div>
                      );
                    })()}

                    {msg.role === 'assistant' && msg.productionJob && (() => {
                      const job = msg.productionJob;
                      const panelRows = Object.values(job.panels || {}).sort((a, b) => a.page_number - b.page_number || a.panel_id.localeCompare(b.panel_id));
                      const placedCount = panelRows.filter((panel) => panel.status === 'placed').length;
                      const verifiedPageCount = (job.pages || []).filter((page) => page.status === 'assembled' && page.verification?.passed === true).length;
                      const targetPageCount = job.target_page_count ?? job.pages.length;
                      const statusLabels: Record<string, string> = {
                        preflight: 'Checking tools and project context',
                        generating: 'Generating panel artwork',
                        assembling: 'Assembling Canvas pages',
                        verifying: 'Checking saved pages',
                        needs_attention: 'Needs attention',
                        completed: 'Ready in Canvas',
                        failed: 'Production failed',
                      };
                      const openablePages = (job.pages || []).filter((page) =>
                        Boolean(page.revision) && ['created', 'assembled', 'needs_attention'].includes(page.status)
                      );
                      const isCompleted = job.status === 'completed';
                      return (
                        <div className="mb-4 rounded-xl border border-white/10 bg-ink-950/80 overflow-hidden text-xs">
                          {/* Tool Call Header */}
                          <div className="flex items-center justify-between p-2.5 bg-white/[0.02] border-b border-white/5">
                            <div className="flex items-center gap-2">
                              <Layers className="w-3.5 h-3.5 text-zinc-300 shrink-0" aria-hidden="true" />
                              <div>
                                <span className="font-semibold text-white">Story Production Pipeline</span>
                                <span className="text-[9px] text-zinc-500 block font-mono">pipeline.story_production</span>
                                <span className="text-[9px] text-zinc-400 block">
                                  Job {job.job_id} · {verifiedPageCount}/{targetPageCount} pages verified · {placedCount}/{panelRows.length} panels placed · {job.stage?.replaceAll('_', ' ') || statusLabels[job.status] || job.status}
                                </span>
                                {job.goal && <span className="text-[9px] text-zinc-500 block">Goal: {job.goal}</span>}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-mono text-zinc-300">
                                {isCompleted ? 'COMPLETED' : job.status.toUpperCase()}
                              </span>
                              {!isCompleted && (
                                <button
                                  type="button"
                                  disabled={isProcessing}
                                  onClick={() => handleSendMessage('Continue production')}
                                  className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-zinc-200 hover:bg-white/10 transition-colors disabled:opacity-40"
                                >
                                  Resume
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Tool Call Content / Results */}
                          <div className="p-3 space-y-3">
                            {job.export_download_url && (
                              <div className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-white">
                                <div className="flex items-center gap-2 min-w-0">
                                  <FileText className="h-4 w-4 text-zinc-300 shrink-0" aria-hidden="true" />
                                  <div className="min-w-0">
                                    <p className="text-[11px] font-medium text-white">Print-Ready Comic Book Ready</p>
                                    <p className="text-[10px] text-zinc-400">PDF compiled with 300 DPI composite pages</p>
                                  </div>
                                </div>
                                <a
                                  href={job.export_download_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  download={`comic_book_${job.job_id}.pdf`}
                                  className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-[11px] font-medium text-black hover:bg-zinc-200 transition-colors shadow-sm"
                                >
                                  <Download className="h-3.5 w-3.5" aria-hidden="true" />
                                  Download PDF
                                </a>
                              </div>
                            )}

                            {openablePages.length > 0 && (
                              <div className="flex flex-wrap gap-2">
                                {openablePages.map((page) => (
                                  <div key={page.page_id} className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 p-1">
                                    <button
                                      type="button"
                                      onClick={() => openCanvasPage(page.page_id)}
                                      className="inline-flex items-center gap-1.5 rounded-md bg-white px-2.5 py-1 text-[11px] font-medium text-black hover:bg-zinc-200 transition-colors"
                                    >
                                      <FolderOpen className="h-3 w-3" aria-hidden="true" />
                                      Open page {page.page_number} · rev {page.revision}
                                    </button>
                                    {page.composite_image_url && (
                                      <a
                                        href={page.composite_image_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-[10px] font-medium text-zinc-300 hover:bg-white/10 hover:text-white transition-colors"
                                        title="Open 300 DPI composite preview"
                                      >
                                        Composite
                                      </a>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                            {panelRows.length > 0 && (
                              <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                                {panelRows.map((panel) => (
                                  <div key={panel.panel_id} className="flex min-w-0 items-center justify-between gap-1 rounded-md border border-white/5 bg-black/40 px-2 py-1 text-[10px]">
                                    <span className="truncate font-mono text-zinc-300">{panel.panel_id}</span>
                                    <span className={panel.status === 'placed' ? 'text-zinc-200 font-medium' : ['failed', 'needs_attention'].includes(panel.status) ? 'text-zinc-400' : 'text-zinc-600'}>
                                      {panel.status.replaceAll('_', ' ')}
                                    </span>
                                    {['failed', 'needs_attention'].includes(panel.status) && (
                                      <button
                                        type="button"
                                        disabled={isProcessing}
                                        onClick={() => handleSendMessage(`Retry panel ${panel.panel_id}`)}
                                        className="shrink-0 rounded border border-white/10 px-1.5 py-0.5 text-zinc-200 hover:bg-white/10 transition-colors disabled:opacity-40"
                                      >Retry</button>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                            {job.errors?.length > 0 && (
                              <ul className="list-disc space-y-1 pl-4 text-[10px] text-zinc-400">
                                {[...new Set(job.errors)].slice(0, 4).map((error, index) => <li key={`${index}-${error}`}>{error}</li>)}
                              </ul>
                            )}
                          </div>
                        </div>
                      );
                    })()}

                    {/* First-Class Tool Calls */}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className="space-y-2 mb-3.5">
                        <div className="flex items-center gap-2 px-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                          <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                          Actions called ({msg.toolCalls.length})
                        </div>
                        {msg.toolCalls.map((tc) => {
                          const isExpanded = expandedToolCalls[tc.callId] || false;
                          const isSucceeded = tc.status === 'succeeded';
                          const isGated = tc.status === 'gated';
                          const isBlocked = tc.status === 'blocked';
                          const toolDefinition = toolCatalog[tc.toolName];
                          const StepIcon = getToolIcon(toolDefinition);
                          const actionLabel = getToolLabel(tc.toolName, toolCatalog);

                          return (
                            <div
                              key={tc.callId}
                              className="rounded-xl border border-white/5 bg-ink-950/80 overflow-hidden text-xs motion-slide-up-in"
                            >
                              <div
                                onClick={() => toggleToolCallExpand(tc.callId)}
                                role="button"
                                tabIndex={0}
                                aria-expanded={isExpanded}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter' || event.key === ' ') {
                                    event.preventDefault();
                                    toggleToolCallExpand(tc.callId);
                                  }
                                }}
                                className="flex items-center justify-between p-2.5 hover:bg-white/[0.02] cursor-pointer transition-colors"
                              >
                                <div className="flex items-center gap-2">
                                  <StepIcon className="w-3.5 h-3.5 text-zinc-300 shrink-0" aria-hidden="true" />
                                  <div>
                                    <span className="font-semibold text-white">{actionLabel}</span>
                                    <span className="text-[9px] text-zinc-500 block font-mono">{tc.toolName}</span>
                                    <span className="text-[9px] text-zinc-500 block">{toolDefinition?.purpose || tc.purpose || tc.toolName}</span>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2">
                                  <Badge
                                    variant={isSucceeded ? 'success' : isGated ? 'simulated' : 'danger'}
                                    size="sm"
                                  >
                                    {isBlocked ? 'BLOCKED' : tc.status.toUpperCase()}
                                  </Badge>
                                  {isExpanded ? (
                                    <ChevronDown className="w-3.5 h-3.5 text-ink-500" />
                                  ) : (
                                    <ChevronRight className="w-3.5 h-3.5 text-ink-500" />
                                  )}
                                </div>
                              </div>

                              {/* Expanded Tool Call Details */}
                              {isExpanded && (
                                <div className="p-3 border-t border-white/5 space-y-2.5 bg-ink-900/40 text-[11px]">
                                  <div className="font-mono text-[10px] text-zinc-500">
                                    Tool: {tc.toolName}{tc.durationMs !== undefined ? ` · ${tc.durationMs} ms` : ''}
                                  </div>
                                  <div>
                                    <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-500 block mb-1">
                                      Sanitized Inputs
                                    </span>
                                    <pre className="p-2 rounded bg-ink-950 font-mono text-ink-300 overflow-x-auto text-[10px]">
                                      {JSON.stringify(tc.sanitizedInputs, null, 2)}
                                    </pre>
                                  </div>

                                  {tc.outputSummary && (
                                    <div>
                                      <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-500 block mb-1">
                                        Result Summary
                                      </span>
                                      <p className="font-mono text-ink-200">{tc.outputSummary}</p>
                                    </div>
                                  )}

                                  {tc.outputData && typeof tc.outputData === 'object' && (tc.outputData as any).page_id && (
                                    <div className="mt-2 p-2.5 rounded-lg border border-white/10 bg-white/[0.03] flex items-center justify-between">
                                      <div className="flex items-center gap-2">
                                        <span className="text-white font-mono font-medium">Page {(tc.outputData as any).page_id}</span>
                                        {(tc.outputData as any).layout_template && (
                                          <span className="text-[10px] text-ink-400 font-mono">({(tc.outputData as any).layout_template})</span>
                                        )}
                                        <span className="text-[10px] text-ink-500">rev {(tc.outputData as any).revision}</span>
                                      </div>
                                      <button
                                        onClick={() => {
                                          const pid = (tc.outputData as any).page_id;
                                          openCanvasPage(pid);
                                          showToast({ type: 'success', title: 'Page Selected', message: `Opened page ${pid} in Canvas Editor` });
                                        }}
                                        className="px-2.5 py-1 rounded bg-white text-ink-950 font-medium text-[11px] hover:bg-ink-100 transition-colors flex items-center gap-1.5 shadow-sm"
                                      >
                                        Open in Canvas Editor
                                      </button>
                                    </div>
                                  )}

                                  {tc.relatedImage && (
                                    <div className="flex items-center gap-3 pt-1">
                                      <img
                                        src={tc.relatedImage.src}
                                        alt={tc.relatedImage.name}
                                        onClick={() => setLightboxImage(tc.relatedImage as LightboxImage)}
                                        className="w-12 h-12 object-cover rounded border border-white/10 cursor-pointer hover:border-white/40"
                                      />
                                      <div>
                                        <span className="font-semibold text-white block">
                                          {tc.relatedImage.name}
                                        </span>
                                        <span className="text-ink-500 font-mono text-[10px]">
                                          SHA: {tc.relatedImage.sha256?.slice(0, 16)}...
                                        </span>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Interactive Human Approval Card */}
                    {msg.pendingApproval && (
                      <div className="mb-4 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 space-y-2.5">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
                            <span className="font-semibold text-amber-200 text-xs">Human Approval Required</span>
                          </div>
                          <Badge variant="warning" size="sm">
                            {msg.pendingApproval.status}
                          </Badge>
                        </div>
                        <p className="text-[11px] text-ink-200 leading-relaxed">
                          {msg.pendingApproval.consequence}
                        </p>
                        <div className="flex items-center gap-2 pt-1">
                          <button
                            onClick={() => handleDecision(msg.pendingApproval!.approval_id, 'APPROVE')}
                            disabled={decidingApprovalId === msg.pendingApproval!.approval_id || msg.pendingApproval.status !== 'PENDING'}
                            className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-xs flex items-center gap-1.5 shadow-sm transition-all"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Approve & Execute</span>
                          </button>
                          <button
                            onClick={() => handleDecision(msg.pendingApproval!.approval_id, 'REJECT')}
                            disabled={decidingApprovalId === msg.pendingApproval!.approval_id || msg.pendingApproval.status !== 'PENDING'}
                            className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-rose-600/30 text-rose-300 disabled:opacity-50 font-medium text-xs flex items-center gap-1.5 border border-white/10 transition-all"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Prominent Generated Artwork Gallery */}
                    {(() => {
                      const generatedImages = msg.role === 'assistant' ? getGeneratedArtworkForMessage(msg) : [];
                      if (generatedImages.length === 0) return null;

                      return (
                        <div className="mb-4 rounded-xl border border-white/10 bg-black/40 p-3 space-y-2.5 shadow-lg">
                          <div className="flex items-center justify-between text-xs pb-1.5 border-b border-white/5">
                            <div className="flex items-center gap-2">
                              <FileImage className="w-4 h-4 text-white" />
                              <span className="font-semibold text-white">Generated Artwork</span>
                            </div>
                            <span className="text-[10px] font-mono text-ink-300 bg-white/5 border border-white/10 px-2 py-0.5 rounded">
                              {generatedImages.length} {generatedImages.length === 1 ? 'panel' : 'panels'}
                            </span>
                          </div>

                          <div
                            className={`grid gap-3 ${
                              generatedImages.length === 1
                                ? 'grid-cols-1'
                                : generatedImages.length === 2
                                ? 'grid-cols-1 sm:grid-cols-2'
                                : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
                            }`}
                          >
                            {generatedImages.map((imgItem, idx) => (
                              <div
                                key={`${imgItem.id}_${idx}`}
                                onClick={() =>
                                  setLightboxImage({
                                    src: imgItem.src,
                                    name: imgItem.name,
                                    sourceType: imgItem.sourceType,
                                    dimensions: imgItem.dimensions,
                                    sizeBytes: imgItem.sizeBytes,
                                    sha256: imgItem.sha256,
                                    mimeType: imgItem.mimeType,
                                    assetId: imgItem.assetId,
                                  })
                                }
                                className="group relative rounded-xl overflow-hidden border border-white/10 bg-ink-950 p-2 cursor-pointer hover:border-white/30 transition-all shadow-md flex flex-col justify-between"
                              >
                                <div className="relative rounded-lg overflow-hidden bg-black/60 flex items-center justify-center min-h-[160px] max-h-[340px]">
                                  <img
                                    src={imgItem.src}
                                    alt={imgItem.name}
                                    decoding="async"
                                    onError={(e) => {
                                      const target = e.currentTarget;
                                      if (imgItem.assetId && !target.src.includes(imgItem.assetId)) {
                                        target.src = apiClient.getAssetFileUrl(imgItem.assetId);
                                      }
                                    }}
                                    className="w-full h-auto max-h-[320px] object-contain rounded transition-transform duration-300 group-hover:scale-[1.02]"
                                  />
                                </div>
                                <div className="mt-2.5 flex items-center justify-between text-[11px] px-1">
                                  <div className="truncate max-w-[190px]">
                                    <span className="font-semibold text-white block truncate">{imgItem.name}</span>
                                    {imgItem.assetId && (
                                      <span className="text-ink-500 font-mono text-[9px] block">
                                        ID: {imgItem.assetId}
                                      </span>
                                    )}
                                  </div>
                                  <span className="text-ink-400 group-hover:text-white font-mono text-[10px] group-hover:underline shrink-0">
                                    Enlarge ↗
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })()}

                    {/* Main Assistant / User Text */}
                    {msg.role === 'assistant' ? (
                      <MarkdownRenderer
                        content={msg.text}
                        onImageClick={(src, alt) => setLightboxImage({ src, name: alt || 'Artwork', sourceType: 'registered_asset' })}
                      />
                    ) : (
                      <p className="text-xs leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                    )}
                    {msg.role === 'assistant' && msg.modelUsage && (
                      <div className="mt-3 border-t border-white/5 pt-2 text-[9px] font-mono text-zinc-500" aria-label="Model token usage">
                        {msg.modelUsage.status === 'unavailable'
                          ? `Token usage not reported · ${msg.modelUsage.model_calls} model call${msg.modelUsage.model_calls === 1 ? '' : 's'}`
                          : `${msg.modelUsage.total_tokens ?? '—'} tokens reported${msg.modelUsage.status === 'partial' ? ' (partial)' : ''} · ${msg.modelUsage.model_calls} model call${msg.modelUsage.model_calls === 1 ? '' : 's'}`}
                      </div>
                    )}
                    {msg.role === 'assistant' && msg.persisted !== false && msg.id === lastAssistantMessageId && (() => {
                      const approvalPending = Boolean(msg.pendingApproval || msg.toolCalls?.some((call) => call.status === 'gated'));
                      return (
                        <div className="mt-3 flex items-center gap-2 border-t border-white/5 pt-2">
                          <button
                            type="button"
                            onClick={handleRetryLastTurn}
                            disabled={isProcessing || approvalPending}
                            title={approvalPending ? 'Resolve the pending approval before retrying.' : 'Run the same saved prompt again. Image generation may use project budget.'}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1.5 text-[11px] text-zinc-300 transition hover:border-white/20 hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            <RefreshCw className="h-3 w-3" aria-hidden="true" />
                            Retry
                          </button>
                          <button
                            type="button"
                            onClick={handleDeleteLastTurn}
                            disabled={isProcessing || approvalPending}
                            title={approvalPending ? 'Resolve the pending approval before deleting this turn.' : 'Remove this prompt and reply from chat. Completed tool actions and assets remain.'}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1.5 text-[11px] text-zinc-400 transition hover:border-rose-400/30 hover:bg-rose-400/10 hover:text-rose-200 disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            <Trash2 className="h-3 w-3" aria-hidden="true" />
                            Delete attempt
                          </button>
                          <span className="ml-auto text-[9px] text-zinc-600">Retry reuses this prompt and its attachments</span>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              ))}

              {/* Working Indicator */}
              {isProcessing && (
                <div className="py-2 px-1 text-xs text-zinc-300 animate-in fade-in">
                  <div className="flex items-center gap-3">
                    <AgentLoader variant="waddle" mode="inline" theme="ink-dark" size={38} message="InkLoop is working" />
                    {activeActivityLabel && <span className="text-[11px] text-zinc-400">{activeActivityLabel}</span>}
                  </div>
                  <div className="mt-2 ml-11 max-w-2xl rounded-xl border border-white/10 bg-black/20 p-3">
                    <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                      <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                      Actions called ({activeToolSteps.length + (activeProductionJob ? 1 : 0)})
                    </div>
                    {activeToolSteps.length > 0 || activeProductionJob ? (
                      <ol aria-label="Agent actions in progress" className="space-y-1.5">
                      {activeToolSteps.map((step) => {
                        const toolDefinition = toolCatalog[step.tool_id];
                        const StepIcon = getToolIcon(toolDefinition);
                        const label = getToolLabel(step.tool_id, toolCatalog);
                        const stateLabel = step.status === 'running' ? 'Working…' : step.status === 'success' ? 'Done' : step.status === 'gated' ? 'Needs your okay' : step.status === 'blocked' ? 'Stopped safely' : 'Could not finish';
                        return (
                          <li key={step.call_id} className="flex items-center justify-between gap-3 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-[11px]">
                            <span className="inline-flex min-w-0 items-center gap-2 text-zinc-200">
                              <StepIcon className="h-3.5 w-3.5 shrink-0 text-zinc-400" aria-hidden="true" />
                              <span className="min-w-0">
                                <span className="block font-medium text-white">{label}</span>
                                <span className="block truncate font-mono text-[9px] text-zinc-500">{step.tool_id}</span>
                                {toolDefinition?.purpose && <span className="block truncate text-[10px] text-zinc-400">{toolDefinition.purpose}</span>}
                              </span>
                            </span>
                            <span className="inline-flex items-center gap-1.5 text-zinc-300 font-mono text-[10px]">
                              {step.status === 'running' && <span className="h-1.5 w-1.5 rounded-full bg-zinc-200 animate-pulse" />}
                              {stateLabel}
                            </span>
                          </li>
                        );
                      })}
                      {activeProductionJob && (() => {
                        const panels = Object.values(activeProductionJob.panels || {}).sort((a, b) => a.page_number - b.page_number || a.panel_id.localeCompare(b.panel_id));
                        const placed = panels.filter((panel) => panel.status === 'placed').length;
                        const currentPanel = panels.find((panel) => ['generating', 'generated', 'pending'].includes(panel.status));
                        const verifiedPages = activeProductionJob.pages.filter((page) => page.status === 'assembled' && page.verification?.passed === true).length;
                        return (
                          <li key="active_story_job" className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5 text-[11px] space-y-2">
                            <div className="flex items-center justify-between gap-3">
                              <span className="inline-flex min-w-0 items-center gap-2 text-zinc-200">
                                <Layers className="h-3.5 w-3.5 shrink-0 text-zinc-400" aria-hidden="true" />
                                <span className="min-w-0">
                                  <span className="block font-medium text-white">Story Production Pipeline</span>
                                  <span className="block truncate font-mono text-[9px] text-zinc-500">pipeline.story_production</span>
                                  <span className="block truncate text-[10px] text-zinc-400">
                                    {verifiedPages}/{activeProductionJob.target_page_count ?? activeProductionJob.pages.length} pages verified · {placed}/{panels.length} panels placed · {activeProductionJob.stage?.replaceAll('_', ' ') || activeProductionJob.status.replaceAll('_', ' ')}
                                  </span>
                                  {currentPanel && <span className="block truncate text-[10px] text-zinc-500">Current: page {currentPanel.page_number} · {currentPanel.panel_id}</span>}
                                </span>
                              </span>
                              <span className="inline-flex items-center gap-1.5 text-zinc-300 font-mono text-[10px]">
                                <span className="h-1.5 w-1.5 rounded-full bg-zinc-200 animate-pulse" />
                                {activeProductionJob.status === 'generating' ? 'Working…' : activeProductionJob.status.replaceAll('_', ' ')}
                              </span>
                            </div>

                            {panels.length > 0 && (
                              <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-6 pt-0.5">
                                {panels.map((panel) => (
                                  <div key={panel.panel_id} className="flex items-center justify-between gap-1 rounded border border-white/5 bg-black/40 px-1.5 py-1 text-[9px]">
                                    <span className="truncate font-mono text-zinc-300">{panel.panel_id}</span>
                                    <span className={panel.status === 'placed' ? 'text-zinc-200 font-medium' : ['failed', 'needs_attention'].includes(panel.status) ? 'text-zinc-400' : 'text-zinc-600'}>
                                      {panel.status.replaceAll('_', ' ')}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {activeProductionJob.pages.filter((page) => Boolean(page.revision) && ['created', 'assembled', 'needs_attention'].includes(page.status)).length > 0 && (
                              <div className="flex flex-wrap gap-2 pt-0.5">
                                {activeProductionJob.pages.filter((page) => Boolean(page.revision) && ['created', 'assembled', 'needs_attention'].includes(page.status)).map((page) => (
                                  <button
                                    key={page.page_id}
                                    type="button"
                                    onClick={() => openCanvasPage(page.page_id)}
                                    className="inline-flex items-center gap-1 rounded border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-zinc-200 hover:bg-white/10 hover:text-white transition-colors"
                                  >
                                    <FolderOpen className="h-3 w-3 text-zinc-400" aria-hidden="true" />
                                    Open page {page.page_number}
                                  </button>
                                ))}
                              </div>
                            )}
                          </li>
                        );
                      })()}
                      </ol>
                    ) : (
                      <p className="text-[11px] text-zinc-500">The Agent is preparing your request. Real tool calls will appear here as they start.</p>
                    )}
                  </div>
                </div>
              )}

              <div ref={transcriptBottomRef} />
            </div>
          )}
        </div>

        {/* Floating Bottom Composer when messages exist */}
        {messages.length > 0 && (
          <div className="shrink-0 p-4 border-t border-white/5 bg-[#141414]/90 backdrop-blur-md">
            <div className="max-w-3xl mx-auto space-y-2">
              {attachedFiles.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 pb-1">
                  {attachedFiles.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-ink-900 border border-white/10 text-xs text-white"
                    >
                      {att.mimeType?.startsWith('image/') ? <img src={att.src} alt={att.name} className="w-5 h-5 object-cover rounded" /> : <FileText className="w-5 h-5 text-ink-300" />}
                      <span className="max-w-[120px] truncate">{att.name}</span>
                      <button onClick={() => handleRemoveAttachment(att.id)}>
                        <X className="w-3.5 h-3.5 text-ink-400 hover:text-rose-400" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="relative rounded-2xl bg-[#222222]/90 border border-white/10 focus-within:border-white/30 transition-all p-3">
                {isProcessing && (
                  <div
                    className="mb-2 flex min-h-11 items-center gap-3 rounded-xl border border-white/10 bg-black/30 px-3 py-2"
                    role="status"
                    aria-live="polite"
                    aria-label="InkLoop Agent is working"
                  >
                    <AgentLoader variant="waddle" mode="inline" theme="ink-dark" size={30} message="InkLoop is working" />
                    <span className="min-w-0 flex-1 truncate text-[11px] text-zinc-400">
                      {activeActivityLabel || (activeToolSteps.length > 0 ? 'Executing your request…' : 'Preparing your request…')}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] text-zinc-500">
                      <span className="h-1.5 w-1.5 rounded-full bg-zinc-200 animate-pulse" />
                      {activeToolSteps.length > 0 ? `${activeToolSteps.length} action${activeToolSteps.length === 1 ? '' : 's'}` : 'Working'}
                    </span>
                  </div>
                )}
                <div className="agent-character-picker">
                  {projectCharacters.length > 0 && <><span>Use characters</span>{projectCharacters.map((character) => <button key={character.id} type="button" aria-pressed={selectedCharacterIds.includes(character.id)} className={selectedCharacterIds.includes(character.id) ? 'selected' : ''} onClick={() => handleToggleCharacter(character.id)}>{character.name}</button>)}</>}
                  {styleProfiles.length > 0 && <label className="flex items-center gap-2 text-[11px] text-ink-400">Style<select aria-label="Agent style context" className="rounded bg-ink-900 border border-white/10 px-2 py-1 text-ink-100" value={selectedStyleProfileId} onChange={(event) => setSelectedStyleProfileId(event.target.value)}><option value="">Project default</option>{styleProfiles.map((profile) => <option key={profile.profile_id} value={profile.profile_id}>{profile.name} · v{profile.version}</option>)}</select></label>}
                  {locations.length > 0 && <label className="flex items-center gap-2 text-[11px] text-ink-400">Location<select aria-label="Agent location context" className="rounded bg-ink-900 border border-white/10 px-2 py-1 text-ink-100" value={selectedLocationId} onChange={(event) => setSelectedLocationId(event.target.value)}><option value="">No location selected</option>{locations.map((location) => <option key={location.location_id} value={location.location_id}>{location.name} · v{location.version}</option>)}</select></label>}
                </div>
                {quickStyleTemplates.length > 0 && (
                  <div className="mt-3">
                    <QuickStylePicker
                      templates={quickStyleTemplates}
                      open={quickStylesOpen}
                      applyingId={applyingQuickStyleId}
                      activeTemplateId={activeQuickStyleTemplateId}
                      onToggle={() => setQuickStylesOpen((open) => !open)}
                      onApply={applyQuickStyle}
                    />
                  </div>
                )}
                <div className="py-1 text-[10px] text-ink-500" role="status" aria-live="polite">{saveStateLabel}</div>
                <textarea
                  ref={textareaRef}
                  value={inputText}
                  onChange={(e) => { setInputText(e.target.value); setSessionSaveState('unsaved'); }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder={isProcessing ? "InkLoop is working on your request…" : "Ask anything, describe a panel, or attach an image to inspect..."}
                  rows={2}
                  disabled={isProcessing}
                  className="w-full bg-transparent text-sm text-white placeholder:text-ink-500 focus:outline-none resize-none font-sans disabled:cursor-wait"
                />

                <div className="flex items-center justify-between pt-2 border-t border-white/5 mt-1">
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isProcessing}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-ink-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-40"
                    >
                      <Paperclip className="w-3.5 h-3.5" />
                      <span>Attach</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setAssetPickerOpen(true)}
                      disabled={isProcessing}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-ink-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-40"
                    >
                      <Database className="w-3.5 h-3.5" />
                      <span>Library</span>
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-ink-500 hidden sm:inline font-mono">
                      {isProcessing ? (
                        <span className="inline-flex items-center gap-1.5 text-zinc-300">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          InkLoop is working…
                        </span>
                      ) : (
                        'Enter to Send • Shift+Enter for newline'
                      )}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleSendMessage()}
                      disabled={isProcessing || (!inputText.trim() && attachedFiles.length === 0)}
                      aria-label={isProcessing ? 'InkLoop is working' : 'Send message'}
                      aria-busy={isProcessing}
                      title={
                        isProcessing
                          ? 'InkLoop is working on your request...'
                          : (!inputText.trim() && attachedFiles.length === 0)
                          ? 'Enter a prompt or attach a file to send'
                          : 'Send message (Enter)'
                      }
                      className={
                        isProcessing
                          ? 'w-8 h-8 rounded-full bg-white/10 border border-white/20 text-white flex items-center justify-center cursor-wait ring-1 ring-white/10 shadow-sm'
                          : (!inputText.trim() && attachedFiles.length === 0)
                          ? 'w-8 h-8 rounded-full bg-white/20 text-ink-500 cursor-not-allowed flex items-center justify-center transition-all opacity-40'
                          : 'w-8 h-8 rounded-full bg-white hover:bg-ink-200 text-black flex items-center justify-center transition-all shadow-sm active:scale-95'
                      }
                    >
                      {isProcessing ? (
                        <Loader2 className="w-4 h-4 animate-spin text-white" />
                      ) : (
                        <ArrowUp className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,.txt,.md,.pdf,.docx"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Asset Picker Modal */}
      <Modal
        isOpen={assetPickerOpen}
        onClose={() => setAssetPickerOpen(false)}
        title={
          <div className="flex items-center gap-2 text-white">
            <Database className="w-4 h-4 text-ink-400" />
            <span>Select Asset from Project Library</span>
          </div>
        }
        maxWidth="xl"
      >
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {registeredAssets.length === 0 ? (
            <div className="p-6 text-center text-ink-400 text-xs">
              No registered assets in active project yet.
            </div>
          ) : (
            registeredAssets.map((asset) => (
              <div
                key={asset.asset_id}
                onClick={() => handleAttachRegisteredAsset(asset)}
                className="p-3 rounded-xl bg-ink-900/70 hover:bg-white/5 border border-white/5 hover:border-white/20 cursor-pointer transition-all flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3">
                  <img
                    src={apiClient.getAssetFileUrl(asset.asset_id)}
                    alt={asset.logical_filename}
                    className="w-10 h-10 object-cover rounded border border-white/10 shrink-0"
                  />
                  <div>
                    <h4 className="text-xs font-semibold text-white">{asset.logical_filename}</h4>
                    <p className="text-[10px] font-mono text-ink-400">
                      ID: {asset.asset_id} • SHA: {asset.content_sha256?.slice(0, 12)}...
                    </p>
                  </div>
                </div>
                <Badge variant="neutral" size="sm">
                  {asset.asset_type || 'ASSET'}
                </Badge>
              </div>
            ))
          )}
        </div>
      </Modal>

      {/* High-Resolution Image Lightbox */}
      <ImageLightbox image={lightboxImage} onClose={() => setLightboxImage(null)} />
    </div>
  );
};
