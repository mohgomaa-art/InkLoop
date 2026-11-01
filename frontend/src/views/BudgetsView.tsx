import React, { useEffect, useState } from 'react';
import {
  Coins,
  ShieldAlert,
  RotateCcw,
  Activity,
  CheckCircle2,
  Clock,
  Sparkles,
  Lock,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface BudgetsViewProps {
  currentProject: string;
}

export const BudgetsView: React.FC<BudgetsViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();
  const [budgets, setBudgets] = useState<any | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [recovering, setRecovering] = useState(false);

  const fetchBudgetTelemetry = async () => {
    try {
      setLoading(true);
      const [bData, evData] = await Promise.all([
        apiClient.getBudgets(currentProject),
        apiClient.listExecutionEvents({ limit: 50 }),
      ]);
      setBudgets(bData);
      setEvents(evData);
    } catch (err: any) {
      showToast({ type: 'error', title: 'Budget load failed', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBudgetTelemetry();
  }, [currentProject]);

  const handleRunRecovery = async () => {
    try {
      setRecovering(true);
      const res = await apiClient.recoverExecution();
      showToast({
        type: 'success',
        title: 'Crash Recovery Completed',
        message: `Recovered ${res.total_recovered_runs} uncompleted runs and ${res.total_recovered_operations} operations.`,
      });
      fetchBudgetTelemetry();
    } catch (err: any) {
      showToast({ type: 'error', title: 'Recovery Failed', message: err.message });
    } finally {
      setRecovering(false);
    }
  };

  const globalCap = budgets?.global_cap_usd || 25.0;
  const availableGlobal = budgets?.available_global_usd !== undefined ? budgets.available_global_usd : 25.0;
  const spentGlobal = Math.max(0, globalCap - availableGlobal);
  const spentPct = Math.min(100, Math.round((spentGlobal / globalCap) * 100));

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <TabCharacterIcon tab="budgets" size={38} />
              Budgets, Spend & Append-Only Event Ledger
            </h1>
            <Badge variant="neutral" size="sm">
              Strict Decimal (4 Places)
            </Badge>
          </div>
          <p className="text-xs text-ink-300 mt-1">
            Hierarchical budget ceilings: Global &bull; Project &bull; Run &bull; Operation. Pre-dispatch atomic reservations prevent runaway spend.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunRecovery}
            disabled={recovering}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-medium transition-colors"
          >
            <Activity className="w-3.5 h-3.5 text-white" />
            {recovering ? 'Auditing Crash States...' : 'Run Crash Recovery'}
          </button>
          <button
            onClick={fetchBudgetTelemetry}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-ink-300 hover:text-white transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Decimal Accuracy & Accounting Invariant Card */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Lock className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            <strong>ADR-010 Financial Invariant:</strong> Floating-point binary drift is strictly prohibited.
            All budget reservations and settlements use Python Decimal minor units. Zero key or token leakage.
          </span>
        </div>
        <Badge variant="warning" size="sm">
          Protected
        </Badge>
      </div>

      {/* Multi-Scope Budget Progress */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Global Budget Scope */}
        <Card title="Global Budget Scope" subtitle="Root ceiling across all projects and sessions">
          <div className="space-y-4 pt-2">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-bold text-white">${spentGlobal.toFixed(4)}</span>
              <span className="text-xs text-ink-400">
                Cap: <strong className="text-white">${globalCap.toFixed(4)} USD</strong>
              </span>
            </div>

            {/* Progress Bar */}
            <div className="h-2 w-full rounded-full bg-ink-950 overflow-hidden border border-white/5">
              <div
                className="h-full bg-white rounded-full transition-all duration-300"
                style={{ width: `${spentPct}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-xs text-ink-400">
              <span>Available Allowance:</span>
              <span className="font-mono text-emerald-400 font-semibold">
                ${availableGlobal.toFixed(4)} USD
              </span>
            </div>
          </div>
        </Card>

        {/* Project Scope */}
        <Card title={`Project Scope: ${currentProject}`} subtitle="Project-level ceiling enforcement">
          <div className="space-y-4 pt-2">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-bold text-white">
                ${budgets?.project_available_usd !== null && budgets?.project_available_usd !== undefined ? (globalCap - budgets.project_available_usd).toFixed(4) : '0.0000'}
              </span>
              <span className="text-xs text-ink-400">
                Project Cap:{' '}
                <strong className="text-white">
                  ${budgets?.project_caps?.[currentProject] !== undefined ? budgets.project_caps[currentProject].toFixed(4) : globalCap.toFixed(4)} USD
                </strong>
              </span>
            </div>

            <div className="h-2 w-full rounded-full bg-ink-950 overflow-hidden border border-white/5">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: '4%' }} />
            </div>

            <div className="flex items-center justify-between text-xs text-ink-400">
              <span>Effective Allowance:</span>
              <span className="font-mono text-emerald-400 font-semibold">
                ${availableGlobal.toFixed(4)} USD
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Append-Only Execution Events Ledger */}
      <Card
        title={`Append-Only Execution Events Ledger (${events.length} Events)`}
        subtitle="SQLite WAL mode ledger recording every state change, atomic reservation, settlement, and recovery discovery."
      >
        <div className="space-y-2 pt-3 max-h-96 overflow-y-auto pr-1">
          {loading ? (
            <div className="py-6 text-center text-xs text-ink-400">Loading execution ledger...</div>
          ) : events.length === 0 ? (
            <p className="text-xs text-ink-400 text-center py-6">No execution events recorded yet.</p>
          ) : (
            events.map((ev, idx) => (
              <div
                key={ev.event_id || idx}
                className="p-3 rounded-xl bg-ink-950 border border-white/5 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-3">
                  <Badge variant="neutral" size="sm">
                    {ev.event_type}
                  </Badge>
                  <div>
                    <span className="font-mono text-white text-[11px]">{ev.entity_id}</span>
                    <p className="text-[10px] text-ink-400 font-mono mt-0.5">
                      Scope: {ev.scope || 'GLOBAL'} &bull; Event ID: {ev.event_id}
                    </p>
                  </div>
                </div>

                <div className="text-right font-mono text-[10px] text-ink-500">
                  {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '—'}
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
};
