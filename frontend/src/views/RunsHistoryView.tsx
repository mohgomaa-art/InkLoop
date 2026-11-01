import React, { useEffect, useState } from 'react';
import {
  Layers,
  Clock,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Eye,
  ArrowRight,
  ShieldCheck,
  Search,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface RunsHistoryViewProps {
  currentProject: string;
}

export const RunsHistoryView: React.FC<RunsHistoryViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();
  const [batches, setBatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedBatch, setSelectedBatch] = useState<any | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [executionRuns, setExecutionRuns] = useState<any[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<any | null>(null);
  const [runEvents, setRunEvents] = useState<any[]>([]);

  const fetchBatches = async () => {
    try {
      setLoading(true);
      const [data, runs] = await Promise.all([apiClient.listBatches().catch(() => []), apiClient.listExecutionRuns().catch(() => [])]);
      setBatches(data);
      setExecutionRuns(runs.filter((run: any) => !currentProject || run.project_id === currentProject));
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to load batches', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, [currentProject]);

  useEffect(() => {
    if (!selectedRunId) { setRunDetail(null); setRunEvents([]); return; }
    let disposed = false;
    let stream: EventSource | null = null;
    void apiClient.getExecutionRun(selectedRunId).then((detail) => {
      if (disposed) return;
      setRunDetail(detail); setRunEvents(detail.events || []);
      stream = new EventSource(apiClient.getExecutionEventsStreamUrl(selectedRunId, (detail.events || []).length));
      stream.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data);
          setRunEvents((items) => [...items, event]);
          if (['run_completed', 'run_failed', 'run_cancelled'].includes(event.event_type)) { void apiClient.getExecutionRun(selectedRunId).then((fresh) => { if (!disposed) setRunDetail(fresh); }); stream?.close(); }
        } catch { /* Ignore malformed events; durable ledger state remains readable through run detail. */ }
      };
      stream.onerror = () => { stream?.close(); };
    }).catch((error) => { if (!disposed) showToast({ type: 'error', title: 'Run details unavailable', message: error.message }); });
    return () => { disposed = true; stream?.close(); };
  }, [selectedRunId]);

  const controlRun = async (runId: string, action: 'cancel' | 'resume') => {
    try {
      const result = action === 'cancel' ? await apiClient.cancelExecutionRun(runId) : await apiClient.resumeExecutionRun(runId);
      setRunDetail((old: any) => old ? { ...old, run: result } : old);
      await fetchBatches();
    } catch (error: any) { showToast({ type: 'error', title: `Could not ${action} run`, message: error.message }); }
  };

  const handleInspectBatch = async (batchId: string) => {
    try {
      setLoadingDetail(true);
      const detail = await apiClient.getBatch(batchId);
      setSelectedBatch(detail);
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to load batch detail', message: err.message });
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleResumeBatch = async (batchId: string) => {
    try {
      setResuming(true);
      const newSummary = await apiClient.resumeBatch(batchId);
      setSelectedBatch(newSummary);
      fetchBatches();
      showToast({
        type: 'success',
        title: 'Batch Resumed Successfully',
        message: `Status: ${newSummary.status}. Retried unresolved operations.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Batch Resume Failed', message: err.message });
    } finally {
      setResuming(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <TabCharacterIcon tab="batches" size={38} />
            Production Batches & Attempt Audits
          </h1>
          <p className="text-xs text-ink-300 mt-1">
            Complete provenance for multi-panel generation batches, bounded retry attempts, and verification gates.
          </p>
        </div>

        <button
          onClick={fetchBatches}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-medium transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Refresh Runs
        </button>
      </div>

      <section className="execution-monitor">
        <div className="execution-monitor-heading"><div><h2>Agent executions</h2><p>Live state and history from the execution ledger.</p></div><button onClick={fetchBatches}><RotateCcw size={14} />Refresh</button></div>
        {executionRuns.length === 0 ? <p className="execution-empty">No execution runs recorded for this project.</p> : executionRuns.map((run) => <div className="execution-run" key={run.run_id}><div><strong>{run.run_id}</strong><span>{run.project_id}</span></div><Badge variant={run.status === 'succeeded' ? 'success' : run.status === 'running' ? 'info' : 'warning'} size="sm">{run.status}</Badge><button onClick={() => setSelectedRunId(run.run_id)}>Inspect live run</button></div>)}
        {selectedRunId && runDetail && <div className="execution-run-detail"><div className="execution-run-detail-head"><strong>{runDetail.run.run_id} · {runDetail.run.status}</strong><div>{runDetail.run.status === 'running' && <button onClick={() => void controlRun(selectedRunId, 'cancel')}>Cancel</button>}{runDetail.run.status === 'interrupted' && <button onClick={() => void controlRun(selectedRunId, 'resume')}>Resume</button>}<button onClick={() => setSelectedRunId(null)}>Close</button></div></div><div className="execution-operation-list">{runDetail.operations?.map((op: any) => <div key={op.operation_id}><span>{op.operation_type}</span><small>{op.engine_id}</small><Badge variant={op.status === 'succeeded' ? 'success' : op.status === 'running' ? 'info' : 'neutral'} size="sm">{op.status}</Badge></div>)}</div><div className="execution-event-list" aria-live="polite">{runEvents.slice(-30).map((event, index) => <div key={`${event.event_id || event.event_type}-${index}`}><time>{new Date(event.timestamp).toLocaleTimeString()}</time><b>{event.event_type}</b><span>{event.operation_id || event.data?.reason || ''}</span></div>)}</div></div>}
      </section>

      {/* Batches Table / Grid */}
      {loading ? (
        <div className="py-12 text-center text-xs text-ink-400">Loading batch records...</div>
      ) : batches.length === 0 ? (
        <Card className="text-center py-12">
          <Layers className="w-10 h-10 text-ink-500 mx-auto mb-3 opacity-40" />
          <p className="text-xs text-ink-300 font-medium">No batch history found.</p>
          <p className="text-[11px] text-ink-500 mt-1">
            Execute a batch from the Generation Studio to record production telemetry.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {batches.map((b) => (
            <div
              key={b.batch_id}
              className="p-5 rounded-2xl glass-card border border-white/5 hover:border-white/15 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-white/5 text-white shrink-0 mt-0.5">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-sm font-bold text-white">{b.batch_id}</span>
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
                  <div className="flex items-center gap-4 text-xs text-ink-400 mt-2">
                    <span>
                      Panels: <strong className="text-white">{b.successful_panels}/{b.total_panels}</strong>
                    </span>
                    <span>
                      Verified: <strong className="text-emerald-400">{b.verified_panels}</strong>
                    </span>
                    <span>
                      Duration:{' '}
                      <strong className="text-white">
                        {b.total_duration_seconds ? `${b.total_duration_seconds.toFixed(1)}s` : '—'}
                      </strong>
                    </span>
                    <span>
                      Started:{' '}
                      <span className="text-ink-300">
                        {b.started_at ? new Date(b.started_at).toLocaleTimeString() : '—'}
                      </span>
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 self-end md:self-auto">
                <button
                  onClick={() => handleInspectBatch(b.batch_id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
                >
                  <Eye className="w-3.5 h-3.5 text-white" />
                  Inspect Batch
                </button>
                {b.status !== 'COMPLETED' && (
                  <button
                    onClick={() => handleResumeBatch(b.batch_id)}
                    disabled={resuming}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/10 border border-white/20 text-xs font-semibold text-white transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Resume
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* BATCH DETAIL MODAL */}
      <Modal
        isOpen={Boolean(selectedBatch)}
        onClose={() => setSelectedBatch(null)}
        title={
          selectedBatch ? (
            <div className="flex items-center gap-3">
              <span>Batch Audit: {selectedBatch.batch_id}</span>
              <Badge variant={selectedBatch.status === 'COMPLETED' ? 'success' : 'warning'} size="sm">
                {selectedBatch.status}
              </Badge>
            </div>
          ) : (
            'Batch Details'
          )
        }
        maxWidth="2xl"
        footer={
          selectedBatch && selectedBatch.status !== 'COMPLETED' ? (
            <button
              onClick={() => handleResumeBatch(selectedBatch.batch_id)}
              disabled={resuming}
              className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm"
            >
              {resuming ? 'Resuming...' : 'Resume Interrupted Operations'}
            </button>
          ) : (
            <button
              onClick={() => setSelectedBatch(null)}
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-medium"
            >
              Close
            </button>
          )
        }
      >
        {selectedBatch && (
          <div className="space-y-6">
            {/* High Level Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Total Panels</span>
                <span className="text-base font-bold text-white">{selectedBatch.total_panels}</span>
              </div>
              <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Successful</span>
                <span className="text-base font-bold text-emerald-400">{selectedBatch.successful_panels}</span>
              </div>
              <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Verified</span>
                <span className="text-base font-bold text-white">{selectedBatch.verified_panels}</span>
              </div>
              <div className="p-3 rounded-xl bg-ink-950 border border-white/5">
                <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Attempts</span>
                <span className="text-base font-bold text-ink-200">{selectedBatch.total_attempts}</span>
              </div>
            </div>

            {/* Per-Panel Outcomes */}
            <div>
              <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-2">
                Panel Slots & Acceptance States
              </h4>
              <div className="space-y-2">
                {selectedBatch.panel_results?.map((res: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-ink-950 border border-white/5 flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-white">{res.panel_id}</span>
                        <Badge
                          variant={res.status === 'ACCEPTED' ? 'success' : 'warning'}
                          size="sm"
                        >
                          {res.status}
                        </Badge>
                      </div>
                      <p className="text-[10px] text-ink-400 font-mono mt-1">
                        Output Hash: {res.output_content_hash ? `${res.output_content_hash.substring(0, 16)}...` : 'None'}
                      </p>
                    </div>

                    <div className="text-right">
                      <span className="text-[11px] text-ink-400">
                        {res.attempts_count} {res.attempts_count === 1 ? 'Attempt' : 'Attempts'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Attempt History Audit Trail */}
            {selectedBatch.attempt_history?.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-2">
                  Attempt History Ledger (Zero Credential Leakage)
                </h4>
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {selectedBatch.attempt_history.map((att: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg bg-ink-950/70 border border-white/5 text-[11px] flex items-center justify-between"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-white font-semibold">
                            Attempt #{att.attempt_number}
                          </span>
                          <span className="text-ink-400 font-mono text-[10px]">{att.panel_id}</span>
                        </div>
                        <p className="text-ink-400 text-[10px] mt-0.5">
                          Model: {att.model} &bull; Latency: {att.duration_seconds ? `${att.duration_seconds.toFixed(2)}s` : '—'}
                        </p>
                      </div>

                      <Badge
                        variant={att.final_panel_status === 'ACCEPTED' ? 'success' : 'neutral'}
                        size="sm"
                      >
                        {att.final_panel_status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};
