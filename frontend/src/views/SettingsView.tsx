import React, { useEffect, useState } from 'react';
import {
  Settings,
  ShieldCheck,
  Cpu,
  Database,
  Lock,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Folder,
  Sparkles,
  Eye,
  Activity,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';
import { useReducedMotion } from '../hooks/useReducedMotion';
import type { MotionPreference } from '../utils/motion';

interface SettingsViewProps {
  currentProject: string;
}

export const SettingsView: React.FC<SettingsViewProps> = () => {
  const { showToast } = useToast();
  const [diag, setDiag] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const { preference, setPreference, systemReduced, isReduced } = useReducedMotion();

  const fetchDiagnostics = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getDiagnostics();
      setDiag(data);
    } catch (err: any) {
      showToast({ type: 'error', title: 'Diagnostics Load Failed', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <TabCharacterIcon tab="settings" size={38} />
              Operational Diagnostics &amp; System Configuration
            </h1>
            <Badge variant="neutral" size="sm">
              Live Telemetry
            </Badge>
          </div>
          <p className="text-xs text-ink-300 mt-1">
            Environment health &bull; Meta Model API readiness &bull; Storage directory integrity &bull; Secret masking audit.
          </p>
        </div>

        <button
          onClick={fetchDiagnostics}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-medium transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Refresh Diagnostics
        </button>
      </div>

      {loading ? (
        <div className="py-12 text-center text-xs text-ink-400">Loading system diagnostics...</div>
      ) : diag ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Provider Readiness */}
          <Card
            title="Meta Model API Integration"
            subtitle="ADR-004 Canonical Credential & Model Catalog Standard"
            action={
              diag.provider?.configured ? (
                <Badge variant="success" size="sm">
                  Live Active
                </Badge>
              ) : (
                <Badge variant="simulated" size="sm">
                  Simulated Ready
                </Badge>
              )
            }
          >
            <div className="space-y-3 pt-2 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">Base URL:</span>
                <span className="font-mono text-white text-[11px]">{diag.provider?.base_url}</span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">API Key Masking (Secret Hygiene):</span>
                <Badge variant="neutral" size="sm">
                  {diag.provider?.api_key_masked}
                </Badge>
              </div>

              {!diag.provider?.configured && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs flex items-start gap-2.5 my-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                  <div>
                    <span className="font-semibold block text-amber-300">
                      MODEL_API_KEY is not configured
                    </span>
                    <span className="text-[11px] text-amber-200/90 leading-relaxed block mt-0.5">
                      Set <code className="font-mono bg-black/40 px-1 py-0.5 rounded text-white">MODEL_API_KEY</code> in your <code className="font-mono bg-black/40 px-1 py-0.5 rounded text-white">.env</code> file to enable live Meta models. Obtain an API key at{' '}
                      <a
                        href="https://dev.meta.ai"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline hover:text-white font-medium text-amber-300"
                      >
                        https://dev.meta.ai
                      </a>.
                    </span>
                  </div>
                </div>
              )}

              <div>
                <span className="text-ink-400 block mb-1.5">Verified Active Model Catalog:</span>
                <div className="flex flex-wrap gap-2">
                  {diag.provider?.models_available?.map((m: string) => (
                    <span
                      key={m}
                      className="px-2.5 py-1 rounded-lg bg-ink-950 border border-white/5 font-mono text-[11px] text-white font-medium"
                    >
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {/* Storage Integrity */}
          <Card
            title="Storage Directory Integrity"
            subtitle="Content-addressed store &amp; artifact persistence paths"
          >
            <div className="space-y-3 pt-2 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">Batches Run Directory:</span>
                <span className={diag.storage?.batches_directory_exists ? 'text-emerald-400' : 'text-rose-400'}>
                  {diag.storage?.batches_directory_exists ? 'Verified Present' : 'Missing'}
                </span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">60-Group Catalogue Data:</span>
                <span className={diag.storage?.catalogue_register_exists ? 'text-emerald-400' : 'text-rose-400'}>
                  {diag.storage?.catalogue_register_exists ? 'Verified Present' : 'Missing'}
                </span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">Canonical Nour Reference Image:</span>
                <span className={diag.storage?.nour_reference_anchor_exists ? 'text-emerald-400' : 'text-rose-400'}>
                  {diag.storage?.nour_reference_anchor_exists ? 'Verified Present' : 'Missing'}
                </span>
              </div>

              <div className="pt-1">
                <span className="text-[10px] text-ink-500 font-mono block truncate">
                  Root: {diag.storage?.project_root}
                </span>
              </div>
            </div>
          </Card>

          {/* Operational Guardrails */}
          <Card
            title="Operational Guardrails &amp; Concurrency"
            subtitle="ADR-006 Hard Safety Ceilings"
          >
            <div className="space-y-3 pt-2 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">Default Global Spend Cap:</span>
                <span className="font-mono text-white font-semibold">
                  ${diag.budget_defaults?.default_spend_cap_usd?.toFixed(2)} USD
                </span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">Max Retries Per Panel Ceiling:</span>
                <span className="font-mono text-white font-semibold">
                  {diag.budget_defaults?.default_max_retries} attempts
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-ink-400">Strict Concurrency Limit:</span>
                <span className="font-mono text-white font-semibold">
                  {diag.budget_defaults?.concurrency_limit} (Isolated Sequential Execution)
                </span>
              </div>
            </div>
          </Card>

          {/* Motion Design & Accessibility System */}
          <Card
            title="Motion Design & Accessibility System"
            subtitle="Calm desktop interaction tokens, compositor pacing & reduced-motion overrides"
          >
            <div className="space-y-4 pt-2 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">OS Reduced Motion Detected:</span>
                <Badge variant={systemReduced ? 'warning' : 'neutral'} size="sm">
                  {systemReduced ? 'Active in OS' : 'Standard'}
                </Badge>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-ink-400">Effective Motion State:</span>
                <span className="font-mono text-white font-semibold">
                  {isReduced ? 'Calm / Reduced (0ms transforms)' : 'Full Smooth Motion (Compositor 60/120 FPS)'}
                </span>
              </div>

              <div>
                <span className="text-[11px] font-semibold text-ink-300 block mb-2">
                  Application Motion Preference:
                </span>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setPreference('normal');
                      showToast({ type: 'info', title: 'Full Motion Enabled', message: 'Restrained, calm desktop motion tokens active.' });
                    }}
                    className={`py-2 px-3 rounded-xl border text-center font-medium motion-interactive cursor-pointer ${
                      preference === 'normal'
                        ? 'bg-white text-zinc-950 border-white'
                        : 'bg-white/5 text-ink-300 border-white/10 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    Full Motion
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPreference('reduced');
                      showToast({ type: 'info', title: 'Reduced Motion Enabled', message: 'Spatial transitions suppressed; gentle fades active.' });
                    }}
                    className={`py-2 px-3 rounded-xl border text-center font-medium motion-interactive cursor-pointer ${
                      preference === 'reduced'
                        ? 'bg-white text-zinc-950 border-white'
                        : 'bg-white/5 text-ink-300 border-white/10 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    Reduced Motion
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPreference('off');
                      showToast({ type: 'info', title: 'Motion Disabled', message: 'All durations set to 0ms for instant feedback.' });
                    }}
                    className={`py-2 px-3 rounded-xl border text-center font-medium motion-interactive cursor-pointer ${
                      preference === 'off'
                        ? 'bg-white text-zinc-950 border-white'
                        : 'bg-white/5 text-ink-300 border-white/10 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    Motion Off
                  </button>
                </div>
              </div>

              <div className="pt-2 text-[11px] text-ink-500 space-y-1">
                <p>• GPU-first: all animations use compositor-only properties (<code className="text-zinc-300">transform</code>, <code className="text-zinc-300">opacity</code>).</p>
                <p>• Canvas safety: direct pointer manipulation has zero transition delays.</p>
                <p>• Resource economy: decorative loops automatically pause when window is hidden.</p>
              </div>
            </div>
          </Card>

          {/* System Version & Invariant Status */}
          <Card title="System Subsystems Status" subtitle="Milestone 1 Architecture State">
            <div className="space-y-3 pt-2 text-xs">
              {Object.entries(diag.system_status || {}).map(([k, v]: any) => (
                <div key={k} className="flex items-center justify-between pb-1.5 border-b border-white/5">
                  <span className="text-ink-400 capitalize">{k.replace(/_/g, ' ')}:</span>
                  <Badge variant="neutral" size="sm">
                    {String(v)}
                  </Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
};
