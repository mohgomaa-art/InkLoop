import React, { useEffect, useState } from 'react';
import {
  Clock,
  Plus,
  CheckCircle2,
  GitCommit,
  ShieldCheck,
  Search,
  Sparkles,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface NarrativeTimelineViewProps {
  currentProject: string;
}

export const NarrativeTimelineView: React.FC<NarrativeTimelineViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolvedPanelId, setResolvedPanelId] = useState('panel_01');
  const [resolvedState, setResolvedState] = useState<any | null>(null);

  // New Event Modal
  const [showEventModal, setShowEventModal] = useState(false);
  const [targetEntity, setTargetEntity] = useState('nour');
  const [panelId, setPanelId] = useState('panel_01');
  const [description, setDescription] = useState('');
  const [deltaJson, setDeltaJson] = useState('{\n  "jacket_worn": false,\n  "holding_prop": "ancient_relic"\n}');
  const [submitting, setSubmitting] = useState(false);

  const fetchTimeline = async () => {
    try {
      setLoading(true);
      const evs = await apiClient.getTimeline(currentProject);
      setEvents(evs);
    } catch (err: any) {
      showToast({ type: 'error', title: 'Timeline load failed', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleResolveState = async () => {
    try {
      const res = await apiClient.resolvePanelState(currentProject, resolvedPanelId);
      setResolvedState(res.resolved_state);
      showToast({
        type: 'success',
        title: 'State Resolved',
        message: `Resolved deterministic state for ${resolvedPanelId} across ${events.length} events.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Resolution failed', message: err.message });
    }
  };

  useEffect(() => {
    fetchTimeline();
  }, [currentProject]);

  const handleAppendEvent = async () => {
    try {
      setSubmitting(true);
      let parsed = {};
      try {
        parsed = JSON.parse(deltaJson);
      } catch {
        showToast({ type: 'error', title: 'Invalid JSON', message: 'Delta must be valid JSON.' });
        return;
      }

      await apiClient.appendStateEvent(currentProject, {
        event_id: `ev_${Date.now()}`,
        panel_id: panelId,
        target_entity: targetEntity,
        state_delta: parsed,
        description,
      });

      setShowEventModal(false);
      setDescription('');
      fetchTimeline();
      showToast({ type: 'success', title: 'Event Appended', message: 'Appended to append-only event ledger.' });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to append event', message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <TabCharacterIcon tab="timeline" size={38} />
              Narrative Continuity & State Timeline
            </h1>
            <Badge variant="neutral" size="sm">
              Append-Only
            </Badge>
          </div>
          <p className="text-xs text-ink-300 mt-1">
            Tracks narrative deltas (outfit changes, held props, weather) without rewriting canonical specs.
          </p>
        </div>

        <button
          onClick={() => setShowEventModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Append Narrative Event
        </button>
      </div>

      {/* Main Grid: Events Stream + Deterministic Resolver */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Events Ledger */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
            <GitCommit className="w-4 h-4 text-white" />
            Append-Only Event Ledger ({events.length} Events)
          </h2>

          {loading ? (
            <div className="py-12 text-center text-xs text-ink-400">Loading events...</div>
          ) : events.length === 0 ? (
            <Card className="text-center py-10">
              <Clock className="w-8 h-8 text-ink-500 mx-auto mb-2 opacity-40" />
              <p className="text-xs text-ink-300 font-medium">No narrative events recorded yet.</p>
              <p className="text-[11px] text-ink-500 mt-1">
                The canon remains in its default pristine state. Append events to record panel-specific deltas.
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {events.map((ev, idx) => (
                <div
                  key={ev.event_id || idx}
                  className="p-4 rounded-xl glass-card border border-white/5 hover:border-white/15 transition-all flex items-start gap-4"
                >
                  <div className="p-2 rounded-lg bg-white/5 text-white mt-0.5 shrink-0">
                    <GitCommit className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-white font-semibold">
                          {ev.panel_id || 'Global'}
                        </span>
                        <Badge variant="neutral" size="sm">
                          {ev.target_entity}
                        </Badge>
                      </div>
                      <span className="text-[10px] text-ink-500 font-mono">
                        {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : 'Recorded'}
                      </span>
                    </div>

                    <p className="text-xs text-ink-200 mb-2">{ev.description}</p>

                    {/* State Delta Box */}
                    <div className="p-2 rounded-lg bg-ink-950 font-mono text-[11px] text-white border border-white/5 overflow-x-auto">
                      <pre className="text-[10px]">{JSON.stringify(ev.state_delta, null, 2)}</pre>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Deterministic State Resolver Sidebar */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Deterministic State Resolver
          </h2>

          <Card title="Resolve Panel Delta" subtitle="Evaluates sequence numbers to calculate effective continuity.">
            <div className="space-y-4 pt-2">
              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">Target Panel ID</label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={resolvedPanelId}
                    onChange={(e) => setResolvedPanelId(e.target.value)}
                    className="flex-1 bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-white/20"
                  />
                  <button
                    onClick={handleResolveState}
                    className="px-3 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-medium transition-colors shadow-sm"
                  >
                    Resolve
                  </button>
                </div>
              </div>

              {resolvedState !== null && (
                <div className="space-y-2 pt-2 border-t border-white/5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">Effective Delta</span>
                    <Badge variant="success" size="sm">
                      Deterministic
                    </Badge>
                  </div>
                  <div className="p-3 rounded-xl bg-ink-950 font-mono text-xs text-emerald-400 border border-white/5 max-h-48 overflow-y-auto">
                    <pre className="text-[10px]">{JSON.stringify(resolvedState, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* APPEND EVENT MODAL */}
      <Modal
        isOpen={showEventModal}
        onClose={() => setShowEventModal(false)}
        title="Append Narrative Event"
        maxWidth="md"
        footer={
          <>
            <button
              onClick={() => setShowEventModal(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleAppendEvent}
              disabled={submitting || !description.trim()}
              className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold disabled:opacity-50 shadow-sm"
            >
              {submitting ? 'Appending...' : 'Append to Ledger'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">Target Panel</label>
              <input
                type="text"
                value={panelId}
                onChange={(e) => setPanelId(e.target.value)}
                className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20 font-mono"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">Entity ID</label>
              <input
                type="text"
                value={targetEntity}
                onChange={(e) => setTargetEntity(e.target.value)}
                className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Description</label>
            <input
              type="text"
              placeholder="e.g., Nour takes off jacket due to heat"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">State Delta (JSON)</label>
            <textarea
              rows={4}
              value={deltaJson}
              onChange={(e) => setDeltaJson(e.target.value)}
              className="w-full font-mono bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};
