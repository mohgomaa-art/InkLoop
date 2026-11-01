import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  BookOpen,
  ShieldCheck,
  Database,
  Layers,
  ArrowRight,
  TrendingUp,
  Coins,
  CheckCircle2,
  AlertCircle,
  Clock,
  Compass,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { NavTab } from '../components/common/Sidebar';

interface WorkspaceViewProps {
  currentProject: string;
  onNavigate: (tab: NavTab) => void;
}

export const WorkspaceView: React.FC<WorkspaceViewProps> = ({ currentProject, onNavigate }) => {
  const [bible, setBible] = useState<any>(null);
  const [batches, setBatches] = useState<any[]>([]);
  const [budgets, setBudgets] = useState<any>(null);
  const [diagnostics, setDiagnostics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        setLoading(true);
        const [bData, batchData, budgetData, diagData] = await Promise.all([
          apiClient.getProjectBible(currentProject).catch(() => null),
          apiClient.listBatches().catch(() => []),
          apiClient.getBudgets(currentProject).catch(() => null),
          apiClient.getDiagnostics().catch(() => null),
        ]);
        if (mounted) {
          setBible(bData);
          setBatches(batchData || []);
          setBudgets(budgetData);
          setDiagnostics(diagData);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [currentProject]);

  const latestBatch = batches[0];
  const charCount = bible?.characters ? Object.keys(bible.characters).length : 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Quiet, creation-first welcome */}
      <section className="workspace-welcome">
        <div className="welcome-kicker flex items-center gap-2.5">
          <TabCharacterIcon tab="workspace" size={36} />
          YOUR CREATIVE WORKSPACE
        </div>
        <h1>Good morning, creator.</h1>
        <p>Your world is ready when you are. Pick up a story, shape a scene, or start with a blank page.</p>
        <div className="welcome-actions">
          <button onClick={() => onNavigate('agent')} className="welcome-primary"><Sparkles /> Start a creation <span>↗</span></button>
          <button onClick={() => onNavigate('creative')} className="welcome-secondary"><Compass className="w-3.5 h-3.5" /> Creative Director</button>
          <button onClick={() => onNavigate('studio')} className="welcome-secondary"><Layers /> Open studio</button>
          <button onClick={() => onNavigate('bible')} className="welcome-secondary"><BookOpen /> Story bible</button>
        </div>
        <div className="welcome-footnote"><span className="status-dot" /> Canon and production tools are ready for this project</div>
      </section>

      {/* 60-Second Quick Start Shelf */}
      <section className="p-5 rounded-2xl bg-zinc-900/60 border border-white/10 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-white" />
            <h2 className="text-sm font-bold text-white tracking-wide">60-Second Project Quick-Start</h2>
          </div>
          <span className="text-[11px] text-zinc-400">Instantly provisions Story Bible, Characters & Page 1</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {[
            {
              genre: 'shonen',
              title: 'Shonen Action (RTL)',
              desc: 'High-contrast ink, bold action lines, dynamic 4-panel spread',
              direction: 'rtl',
              lang: 'ar',
            },
            {
              genre: 'webtoon',
              title: 'Vertical Webtoon',
              desc: 'Infinite scroll layout, smooth digital gradients, mobile-first',
              direction: 'ltr',
              lang: 'en',
            },
            {
              genre: 'seinen',
              title: 'Gritty Seinen Noir',
              desc: 'Cinematic wide aspect ratios, deep black shadows, hatching',
              direction: 'rtl',
              lang: 'ar',
            },
            {
              genre: 'comedy',
              title: '4-Koma Comedy',
              desc: 'Classic 4-panel vertical gag format with clean open gutters',
              direction: 'rtl',
              lang: 'ar',
            },
          ].map((item) => (
            <button
              key={item.genre}
              type="button"
              onClick={async () => {
                try {
                  const res = await apiClient.quickStartProject({
                    title: `New ${item.title.split(' ')[0]} Comic`,
                    genre: item.genre as any,
                    premise: item.desc,
                    reading_direction: item.direction as any,
                    language: item.lang as any,
                  });
                  if (res.success) {
                    onNavigate('editor');
                  }
                } catch {
                  onNavigate('editor');
                }
              }}
              className="p-3.5 rounded-xl bg-zinc-800/80 hover:bg-zinc-800 border border-white/10 hover:border-white/30 text-left transition space-y-1.5 group cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white group-hover:text-amber-400 transition">
                  {item.title}
                </span>
                <ArrowRight size={13} className="text-zinc-500 group-hover:text-white transition" />
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">{item.desc}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Primary KPI Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Story Canon Status */}
        <Card>
          <div className="flex items-center justify-between text-ink-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Story Canon</span>
            <BookOpen className="w-4 h-4 text-ink-200" />
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {charCount} {charCount === 1 ? 'Character' : 'Characters'}
          </div>
          <div className="flex items-center gap-2 text-xs text-ink-400">
            <Badge variant="neutral" size="sm">
              v{bible?.bible_version || 1}
            </Badge>
            <span className="truncate font-mono text-[10px] text-ink-500 max-w-[120px]">
              {bible?.canon_hash?.substring(0, 10)}...
            </span>
          </div>
        </Card>

        {/* Total Batches */}
        <Card>
          <div className="flex items-center justify-between text-ink-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Production Batches</span>
            <Layers className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-white mb-1">{batches.length}</div>
          <div className="flex items-center gap-2 text-xs text-ink-400">
            <span>Latest:</span>
            <span className="text-white font-medium">
              {latestBatch?.status || 'No batches run yet'}
            </span>
          </div>
        </Card>

        {/* Visual Verification Gate */}
        <Card>
          <div className="flex items-center justify-between text-ink-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Verification Quality</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mb-1">3 Tiers</div>
          <div className="flex items-center gap-2 text-xs text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>L0 Code &bull; L1 SAM &bull; L2 Judge</span>
          </div>
        </Card>

        {/* Global Spend Cap */}
        <Card>
          <div className="flex items-center justify-between text-ink-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Budget Available</span>
            <Coins className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            ${budgets ? budgets.available_global_usd.toFixed(2) : '25.00'}
          </div>
          <div className="flex items-center gap-2 text-xs text-ink-400">
            <span>Global Cap:</span>
            <span className="text-white font-medium">
              ${budgets ? budgets.global_cap_usd.toFixed(2) : '25.00'}
            </span>
          </div>
        </Card>
      </div>

      {/* Two-Column Activity & Readiness */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Batches Activity */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
              <Clock className="w-4 h-4 text-ink-200" />
              Recent Generation Batches
            </h2>
            <button
              onClick={() => onNavigate('batches')}
              className="text-xs font-medium text-ink-300 hover:text-white flex items-center gap-1 transition-colors"
            >
              View all runs <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {batches.length === 0 ? (
            <Card className="text-center py-8">
              <Layers className="w-8 h-8 text-ink-500 mx-auto mb-2 opacity-50" />
              <p className="text-xs text-ink-400">No batch runs executed yet.</p>
              <button
                onClick={() => onNavigate('studio')}
                className="mt-3 text-xs text-ink-300 hover:text-white hover:underline"
              >
                Launch your first generation &rarr;
              </button>
            </Card>
          ) : (
            <div className="space-y-2">
              {batches.slice(0, 4).map((b) => (
                <div
                  key={b.batch_id}
                  onClick={() => onNavigate('batches')}
                  className="flex items-center justify-between p-4 rounded-xl bg-ink-900/60 border border-white/5 hover:border-white/20 hover:bg-ink-850/60 transition-all cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-white/5 text-ink-300">
                      <Layers className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white font-mono">
                          {b.batch_id}
                        </span>
                        {b.is_simulated ? (
                          <Badge variant="simulated" size="sm">
                            Simulated
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            Live Provider
                          </Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-ink-400 mt-0.5">
                        {b.successful_panels}/{b.total_panels} panels succeeded &bull;{' '}
                        {b.verified_panels} verified
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <Badge
                        variant={
                          b.status === 'COMPLETED'
                            ? 'success'
                            : b.status === 'RUNNING'
                            ? 'info'
                            : 'warning'
                        }
                        size="sm"
                      >
                        {b.status}
                      </Badge>
                      <p className="text-[10px] text-ink-500 font-mono mt-1">
                        {b.total_duration_seconds ? `${b.total_duration_seconds.toFixed(1)}s` : '—'}
                      </p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-ink-500" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Engine Readiness & Defensive Health */}
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            System Readiness
          </h2>

          <Card className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs pb-2 border-b border-white/5">
                <span className="text-ink-400">Meta Model API</span>
                {diagnostics?.provider?.configured ? (
                  <Badge variant="success" size="sm">
                    Live Keys Ready
                  </Badge>
                ) : (
                  <Badge variant="simulated" size="sm">
                    Simulated Ready
                  </Badge>
                )}
              </div>

              <div className="flex items-center justify-between text-xs pb-2 border-b border-white/5">
                <span className="text-ink-400">M0 Feasibility Anchor</span>
                <Badge variant="success" size="sm">
                  100% Passed (Arm B)
                </Badge>
              </div>

              <div className="flex items-center justify-between text-xs pb-2 border-b border-white/5">
                <span className="text-ink-400">Canonical Character</span>
                <span className="text-white font-medium">Nour (Verified)</span>
              </div>

              <div className="flex items-center justify-between text-xs pb-2 border-b border-white/5">
                <span className="text-ink-400">Reference Anchor Hash</span>
                <span className="font-mono text-[10px] text-emerald-400">b2c2c4dc...</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-ink-400">Taxonomy Coverage</span>
                <span className="text-ink-200 font-medium">60 Groups / 840 Elements</span>
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={() => onNavigate('settings')}
                className="w-full py-2 rounded-xl bg-white/5 hover:bg-white/10 text-ink-300 hover:text-white text-xs font-medium border border-white/10 transition-colors"
              >
                Inspect Diagnostics & Logs
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
