import React, { useState } from 'react';
import {
  Sparkles,
  Camera,
  Layers,
  ShieldCheck,
  Cpu,
  Coins,
  RefreshCw,
  FileCode,
  CheckCircle2,
  AlertCircle,
  Eye,
  Sliders,
  Flame,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface GenerationStudioViewProps {
  currentProject: string;
}

export const GenerationStudioView: React.FC<GenerationStudioViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();

  // Scene parameters
  const [sceneTitle, setSceneTitle] = useState('Scene 1');
  const [shotType, setShotType] = useState('medium close-up');
  const [actionPrompt, setActionPrompt] = useState(
    ''
  );
  const [cameraAngle, setCameraAngle] = useState('eye-level, slight three-quarter view');
  const [lighting, setLighting] = useState('');
  const [panelId, setPanelId] = useState('panel_01');

  // Generation options
  const [isSimulated, setIsSimulated] = useState(false);
  const [maxRetries, setMaxRetries] = useState(2);
  const [spendCap, setSpendCap] = useState(10.0);
  const [requireVerification, setRequireVerification] = useState(true);

  // Results & States
  const [compiledPacket, setCompiledPacket] = useState<any | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [batchResult, setBatchResult] = useState<any | null>(null);

  // Creative Copier Profiles State
  const [styleProfiles, setStyleProfiles] = useState<any[]>([]);
  const [characterProfiles, setCharacterProfiles] = useState<any[]>([]);
  const [selectedStyleId, setSelectedStyleId] = useState<string>('');
  const [selectedCharIds, setSelectedCharIds] = useState<string[]>([]);
  const [creativeResult, setCreativeResult] = useState<any | null>(null);

  const selectedCharacterIds = characterProfiles
    .filter((profile) => selectedCharIds.includes(profile.profile_id))
    .map((profile) => profile.character_id)
    .filter((id): id is string => Boolean(id));
  const displayScore = (value: unknown) => typeof value === 'number' && Number.isFinite(value)
    ? `${Math.round(value <= 1 ? value * 100 : value)}%`
    : 'Not verified';

  React.useEffect(() => {
    apiClient.listStyleProfiles(currentProject).then(setStyleProfiles).catch(() => {});
    apiClient.listCharacterProfiles(currentProject).then(setCharacterProfiles).catch(() => {});
  }, [currentProject]);

  const handleGenerateWithCreativeProfiles = async () => {
    try {
      setGenerating(true);
      setCreativeResult(null);
      const res = await apiClient.generateWithCreativeProfiles(currentProject, {
        scene_action: actionPrompt,
        shot_type: `${shotType}, ${cameraAngle}`,
        style_profile_id: selectedStyleId || undefined,
        character_profile_ids: selectedCharIds.length > 0 ? selectedCharIds : undefined,
        panel_id: panelId,
        lighting_intent: lighting,
      });
      setCreativeResult(res);
      const score = res.qa_result.style_score ?? res.qa_result.overall_score ?? res.qa_result.style_fidelity_score;
      showToast({
        type: res.qa_result.status === 'pass' || res.qa_result.passed === true ? 'success' : 'info',
        title: res.qa_result.status === 'pass' || res.qa_result.passed === true ? 'Creative Generation Complete' : 'Generated; verification unavailable',
        message: `Asset ${res.output_asset_id || res.asset_id} generated. Style verification: ${displayScore(score)}.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Generation Failed', message: err.message });
    } finally {
      setGenerating(false);
    }
  };

  const handleCompileContext = async () => {
    try {
      setCompiling(true);
      const packet = await apiClient.compileContext({
        project_id: currentProject,
        story_id: 'story_01',
        panel_id: panelId,
        scene: {
          scene_id: 'scene_01',
          scene_index: 0,
          title: sceneTitle,
          shot_type: shotType,
          action: actionPrompt,
          camera_angle: cameraAngle,
          lighting,
          character_ids: selectedCharacterIds,
        },
      });
      setCompiledPacket(packet);
      showToast({
        type: 'success',
        title: 'Context Compiled by Pure Code',
        message: `Fingerprint SHA-256: ${packet.context_fingerprint.substring(0, 12)}...`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Context Compilation Failed', message: err.message });
    } finally {
      setCompiling(false);
    }
  };

  const handleDispatchGeneration = async () => {
    try {
      setGenerating(true);
      const summary = await apiClient.startBatch({
        batch_id: `batch_${Date.now()}`,
        project_id: currentProject,
        story_id: 'story_01',
        scenes: [
          {
            scene_id: 'scene_01',
            scene_index: 0,
            title: sceneTitle,
            shot_type: shotType,
            action: actionPrompt,
            camera_angle: cameraAngle,
            lighting,
            character_ids: selectedCharacterIds,
          },
        ],
        model: 'muse-image-1.0',
        max_retries_per_panel: maxRetries,
        spend_cap_usd: spendCap,
        is_simulated: isSimulated,
        require_verification: requireVerification,
      });
      setBatchResult(summary);
      showToast({
        type: 'success',
        title: `Batch Completed: ${summary.status}`,
        message: `${summary.successful_panels} / ${summary.total_panels} panels produced. Verified: ${summary.verified_panels}`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Generation Dispatch Failed', message: err.message });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <TabCharacterIcon tab="studio" size={38} />
            Generation Studio
          </h1>
          <p className="text-xs text-ink-300 mt-1">
            Dispatch generation runs with pure-code context isolation, bounded retries, and multi-tier verification.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCompileContext}
            disabled={compiling || generating}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-medium transition-colors"
          >
            <FileCode className="w-4 h-4 text-ink-400" />
            {compiling ? 'Compiling...' : 'Inspect Compiled Context'}
          </button>
          <button
            onClick={handleDispatchGeneration}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-black hover:bg-ink-200 text-xs font-semibold transition-all disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            {generating ? 'Orchestrating Batch...' : 'Generate Panel'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Directive Inputs */}
        <div className="lg:col-span-2 space-y-5">
          {/* Creative Copier Conditioning Card */}
          <Card
            title="Style & Character Conditioning (Copier Profiles)"
            subtitle="Condition panel generation with learned Style Profile and Character Identity Invariants"
            action={
              <button
                onClick={handleGenerateWithCreativeProfiles}
                disabled={generating}
                className="px-3.5 py-1.5 rounded-lg bg-white text-black hover:bg-ink-200 text-xs font-bold transition-all disabled:opacity-50 flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Generate with Copier Profiles
              </button>
            }
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">
                  Active Style Profile
                </label>
                <select
                  value={selectedStyleId}
                  onChange={(e) => setSelectedStyleId(e.target.value)}
                  className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                >
                  <option value="">-- None (Default Canvas Style) --</option>
                  {styleProfiles.map((p) => (
                    <option key={p.profile_id} value={p.profile_id}>
                      {p.name} (v{p.version}) {p.approved_by_user ? '✓ Approved' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">
                  Character Profile(s)
                </label>
                <select
                  multiple
                  value={selectedCharIds}
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, (option) => option.value);
                    setSelectedCharIds(values);
                  }}
                  className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30 h-20"
                >
                  {characterProfiles.map((c) => (
                    <option key={c.profile_id} value={c.profile_id}>
                      {c.name} ({c.character_id}) {c.approved_by_user ? '✓ Approved' : ''}
                    </option>
                  ))}
                </select>
                <span className="text-[10px] text-ink-400 mt-1 block">
                  Hold Ctrl / Cmd to select multiple characters
                </span>
              </div>
            </div>
          </Card>

          {/* Creative Copier Generation Result Card */}
          {creativeResult && (
            <Card
              title={`Copier Generation Result: ${creativeResult.asset_id}`}
              subtitle={`Panel: ${creativeResult.panel_id} &bull; Scene: ${creativeResult.scene_id}`}
              action={
                <Badge
                  variant={creativeResult.qa_result.passed || creativeResult.qa_result.overall_passed ? 'success' : 'warning'}
                  size="sm"
                >
                  {creativeResult.qa_result.passed || creativeResult.qa_result.overall_passed ? 'QA Passed' : 'QA Attention Needed'}
                </Badge>
              }
            >
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="aspect-square bg-black rounded-xl overflow-hidden border border-white/10 flex items-center justify-center">
                    <img
                      src={apiClient.getAssetFileUrl(creativeResult.output_asset_id || creativeResult.asset_id || '')}
                      alt="Generated Panel Result"
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                  <div className="space-y-3 text-xs">
                    <div className="p-3 rounded-xl bg-ink-950 border border-white/5 space-y-1">
                      <div className="flex justify-between">
                        <span className="text-ink-400">Style Fidelity:</span>
                        <span className="font-mono text-white font-bold">
                          {displayScore(creativeResult.qa_result.style_score ?? creativeResult.qa_result.overall_score ?? creativeResult.qa_result.style_fidelity_score)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-ink-400">Character Fidelity:</span>
                        <span className="font-mono text-white font-bold">
                          {displayScore(creativeResult.qa_result.identity_score ?? creativeResult.qa_result.character_fidelity_score)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-ink-400">Dynamic Variation:</span>
                        <span className="font-mono text-white font-bold">
                          {displayScore(creativeResult.qa_result.variation_score ?? creativeResult.qa_result.dynamic_variation_score)}
                        </span>
                      </div>
                    </div>

                    {creativeResult.qa_result.findings.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-semibold text-ink-400 uppercase tracking-wider block">
                          QA Findings
                        </span>
                        {creativeResult.qa_result.findings.map((f: any, idx: number) => (
                          <div
                            key={idx}
                            className="p-2 rounded bg-ink-950 border border-white/5 text-[11px] text-ink-300"
                          >
                            <span className="font-medium text-white">{f.rule_name}:</span> {f.message}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          )}

          <Card title="Scene & Panel Directives" subtitle="Sequential beat instructions for this comic panel">
            <div className="space-y-4 pt-2">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="text-xs font-medium text-ink-300 block mb-1">Scene Title</label>
                  <input
                    type="text"
                    value={sceneTitle}
                    onChange={(e) => setSceneTitle(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-ink-300 block mb-1">Panel Slot</label>
                  <input
                    type="text"
                    value={panelId}
                    onChange={(e) => setPanelId(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">
                  Subject Action & Narrative Beat (Artwork Only)
                </label>
                <textarea
                  rows={4}
                  value={actionPrompt}
                  onChange={(e) => setActionPrompt(e.target.value)}
                  placeholder="Describe the physical subject action..."
                  className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/30 leading-relaxed"
                />
                <p className="text-[11px] text-ink-400 mt-1">
                  Notice: Text and speech bubbles are rendered strictly by code in downstream layers (ADR-003).
                  Do not request dialogue inside the artwork.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-ink-300 block mb-1">Shot Framing</label>
                  <input
                    type="text"
                    value={shotType}
                    onChange={(e) => setShotType(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-ink-300 block mb-1">Camera Perspective</label>
                  <input
                    type="text"
                    value={cameraAngle}
                    onChange={(e) => setCameraAngle(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">Lighting Directive</label>
                <input
                  type="text"
                  value={lighting}
                  onChange={(e) => setLighting(e.target.value)}
                  className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                />
              </div>
            </div>
          </Card>

          {/* Compiled Context Packet Preview */}
          {compiledPacket && (
            <Card
              title="Compiled Panel Context Packet"
              subtitle="Pure-code continuity packet. Zero conversational state."
              action={
                <Badge variant="neutral" size="sm">
                  SHA-256: {compiledPacket.context_fingerprint?.substring(0, 8)}...
                </Badge>
              }
            >
              <div className="space-y-3 pt-2 text-xs">
                <div>
                  <span className="font-semibold text-white block mb-1">Effective Generation Prompt:</span>
                  <div className="p-3 rounded-xl bg-ink-950 border border-white/5 text-ink-200 leading-relaxed font-mono text-[11px]">
                    {compiledPacket.generation_prompt}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="font-semibold text-white block mb-1">Negative Constraints:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-rose-300 text-[11px]">
                      {compiledPacket.prohibited_deviations?.map((r: string, i: number) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <span className="font-semibold text-white block mb-1">Anchored Reference:</span>
                    <div className="text-[11px] text-ink-400 font-mono">
                      {compiledPacket.reference_assets?.length > 0
                        ? compiledPacket.reference_assets[0].asset_id
                        : 'Unanchored'}
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Live Batch Outcome Display */}
          {batchResult && (
            <Card
              title={`Batch Outcome: ${batchResult.batch_id}`}
              subtitle={`Status: ${batchResult.status} &bull; Latency: ${batchResult.total_duration_seconds.toFixed(2)}s`}
              action={
                <Badge
                  variant={
                    batchResult.status === 'COMPLETED'
                      ? 'success'
                      : batchResult.status === 'RUNNING'
                      ? 'info'
                      : 'warning'
                  }
                  size="sm"
                >
                  {batchResult.status}
                </Badge>
              }
            >
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                    <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Panels</span>
                    <span className="text-lg font-bold text-white">
                      {batchResult.successful_panels}/{batchResult.total_panels}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                    <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Verified</span>
                    <span className="text-lg font-bold text-emerald-400">
                      {batchResult.verified_panels}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                    <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Mode</span>
                    <span className="text-sm font-semibold text-white">
                      {batchResult.is_simulated ? 'Simulated' : 'Live Provider'}
                    </span>
                  </div>
                </div>

                {/* Per-panel details */}
                <div className="space-y-2">
                  {batchResult.panel_results?.map((res: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-ink-950/80 border border-white/5 flex items-center justify-between"
                    >
                      <div>
                        <span className="font-mono text-xs text-white font-medium">
                          {res.panel_id}
                        </span>
                        <p className="text-[10px] text-ink-400">
                          Attempts: {res.attempts_count} &bull; Output Hash: {res.output_content_hash?.substring(0, 10)}...
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            res.status === 'ACCEPTED'
                              ? 'success'
                              : res.status === 'GENERATED_PENDING_VERIFICATION'
                              ? 'info'
                              : 'danger'
                          }
                          size="sm"
                        >
                          {res.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Right Col: Production Controls */}
        <div className="space-y-4">
          <Card title="Production Controls" subtitle="Budget ceilings, retry policies, and verification gates">
            <div className="space-y-4 pt-2">
              {/* Simulation Mode Toggle */}
              <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-white">Execution Adapter</span>
                  {isSimulated ? (
                    <Badge variant="simulated" size="sm">
                      Simulated
                    </Badge>
                  ) : (
                    <Badge variant="neutral" size="sm">
                      Live Meta API
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => setIsSimulated(true)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isSimulated
                        ? 'bg-white text-black font-semibold'
                        : 'bg-white/5 text-ink-400 hover:text-white'
                    }`}
                  >
                    Simulated (Free)
                  </button>
                  <button
                    onClick={() => setIsSimulated(false)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      !isSimulated
                        ? 'bg-white text-black font-semibold'
                        : 'bg-white/5 text-ink-400 hover:text-white'
                    }`}
                  >
                    Live Meta API
                  </button>
                </div>
                <p className="text-[10px] text-ink-500 mt-2">
                  Simulated mode validates orchestration, attempt logs, and verification flow without incurring API spend.
                </p>
              </div>

              {/* Bounded Retries */}
              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">
                  Max Retries Per Panel (Bounded Ceiling)
                </label>
                <input
                  type="number"
                  min={1}
                  max={4}
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(parseInt(e.target.value, 10))}
                  className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                />
                <p className="text-[10px] text-ink-500 mt-1">
                  In accordance with ADR-006, retries are strictly capped at $\le 4$ total attempts before routing to human.
                </p>
              </div>

              {/* Spend Cap */}
              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">
                  Batch Spend Cap ($ USD)
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={spendCap}
                  onChange={(e) => setSpendCap(parseFloat(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                />
              </div>

              {/* Require Verification Checkbox */}
              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="req_verif"
                  checked={requireVerification}
                  onChange={(e) => setRequireVerification(e.target.checked)}
                  className="rounded bg-ink-950 border-white/10 accent-white focus:ring-0"
                />
                <label htmlFor="req_verif" className="text-xs text-ink-300 cursor-pointer">
                  Require Visual Verifier Passing Verdict for Acceptance
                </label>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
