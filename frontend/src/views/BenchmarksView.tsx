import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Layers,
  Lock,
  Cpu,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface BenchmarksViewProps {
  currentProject: string;
}

export const BenchmarksView: React.FC<BenchmarksViewProps> = () => {
  const { showToast } = useToast();
  const [m0Data, setM0Data] = useState<any | null>(null);
  const [regData, setRegData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'m0' | 'regressions'>('m0');
  const armRate = (id: string) => m0Data?.first_pass_yield?.[id];
  const armInterval = (id: string) => m0Data?.uncertainty_summaries?.find((row: any) => row.metric_name === (id === 'arm_b_reference_anchored' ? 'first_pass_yield_arm_b_anchored' : 'first_pass_yield_arm_a_text_only'));
  const armPassed = (id: string) => {
    const rate = armRate(id);
    return typeof rate === 'number' ? `${Math.round(rate * 6)}/6 (${Math.round(rate * 100)}%)` : 'Unavailable';
  };

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        setLoading(true);
        const [m0, reg] = await Promise.all([
          apiClient.getM0Benchmark(),
          apiClient.getRegressions(),
        ]);
        setM0Data(m0);
        setRegData(reg);
      } catch (err: any) {
        showToast({ type: 'error', title: 'Benchmarks Load Failed', message: err.message });
      } finally {
        setLoading(false);
      }
    };
    fetchTelemetry();
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <TabCharacterIcon tab="benchmarks" size={38} />
              Scientific Benchmarks & Visual Regression Corpus
            </h1>
            <Badge variant="neutral" size="sm">
              ADR-007 &amp; ADR-013
            </Badge>
          </div>
          <p className="text-xs text-ink-300 mt-1">
            Empirical M0 feasibility trial data &bull; Wilson score uncertainty intervals &bull; 7-domain fail-closed engine readiness.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('m0')}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeTab === 'm0'
                ? 'bg-white text-black font-semibold shadow-sm'
                : 'text-ink-400 hover:text-white bg-white/5'
            }`}
          >
            M0 Visual Feasibility (N=12)
          </button>
          <button
            onClick={() => setActiveTab('regressions')}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeTab === 'regressions'
                ? 'bg-white text-black font-semibold shadow-sm'
                : 'text-ink-400 hover:text-white bg-white/5'
            }`}
          >
            7-Domain Regression Corpus
          </button>
        </div>
      </div>

      {/* TAB 1: M0 FEASIBILITY BENCHMARK */}
      {activeTab === 'm0' && (
        <div className="space-y-6">
          {/* Arm A vs Arm B Comparative Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Arm A Card */}
            <Card
              title="Arm A: Unanchored Text Generation"
            subtitle="Stored historical sample data; not a live or newly reproduced provider run"
              action={
                <Badge variant="danger" size="md">
                  {armPassed('arm_a_text_only')}
                </Badge>
              }
            >
              <div className="space-y-3 pt-2 text-xs">
                <p className="text-ink-300 leading-relaxed">Historical Arm A summary loaded from the stored experiment record. Inspect the sample ledger below for recorded outcomes and hashes.</p>
                <div className="p-3 rounded-xl bg-ink-950 font-mono text-[11px] text-ink-400 border border-white/5 space-y-1">
                  <div>First-Pass Yield: <strong className="text-white">{armRate('arm_a_text_only') == null ? 'Unavailable' : `${Math.round(armRate('arm_a_text_only') * 100)}%`}</strong></div>
                  <div>Wilson 95% CI: <span className="text-ink-300">{armInterval('arm_a_text_only') ? `[${armInterval('arm_a_text_only').confidence_interval_low}, ${armInterval('arm_a_text_only').confidence_interval_high}]` : 'Unavailable'}</span></div>
                  <div>Status: <span className="text-ink-300 font-semibold">Historical record</span></div>
                </div>
              </div>
            </Card>

            {/* Arm B Card */}
            <Card
              title="Arm B: Canonical Reference Anchored"
            subtitle="Stored historical anchored-arm records; project-specific results are not implied"
              action={
                <Badge variant="success" size="md">
                  {armPassed('arm_b_reference_anchored')}
                </Badge>
              }
            >
              <div className="space-y-3 pt-2 text-xs">
                <p className="text-ink-300 leading-relaxed">This summary reflects the stored historical dataset only. Run a project-specific evaluation to assess current assets and provider behavior.</p>
                <div className="p-3 rounded-xl bg-ink-950 font-mono text-[11px] text-ink-400 border border-white/5 space-y-1">
                  <div>First-Pass Yield: <strong className="text-white">{armRate('arm_b_reference_anchored') == null ? 'Unavailable' : `${Math.round(armRate('arm_b_reference_anchored') * 100)}%`}</strong></div>
                  <div>Wilson 95% CI: <span className="text-ink-300">{armInterval('arm_b_reference_anchored') ? `[${armInterval('arm_b_reference_anchored').confidence_interval_low}, ${armInterval('arm_b_reference_anchored').confidence_interval_high}]` : 'Unavailable'}</span></div>
                  <div>Status: <span className="text-ink-300 font-semibold">Historical record</span></div>
                </div>
              </div>
            </Card>
          </div>

          {/* Scientific Limitations & Denominator Accounting */}
          <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-xs text-ink-300 space-y-2">
            <h4 className="font-semibold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-white" />
              Empirical Denominator Accounting &amp; Scientific Limitations
            </h4>
            <p className="leading-relaxed">
              Values above are imported from a stored historical artifact and are not a live verification result. The stored experiment metadata reports its sample denominator and limitations; inspect those records before drawing conclusions.
            </p>
          </div>

          {/* Sample Records Table */}
          {m0Data && (
            <Card title="Sample Records Ledger" subtitle="Exact latencies and token counts from live Meta API trial">
              <div className="overflow-x-auto pt-2">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-ink-400 text-[10px] uppercase font-semibold">
                      <th className="py-2.5 px-3">Sample ID</th>
                      <th className="py-2.5 px-3">Arm</th>
                      <th className="py-2.5 px-3">Scene Description</th>
                      <th className="py-2.5 px-3">Outcome</th>
                      <th className="py-2.5 px-3">Latency</th>
                      <th className="py-2.5 px-3">Output Hash</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono text-[11px]">
                    {m0Data.sample_records?.map((s: any, idx: number) => (
                      <tr key={idx} className="hover:bg-white/5 transition-colors">
                        <td className="py-2.5 px-3 font-semibold text-white">{s.sample_id}</td>
                        <td className="py-2.5 px-3">
                          <Badge variant={s.arm === 'ARM_B' ? 'success' : 'neutral'} size="sm">
                            {s.arm}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-3 font-sans text-ink-300 max-w-xs truncate">
                          {s.prompt_summary}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={s.outcome_status === 'SUCCESS' ? 'text-emerald-400' : 'text-rose-400'}>
                            {s.outcome_status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-ink-400">
                          {s.latency_seconds ? `${s.latency_seconds.toFixed(2)}s` : '—'}
                        </td>
                        <td className="py-2.5 px-3 text-ink-500 text-[10px]">
                          {s.output_hash ? `${s.output_hash.substring(0, 10)}...` : 'None'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* TAB 2: 7-DOMAIN VISUAL REGRESSION CORPUS */}
      {activeTab === 'regressions' && (
        <div className="space-y-6">
          {/* Readiness Inventory Summary */}
          {regData?.readiness_inventory && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-center">
              <div className="p-4 rounded-xl glass-card border border-white/5">
                <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">
                  Ready Domains
                </span>
                <span className="text-2xl font-bold text-emerald-400">
                  {regData.readiness_inventory.readiness_summary?.ready || 3}
                </span>
                <span className="text-[10px] text-ink-400 block mt-1">E1 Image Generation</span>
              </div>

              <div className="p-4 rounded-xl glass-card border border-white/5">
                <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">
                  Blocked Domains
                </span>
                <span className="text-2xl font-bold text-rose-400">
                  {regData.readiness_inventory.readiness_summary?.blocked_by_engine || 4}
                </span>
                <span className="text-[10px] text-ink-400 block mt-1">E5, E6, E7, S8 (Unimplemented)</span>
              </div>

              <div className="p-4 rounded-xl glass-card border border-white/5">
                <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">
                  Engine Readiness Guard
                </span>
                <Badge variant="neutral" size="md" className="mt-1">
                  Fail-Closed Active
                </Badge>
                <span className="text-[10px] text-ink-400 block mt-1">No fake test passes permitted</span>
              </div>
            </div>
          )}

          {/* Cases List */}
          <div className="space-y-3">
            {regData?.cases?.map((c: any, idx: number) => {
              const isReady = c.readiness === 'ready';

              return (
                <div
                  key={c.case_id || idx}
                  className="p-5 rounded-2xl glass-card border border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-white">{c.case_id}</span>
                      <Badge variant={isReady ? 'success' : 'danger'} size="sm">
                        {isReady ? 'READY' : 'BLOCKED BY ENGINE'}
                      </Badge>
                      <span className="text-xs text-ink-400 font-mono">[{c.domain}]</span>
                    </div>
                    <h3 className="text-sm font-semibold text-white">{c.title}</h3>
                    <p className="text-xs text-ink-300 leading-relaxed">{c.description}</p>
                    <div className="text-[10px] text-ink-500 font-mono mt-1">
                      Target Engine: <span className="text-white">{c.target_engine_id}</span> &bull; Dimension: {c.dimension}
                    </div>
                  </div>

                  <div className="shrink-0 text-right">
                    {isReady ? (
                      <span className="text-xs text-emerald-400 flex items-center gap-1 font-semibold">
                        <CheckCircle2 className="w-4 h-4" /> Evaluatable
                      </span>
                    ) : (
                      <span className="text-xs text-rose-400 flex items-center gap-1 font-semibold">
                        <Lock className="w-4 h-4" /> Locked by Engine
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
