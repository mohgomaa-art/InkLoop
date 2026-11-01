import React, { useEffect, useState } from 'react';
import {
  Library,
  ShieldCheck,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Award,
  FileText,
  Lock,
  ExternalLink,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface CatalogueViewProps {
  currentProject: string;
}

export const CatalogueView: React.FC<CatalogueViewProps> = () => {
  const { showToast } = useToast();
  const [summary, setSummary] = useState<any | null>(null);
  const [groups, setGroups] = useState<any[]>([]);
  const [licenses, setLicenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedGroup, setSelectedGroup] = useState<any | null>(null);
  const [groupDetail, setGroupDetail] = useState<any | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeTab, setActiveTab] = useState<'taxonomy' | 'licenses'>('taxonomy');

  // Promotion review modal
  const [promoteModalOpen, setPromoteModalOpen] = useState(false);
  const [targetStatus, setTargetStatus] = useState('RESEARCHED');
  const [reviewerId, setReviewerId] = useState('lead_reviewer');
  const [reviewerRole, setReviewerRole] = useState('Lead Architecture Owner');
  const [rationale, setRationale] = useState('');
  const [evidenceIds, setEvidenceIds] = useState('exp_m0_visual_feasibility');
  const [submittingReview, setSubmittingReview] = useState(false);

  const fetchCatalogue = async () => {
    try {
      setLoading(true);
      const [sum, grps, lics] = await Promise.all([
        apiClient.getCatalogueSummary(),
        apiClient.listTaxonomyGroups(),
        apiClient.listLicenses(),
      ]);
      setSummary(sum);
      setGroups(grps);
      setLicenses(lics);
    } catch (err: any) {
      showToast({ type: 'error', title: 'Catalogue Load Failed', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalogue();
  }, []);

  const handleSelectGroup = async (group: any) => {
    setSelectedGroup(group);
    try {
      setLoadingDetail(true);
      const detail = await apiClient.getTaxonomyGroup(group.group_id);
      setGroupDetail(detail);
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to load group detail', message: err.message });
    } finally {
      setLoadingDetail(false);
    }
  };

  const handlePromoteGroup = async () => {
    if (!selectedGroup) return;
    try {
      setSubmittingReview(true);
      const review = await apiClient.promoteGroup({
        group_id: selectedGroup.group_id,
        target_status: targetStatus,
        reviewer_id: reviewerId,
        reviewer_role: reviewerRole,
        rationale,
        verified_evidence_ids: evidenceIds.split(',').map((s) => s.trim()).filter(Boolean),
      });

      setPromoteModalOpen(false);
      fetchCatalogue();
      showToast({
        type: review.decision === 'APPROVED' ? 'success' : 'warning',
        title: `Promotion Decision: ${review.decision}`,
        message: review.decision === 'APPROVED'
          ? `Group promoted to ${targetStatus} with immutable audit record.`
          : review.rationale || 'Failed validation gate.',
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Promotion Request Failed', message: err.message });
    } finally {
      setSubmittingReview(false);
    }
  };

  const filteredGroups = groups.filter((g) => {
    const matchesSearch =
      g.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      g.group_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus =
      statusFilter === 'ALL' || g.coverage_status.toUpperCase() === statusFilter.toUpperCase();
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <TabCharacterIcon tab="catalogue" size={38} />
              Image Knowledge Catalogue & Research Governance
            </h1>
            <Badge variant="neutral" size="sm">
              60 Groups Foundation
            </Badge>
          </div>
          <p className="text-xs text-ink-300 mt-1">
            Truthful coverage register: 60 taxonomy groups &bull; 840 canonical elements &bull; Fail-closed licensing governance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('taxonomy')}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeTab === 'taxonomy'
                ? 'bg-white text-black font-semibold shadow-sm'
                : 'text-ink-400 hover:text-white bg-white/5'
            }`}
          >
            60-Group Taxonomy
          </button>
          <button
            onClick={() => setActiveTab('licenses')}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeTab === 'licenses'
                ? 'bg-white text-black font-semibold shadow-sm'
                : 'text-ink-400 hover:text-white bg-white/5'
            }`}
          >
            Licensing Registry ({licenses.length})
          </button>
        </div>
      </div>

      {/* KPI Tiles */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="p-4 rounded-xl glass-card border border-white/5">
            <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">Total Groups</span>
            <span className="text-xl font-bold text-white">{summary.total_groups}</span>
          </div>
          <div className="p-4 rounded-xl glass-card border border-white/5">
            <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">Canonical Elements</span>
            <span className="text-xl font-bold text-white">{summary.total_canonical_elements}</span>
          </div>
          <div className="p-4 rounded-xl glass-card border border-white/5">
            <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">Tested / Researched</span>
            <span className="text-xl font-bold text-emerald-400">
              {summary.experimentally_tested_count + summary.researched_count}
            </span>
          </div>
          <div className="p-4 rounded-xl glass-card border border-white/5">
            <span className="text-[10px] text-ink-500 uppercase tracking-wider block mb-1">Open Research Gaps</span>
            <span className="text-xl font-bold text-amber-400">{summary.unresearched_count}</span>
          </div>
        </div>
      )}

      {/* TAB 1: 60-GROUP TAXONOMY */}
      {activeTab === 'taxonomy' && (
        <div className="space-y-4">
          {/* Search & Filter Toolbar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-ink-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search groups by name or ID (e.g., lighting, continuity)..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-ink-950 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-white/20"
              />
            </div>

            <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
              {['ALL', 'EXPERIMENTALLY_TESTED', 'RESEARCHED', 'UNRESEARCHED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                    statusFilter === st
                      ? 'bg-white/10 border border-white/20 text-white font-semibold'
                      : 'bg-white/5 text-ink-400 hover:text-white border border-transparent'
                  }`}
                >
                  {st.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Groups Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filteredGroups.map((g) => {
              const isTested = g.coverage_status.toUpperCase() === 'EXPERIMENTALLY_TESTED';
              const isResearched = g.coverage_status.toUpperCase() === 'RESEARCHED';

              return (
                <div
                  key={g.group_id}
                  onClick={() => handleSelectGroup(g)}
                  className="p-4 rounded-2xl glass-card border border-white/5 hover:border-white/15 transition-all cursor-pointer flex flex-col justify-between gap-3"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="text-xs font-bold text-white tracking-tight leading-snug">
                        {g.name}
                      </span>
                      <Badge
                        variant={isTested ? 'success' : isResearched ? 'purple' : 'neutral'}
                        size="sm"
                      >
                        {g.coverage_status.replace('_', ' ')}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-ink-400 line-clamp-2 leading-relaxed">
                      {g.description}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-white/5 text-[10px] text-ink-500 font-mono">
                    <span>{g.element_count} Elements</span>
                    <span className="text-white flex items-center gap-1 font-sans">
                      Inspect &rarr;
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: LICENSES REGISTRY */}
      {activeTab === 'licenses' && (
        <Card title="Licensing & Rights Governance" subtitle="Defensive rights tracking across asset families (ADR-012)">
          <div className="space-y-3 pt-2">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-ink-400">
                    <th className="py-2.5 px-3 font-semibold uppercase tracking-wider text-[10px]">Target Name</th>
                    <th className="py-2.5 px-3 font-semibold uppercase tracking-wider text-[10px]">Target Family</th>
                    <th className="py-2.5 px-3 font-semibold uppercase tracking-wider text-[10px]">License Type</th>
                    <th className="py-2.5 px-3 font-semibold uppercase tracking-wider text-[10px]">Commercial Clearance</th>
                    <th className="py-2.5 px-3 font-semibold uppercase tracking-wider text-[10px]">Attribution Required</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {licenses.map((lic, idx) => (
                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-white">{lic.target_name}</td>
                      <td className="py-2.5 px-3 text-ink-300 font-mono text-[11px]">{lic.target_type}</td>
                      <td className="py-2.5 px-3 text-white font-medium">{lic.license_type}</td>
                      <td className="py-2.5 px-3">
                        <Badge variant={lic.is_commercial_use_permitted ? 'success' : 'danger'} size="sm">
                          {lic.is_commercial_use_permitted ? 'CLEARED' : 'UNAPPROVED'}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-ink-400 text-[11px]">
                        {lic.attribution_required ? 'Yes' : 'No'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      )}

      {/* GROUP DETAIL MODAL */}
      <Modal
        isOpen={Boolean(selectedGroup)}
        onClose={() => {
          setSelectedGroup(null);
          setGroupDetail(null);
        }}
        title={selectedGroup ? selectedGroup.name : 'Group Specification'}
        maxWidth="xl"
        footer={
          <div className="flex items-center justify-between w-full">
            <button
              onClick={() => setPromoteModalOpen(true)}
              className="px-3.5 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm"
            >
              Formal Promotion Review
            </button>
            <button
              onClick={() => {
                setSelectedGroup(null);
                setGroupDetail(null);
              }}
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-medium"
            >
              Close
            </button>
          </div>
        }
      >
        {loadingDetail ? (
          <div className="py-12 text-center text-xs text-ink-400">Loading group details...</div>
        ) : groupDetail ? (
          <div className="space-y-5 text-xs">
            <div className="p-3 rounded-xl bg-ink-950 border border-white/5 flex items-center justify-between">
              <div>
                <span className="font-mono text-ink-400 block text-[10px]">Group ID: {groupDetail.group_id}</span>
                <span className="text-white font-medium text-xs mt-0.5 block">{groupDetail.canonical_name}</span>
              </div>
              <Badge variant="neutral" size="sm">
                {groupDetail.coverage_status?.replace('_', ' ')}
              </Badge>
            </div>

            {/* Canonical Elements */}
            <div>
              <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-2">
                Canonical Elements ({groupDetail.canonical_elements?.length})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {groupDetail.canonical_elements?.map((el: string, idx: number) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 rounded-lg bg-ink-950 border border-white/5 text-[11px] text-ink-300 font-mono"
                  >
                    {el}
                  </span>
                ))}
              </div>
            </div>

            {/* Research Gaps Notice */}
            {groupDetail.research_gaps?.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2">
                  Active Research Gaps
                </h4>
                <ul className="list-disc list-inside space-y-1 text-ink-300 text-[11px]">
                  {groupDetail.research_gaps.map((gap: string, idx: number) => (
                    <li key={idx}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : null}
      </Modal>

      {/* PROMOTION REVIEW MODAL */}
      <Modal
        isOpen={promoteModalOpen}
        onClose={() => setPromoteModalOpen(false)}
        title="Submit Status Promotion Request"
        maxWidth="md"
        footer={
          <>
            <button
              onClick={() => setPromoteModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handlePromoteGroup}
              disabled={submittingReview || !rationale.trim()}
              className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold disabled:opacity-50 shadow-sm"
            >
              {submittingReview ? 'Submitting Review...' : 'Submit Audit Review'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-ink-300 leading-relaxed">
            In accordance with ADR-012, status promotion requires verified evidence references and role-authorized rationale. Baseless promotions fail closed.
          </p>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Target Status</label>
            <select
              value={targetStatus}
              onChange={(e) => setTargetStatus(e.target.value)}
              className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
            >
              <option value="RESEARCHED">RESEARCHED (Theory + Guidelines)</option>
              <option value="VALIDATED">VALIDATED (Requires 2+ passing empirical experiments)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Reviewer Role</label>
            <input
              type="text"
              value={reviewerRole}
              onChange={(e) => setReviewerRole(e.target.value)}
              className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Audit Rationale</label>
            <textarea
              rows={3}
              placeholder="State exact source backing or experimental trial..."
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">
              Verified Evidence IDs (comma separated)
            </label>
            <input
              type="text"
              value={evidenceIds}
              onChange={(e) => setEvidenceIds(e.target.value)}
              className="w-full font-mono bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};
