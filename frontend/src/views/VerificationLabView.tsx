import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Play,
  FileCheck,
  Cpu,
  Layers,
  HelpCircle,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface VerificationLabViewProps {
  currentProject: string;
}

export const VerificationLabView: React.FC<VerificationLabViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();
  const [rules, setRules] = useState<any | null>(null);
  const [loadingRules, setLoadingRules] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<any | null>(null);
  const [mode, setMode] = useState<'simulated' | 'live'>('live');
  const [assetId, setAssetId] = useState('');
  const [characterId, setCharacterId] = useState('');
  const [projectImages, setProjectImages] = useState<any[]>([]);
  const [projectCharacters, setProjectCharacters] = useState<any[]>([]);

  useEffect(() => {
    const fetchRules = async () => {
      try {
        setLoadingRules(true);
        const data = await apiClient.getVerificationRules();
        setRules(data);
      } catch (err: any) {
        showToast({ type: 'error', title: 'Rules fetch failed', message: err.message });
      } finally {
        setLoadingRules(false);
      }
    };
    fetchRules();
  }, []);

  useEffect(() => {
    setAssetId('');
    setCharacterId('');
    Promise.all([
      apiClient.listAssets({ project_id: currentProject }).then((assets) => setProjectImages(assets.filter((asset) => String(asset.mime_type || '').startsWith('image/')))),
      apiClient.getProjectBible(currentProject).then((bible) => setProjectCharacters(Object.entries(bible.characters || {}).map(([id, character]: [string, any]) => ({ character_id: id, name: character.name || id })))),
    ]).catch((err: any) => showToast({ type: 'error', title: 'Project Verification Context Failed', message: err.message }));
  }, [currentProject]);

  const handleRunVerification = async () => {
    try {
      setVerifying(true);
      const res = await apiClient.verifyAsset({
        project_id: currentProject,
        character_id: characterId,
        asset_id: assetId,
        mode,
      });
      setVerificationResult(res);
      showToast({
        type: res.passed ? 'success' : 'warning',
        title: res.passed ? 'Verification Passed Gate' : 'Verification Rejected',
        message: res.passed
          ? 'All declared canonical attributes passed checklist verification.'
          : res.rejection_reason || 'One or more required traits failed verification.',
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Verification Run Failed', message: err.message });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <TabCharacterIcon tab="verification" size={38} />
              Visual Verification Lab
            </h1>
            <Badge variant="success" size="sm">
              Remove-Only Gate
            </Badge>
          </div>
          <p className="text-xs text-ink-300 mt-1">
            Checks the selected project image against the selected character contract. Provider-based checks show unavailable or unverified states when evidence is missing.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-ink-950 border border-white/10 text-xs">
            <button
              onClick={() => setMode('simulated')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                mode === 'simulated'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-ink-400 hover:text-white'
              }`}
            >
              Simulated
            </button>
            <button
              onClick={() => setMode('live')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                mode === 'live'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-ink-400 hover:text-white'
              }`}
            >
              Live API
            </button>
          </div>

          <select aria-label="Registered project image" value={assetId} onChange={(e) => setAssetId(e.target.value)} className="bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white">
            <option value="">Select image</option>
            {projectImages.map((asset) => <option key={asset.asset_id} value={asset.asset_id}>{asset.name || asset.filename || asset.asset_id}</option>)}
          </select>
          <select aria-label="Canonical project character" value={characterId} onChange={(e) => setCharacterId(e.target.value)} className="bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white">
            <option value="">Select character</option>
            {projectCharacters.map((character) => <option key={character.character_id} value={character.character_id}>{character.name} ({character.character_id})</option>)}
          </select>
          <button
            onClick={handleRunVerification}
            disabled={verifying || !assetId.trim() || !characterId.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold  transition-all disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            {verifying ? 'Evaluating Tiers...' : 'Run Verification Gate'}
          </button>
        </div>
      </div>

      {/* Main Layout: Verification Runner Result + Tiered Rules Inspection */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Verification Result Showcase */}
        <div className="lg:col-span-2 space-y-5">
          {verificationResult ? (
            <Card
              title="Verification Gate Verdict"
              subtitle={`Mode: ${verificationResult.is_simulated ? 'SIMULATED' : 'LIVE PROVIDER'}`}
              action={
                <Badge variant={verificationResult.passed ? 'success' : 'danger'} size="lg">
                  {verificationResult.passed ? 'PASSED GATE' : 'REJECTED BY VERIFIER'}
                </Badge>
              }
            >
              <div className="space-y-5 pt-2">
                {/* 3 Tier Status Grid */}
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                    <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">
                      L0 Code Check
                    </span>
                    <Badge variant={verificationResult.l0_passed !== false ? 'success' : 'danger'} size="sm">
                      {verificationResult.l0_passed !== false ? 'PASS' : 'FAIL'}
                    </Badge>
                  </div>

                  <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                    <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">
                      L1 SAM 3.1
                    </span>
                    <Badge variant={verificationResult.l1_passed !== false ? 'success' : 'danger'} size="sm">
                      {verificationResult.l1_passed !== false ? 'PASS' : 'FAIL'}
                    </Badge>
                  </div>

                  <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                    <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">
                      L2 Vision Judge
                    </span>
                    <Badge variant={verificationResult.l2_passed !== false ? 'success' : 'danger'} size="sm">
                      {verificationResult.l2_passed !== false ? 'PASS' : 'FAIL'}
                    </Badge>
                  </div>
                </div>

                {/* Detailed Canonical Attribute Verdicts */}
                <div>
                  <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-2">
                    Declared Canonical Checklist (Tri-State JSON)
                  </h4>
                  <div className="space-y-2">
                    {verificationResult.verdicts?.map((v: any, idx: number) => {
                      const isPass = v.verdict === 'pass';
                      const isUnsure = v.verdict === 'unsure';

                      return (
                        <div
                          key={idx}
                          className="p-3 rounded-xl bg-ink-950 border border-white/5 flex items-start justify-between gap-4"
                        >
                          <div className="flex items-start gap-3">
                            {isPass ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                            ) : isUnsure ? (
                              <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                            ) : (
                              <XCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                            )}
                            <div>
                              <span className="font-mono text-xs font-semibold text-white uppercase">
                                {v.attr_id}
                              </span>
                              <p className="text-xs text-ink-300 mt-0.5">{v.evidence}</p>
                            </div>
                          </div>

                          <Badge
                            variant={isPass ? 'success' : isUnsure ? 'warning' : 'danger'}
                            size="sm"
                          >
                            {v.verdict.toUpperCase()}
                          </Badge>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Rejection / Human Review Notice */}
                {!verificationResult.passed && (
                  <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-200 text-xs">
                    <strong className="block mb-1">Fail-Closed Policy Enforced:</strong>
                    {verificationResult.rejection_reason || 'Panel fails quality gate and is held for targeted retry or operator review.'}
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <Card className="text-center py-16">
              <ShieldCheck className="w-12 h-12 text-ink-500 mx-auto mb-3 opacity-40" />
              <h3 className="text-sm font-semibold text-white">No Verification Run Selected</h3>
              <p className="text-xs text-ink-400 mt-1 max-w-sm mx-auto">
                Enter a registered image asset ID and a character ID from this project, then choose live verification or an explicit simulated check.
              </p>
            </Card>
          )}
        </div>

        {/* Multi-Tier Rules Explorer */}
        <div className="space-y-4">
          <Card title="Active Verification Rules" subtitle="Formal thresholds applied at each inspection tier">
            {loadingRules ? (
              <div className="text-xs text-ink-400 py-6 text-center">Loading rules...</div>
            ) : rules ? (
              <div className="space-y-4 pt-2 text-xs">
                {/* L0 Tier */}
                <div className="p-3 rounded-xl bg-ink-950 border border-white/5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">Tier L0: Code Heuristics</span>
                    <Badge variant="neutral" size="sm">
                      Deterministic
                    </Badge>
                  </div>
                  <p className="text-[11px] text-ink-400">
                    Min Dimensions: {rules.l0_code?.min_dimension_px}px &bull; Min Size: {rules.l0_code?.min_byte_size} bytes
                  </p>
                  <p className="text-[11px] text-ink-400">
                    Sheet Bleed Check: {rules.l0_code?.sheet_bleed_check ? 'Enabled' : 'Disabled'}
                  </p>
                </div>

                {/* L1 Tier */}
                <div className="p-3 rounded-xl bg-ink-950 border border-white/5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">Tier L1: SAM 3.1 Segmentation</span>
                    <Badge variant="neutral" size="sm">
                      Model-Based
                    </Badge>
                  </div>
                  <p className="text-[11px] text-ink-400">
                    Model: {rules.l1_sam_subject?.model} &bull; Query comes from the selected being's declared form
                  </p>
                  <p className="text-[11px] text-ink-400">
                    Face-specific checks apply only when enabled in that character's canon. Nonhuman forms are checked against their declared attributes.
                  </p>
                </div>

                {/* L2 Tier */}
                <div className="p-3 rounded-xl bg-ink-950 border border-white/5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">Tier L2: Vision Judge</span>
                    <Badge variant="neutral" size="sm">
                      Tri-State JSON
                    </Badge>
                  </div>
                  <p className="text-[11px] text-ink-400">
                    Model: {rules.l2_vision_judge?.model}
                  </p>
                  <p className="text-[11px] text-ink-400">
                    Acceptance: {rules.l2_vision_judge?.acceptance_policy}
                  </p>
                  <p className="text-[11px] text-amber-400">
                    Unsure Policy: {rules.l2_vision_judge?.unsure_policy}
                  </p>
                  <p className="text-[11px] text-ink-400">{rules.l2_vision_judge?.anatomy_policy}</p>
                </div>
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
};
