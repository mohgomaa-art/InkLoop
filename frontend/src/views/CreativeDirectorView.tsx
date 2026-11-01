import React, { useState, useEffect } from 'react';
import {
  Compass,
  BookOpen,
  Users,
  Layers,
  Palette,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Check,
  X,
  FileText,
  Eye,
  Sliders,
  Send,
  Loader2,
  FileCode,
  Copy,
  BookPlus,
  UserPlus,
  Sparkles,
  Cpu,
  Plus,
  Upload,
  Image as ImageIcon,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { NavTab } from '../components/common/Sidebar';
import {
  CreativeMode,
  CreativePackage,
  ValidationResult,
  LocationSpec,
  LocationStateVariant,
} from '../types/creative';

interface CreativeDirectorViewProps {
  currentProject: string;
  onNavigate?: (tab: NavTab) => void;
  initialTab?: 'story' | 'locations';
}

export const CreativeDirectorView: React.FC<CreativeDirectorViewProps> = ({ currentProject, onNavigate, initialTab = 'story' }) => {
  const [mode, setMode] = useState<CreativeMode>('full_production_bible');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [commitSuccess, setCommitSuccess] = useState<string | null>(null);
  const [packageData, setPackageData] = useState<CreativePackage | null>(null);
  const [committedChars, setCommittedChars] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<
    'story' | 'characters' | 'relationships' | 'world' | 'locations' | 'narrative' | 'style' | 'sheets' | 'contracts'
  >(initialTab);
  const [selectedCharacterId, setSelectedCharacterId] = useState<string>('nour');

  // Add Character modal state
  const [showAddCharModal, setShowAddCharModal] = useState(false);
  const [newCharName, setNewCharName] = useState('');
  const [newCharRole, setNewCharRole] = useState('Supporting Character');
  const [newCharAge, setNewCharAge] = useState('20-25');
  const [newCharDesc, setNewCharDesc] = useState('');
  const [newCharInvariants, setNewCharInvariants] = useState('');
  const [newCharGarments, setNewCharGarments] = useState('');
  const [newCharCommitToCanon, setNewCharCommitToCanon] = useState(true);
  const [creatingChar, setCreatingChar] = useState(false);

  const [locationDraft, setLocationDraft] = useState<LocationSpec | null>(null);
  const [savingLocation, setSavingLocation] = useState(false);
  const [locationSaveError, setLocationSaveError] = useState<string | null>(null);
  const [locationVariantDraft, setLocationVariantDraft] = useState<Omit<LocationStateVariant, 'variant_id'>>({ name: '', visible_changes: [] });
  const [locationVariantChanges, setLocationVariantChanges] = useState('');

  // Prompt compiler sandbox state
  const [compilerAction, setCompilerAction] = useState('Nour running across flooded rooftops in rain at midnight');
  const [compilerEmotion, setCompilerEmotion] = useState('determined');
  const [compilerActionShot, setCompilerActionShot] = useState(true);
  const [compiledResult, setCompiledResult] = useState<{ positive: string; negative: string } | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  // Load existing package and story bible on project change
  useEffect(() => {
    let isMounted = true;
    const loadExisting = async () => {
      try {
        const [pkg, bible] = await Promise.all([
          apiClient.getCreativePackage(currentProject).catch(() => null),
          apiClient.getProjectBible(currentProject).catch(() => null),
        ]);
        if (isMounted) {
          if (pkg) {
            setPackageData(pkg);
            const firstChar = Object.keys(pkg.characters)[0];
            if (firstChar) setSelectedCharacterId(firstChar);
          } else {
            setPackageData(null);
          }
          if (bible?.characters) {
            setCommittedChars(bible.characters);
          } else {
            setCommittedChars({});
          }
        }
      } catch {
        if (isMounted) {
          setPackageData(null);
          setCommittedChars({});
        }
      }
    };
    loadExisting();
    return () => {
      isMounted = false;
    };
  }, [currentProject]);

  const handleDevelop = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const pkg = await apiClient.developCreativeUniverse({
        project_id: currentProject,
        user_prompt: prompt,
        mode,
      });
      setPackageData(pkg);
      const firstChar = Object.keys(pkg.characters)[0];
      if (firstChar) setSelectedCharacterId(firstChar);
    } catch (err: any) {
      setError(err?.payload?.message || err?.message || 'Synthesis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveCanon = async () => {
    if (!packageData) return;
    setCommitting(true);
    setError(null);
    setCommitSuccess(null);
    try {
      await apiClient.approveCreativeCanon({
        project_id: currentProject,
        character_ids_to_commit: Object.keys(packageData.characters),
        commit_style: true,
      });
      // Refresh package and project bible
      const [reloadedPkg, reloadedBible] = await Promise.all([
        apiClient.getCreativePackage(currentProject),
        apiClient.getProjectBible(currentProject),
      ]);
      setPackageData(reloadedPkg);
      if (reloadedBible?.characters) {
        setCommittedChars(reloadedBible.characters);
      }
      setCommitSuccess(
        `Successfully committed all ${Object.keys(packageData.characters).length} characters and visual style to Story Bible canon! They are now active in the Agent Studio.`
      );
    } catch (err: any) {
      setError(err?.payload?.message || err?.message || 'Failed to commit canon');
    } finally {
      setCommitting(false);
    }
  };

  const handleCommitSingleCharacter = async (charId: string) => {
    if (!packageData || !packageData.characters[charId]) return;
    setCommitting(true);
    setError(null);
    setCommitSuccess(null);
    const charName = packageData.characters[charId].name;
    try {
      await apiClient.approveCreativeCanon({
        project_id: currentProject,
        character_ids_to_commit: [charId],
        commit_style: false,
      });
      // Refresh package and project bible
      const [reloadedPkg, reloadedBible] = await Promise.all([
        apiClient.getCreativePackage(currentProject),
        apiClient.getProjectBible(currentProject),
      ]);
      setPackageData(reloadedPkg);
      if (reloadedBible?.characters) {
        setCommittedChars(reloadedBible.characters);
      }
      setCommitSuccess(
        `Character '${charName}' committed to Story Bible canon! You can now chat and generate with '${charName}' in the Agent Studio.`
      );
    } catch (err: any) {
      setError(err?.payload?.message || err?.message || `Failed to commit ${charName} to canon`);
    } finally {
      setCommitting(false);
    }
  };

  const [generatingAnchor, setGeneratingAnchor] = useState<string | null>(null);
  const [anchorSuccessMsg, setAnchorSuccessMsg] = useState<{ id: string; text: string; isError?: boolean } | null>(null);

  const handleGenerateAnchor = async (characterId: string) => {
    setGeneratingAnchor(characterId);
    setAnchorSuccessMsg(null);
    try {
      if (!committedChars[characterId]) {
        await handleCommitSingleCharacter(characterId);
      }
      const res = await fetch(`/api/v1/projects/${currentProject}/characters/${characterId}/generate-anchor`, {
        method: 'POST',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || 'Failed to generate anchor portrait');
      }
      const data = await res.json();
      const updatedBible = await apiClient.getProjectBible(currentProject);
      if (updatedBible?.characters) {
        setCommittedChars(updatedBible.characters);
      }
      setAnchorSuccessMsg({ id: characterId, text: `Canonical reference anchor generated (${data.asset_id}). Agent is now ready to generate panels!` });
    } catch (err: any) {
      setAnchorSuccessMsg({ id: characterId, text: err.message, isError: true });
    } finally {
      setGeneratingAnchor(null);
    }
  };

  const handleUploadAnchor = async (characterId: string, file: File) => {
    setGeneratingAnchor(characterId);
    setAnchorSuccessMsg(null);
    try {
      if (!committedChars[characterId]) {
        await handleCommitSingleCharacter(characterId);
      }
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`/api/v1/projects/${currentProject}/characters/${characterId}/upload-anchor`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || 'Failed to upload anchor');
      }
      const data = await res.json();
      const updatedBible = await apiClient.getProjectBible(currentProject);
      if (updatedBible?.characters) {
        setCommittedChars(updatedBible.characters);
      }
      setAnchorSuccessMsg({ id: characterId, text: `Anchor uploaded and registered (${data.asset_id})!` });
    } catch (err: any) {
      setAnchorSuccessMsg({ id: characterId, text: err.message, isError: true });
    } finally {
      setGeneratingAnchor(null);
    }
  };

  const handleCreateCustomCharacter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCharName.trim()) return;
    setCreatingChar(true);
    setError(null);
    try {
      const invs = newCharInvariants
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);
      const garms = newCharGarments
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);

      const updatedPkg = await apiClient.addCreativeCharacter({
        project_id: currentProject,
        name: newCharName.trim(),
        role: newCharRole,
        age_range: newCharAge,
        narrative_function: newCharDesc.trim(),
        visual_invariants: invs.length > 0 ? invs : undefined,
        garments: garms.length > 0 ? garms : undefined,
        commit_to_canon: newCharCommitToCanon,
      });

      setPackageData(updatedPkg);
      const newCid = newCharName.trim().toLowerCase().replace(/\s+/g, '_');
      setSelectedCharacterId(newCid);
      setActiveTab('characters');

      // Refresh project bible
      const reloadedBible = await apiClient.getProjectBible(currentProject).catch(() => null);
      if (reloadedBible?.characters) {
        setCommittedChars(reloadedBible.characters);
      }

      setCommitSuccess(
        newCharCommitToCanon
          ? `Character '${newCharName.trim()}' created and committed to Story Bible canon! You can now chat and generate with '${newCharName.trim()}' in the Agent Studio.`
          : `Character '${newCharName.trim()}' added to Universe cast!`
      );
      setShowAddCharModal(false);
      setNewCharName('');
      setNewCharDesc('');
      setNewCharInvariants('');
      setNewCharGarments('');
    } catch (err: any) {
      setError(err?.payload?.message || err?.message || 'Failed to add character');
    } finally {
      setCreatingChar(false);
    }
  };

  const openLocationEditor = (location?: LocationSpec, duplicate = false) => {
    const baseId = location?.location_id || 'new_location';
    let nextId = duplicate ? `${baseId}_copy` : baseId;
    let suffix = 2;
    while (duplicate && packageData?.world_bible.locations[nextId]) {
      nextId = `${baseId}_copy_${suffix++}`;
    }
    setLocationSaveError(null);
    setLocationDraft(location ? {
      ...location,
      location_id: nextId,
      name: duplicate ? `${location.name} Copy` : location.name,
      source_location_id: duplicate ? location.location_id : location.source_location_id,
      version: duplicate ? undefined : location.version,
      version_history: duplicate ? [] : location.version_history,
    } : {
      location_id: '',
      name: '',
      atmosphere: '',
      spatial_layout: '',
      visual_anchors: [],
      lighting_conditions: '',
      narrative_use: '',
      continuity_rules: [],
      aliases: [],
      location_type: '',
      geographic_context: '',
      scale: '',
      zones: [],
      environment_details: {},
      state_variants: [],
    });
    setLocationVariantDraft({ name: '', visible_changes: [] });
    setLocationVariantChanges('');
  };

  const saveLocation = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!packageData || !locationDraft) return;
    const locationId = locationDraft.location_id.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '');
    if (!locationId || !locationDraft.name.trim()) {
      setLocationSaveError('Enter a stable location ID and a name before saving.');
      return;
    }
    const payload: LocationSpec = {
      ...locationDraft,
      location_id: locationId,
      name: locationDraft.name.trim(),
      state_variants: locationDraft.state_variants || [],
    };
    setSavingLocation(true);
    setLocationSaveError(null);
    try {
      const saved = await apiClient.saveCreativeLocation(currentProject, locationId, packageData.version, locationDraft.version, payload);
      setPackageData(saved);
      setLocationDraft(null);
    } catch (err: any) {
      setLocationSaveError(err?.payload?.message || err?.message || 'The location could not be saved. Reload the project and try again.');
    } finally {
      setSavingLocation(false);
    }
  };

  const deleteLocation = async (locationId: string) => {
    if (!packageData || !window.confirm(`Delete location "${packageData.world_bible.locations[locationId]?.name || locationId}"? This cannot be undone.`)) return;
    setError(null);
    try {
      const saved = await apiClient.deleteCreativeLocation(currentProject, locationId, packageData.version);
      setPackageData(saved);
    } catch (err: any) {
      setError(err?.payload?.message || err?.message || 'The location could not be deleted.');
    }
  };

  const handleValidate = async () => {
    if (!packageData) return;
    setLoading(true);
    try {
      const val = await apiClient.validateCreativeCoherence(currentProject);
      setPackageData({
        ...packageData,
        validation: val,
      });
    } catch (err: any) {
      setError(err?.payload?.message || err?.message || 'Validation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCompilePrompt = async () => {
    if (!packageData) return;
    setCompiling(true);
    try {
      const res = await apiClient.compileCreativePrompt({
        project_id: currentProject,
        character_id: selectedCharacterId,
        scene_description: compilerAction,
        emotion: compilerEmotion,
        is_action_shot: compilerActionShot,
      });
      setCompiledResult({
        positive: res.positive_prompt,
        negative: res.negative_prompt,
      });
    } catch (err: any) {
      setError(err?.payload?.message || err?.message || 'Failed to compile prompt');
    } finally {
      setCompiling(false);
    }
  };

  const handleCopyPositive = () => {
    if (!compiledResult?.positive) return;
    navigator.clipboard.writeText(compiledResult.positive);
    setCopiedPrompt(true);
    setTimeout(() => setCopiedPrompt(false), 2000);
  };

  const sampleStarters = [
    {
      label: 'Dark Fantasy Flooded City',
      text: 'A dark fantasy manhwa titled "Echo Tides" about a quiet courier named Nour who can hear memories trapped inside broken objects in a flooded metropolis. Grounded emotional tone, rich ink linework, muted aquatic teal palette.',
    },
    {
      label: 'Cyberpunk Memory Courier',
      text: 'Sci-fi cyberpunk noir webtoon about an 18-year-old courier with a white hair streak who smuggles black-market brain fragments across sunken neon skyways. High stakes, sharp linework, intense psychological tension.',
    },
    {
      label: 'Supernatural Mystery Relic Shop',
      text: 'A supernatural mystery comic about an antique restorer who uncovers murdered souls trapped inside clockwork mechanisms. Atmospheric Gothic tone, deep contrast screentones, and deliberate pacing.',
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 md:p-6 text-ink-100">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="flex items-start gap-3.5">
            <TabCharacterIcon tab="creative" size={44} className="mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white">
                  Creative Director & Universe Builder
                </h1>
                <Badge variant="studio" size="sm">
                  v1.0 · Monotonic
                </Badge>
                {packageData && (
                  packageData.synthesis_source === 'live_ai' ? (
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      Live AI Model (muse-spark-1.3)
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full bg-white/5 text-ink-300 border border-white/10 text-xs font-medium flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5" />
                      Deterministic Universe Engine
                    </span>
                  )
                )}
              </div>
              <p className="text-xs text-ink-400 mt-1">
                Transforms natural language briefs into versioned Story Bibles, character invariant profiles, and downstream generation contracts.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddCharModal(true)}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-ink-800 hover:bg-ink-750 border border-white/10 text-white flex items-center gap-1.5 transition-colors shadow-sm"
            title="Create and add an individual character directly into Universe & Story Bible canon"
          >
            <UserPlus className="w-3.5 h-3.5 text-emerald-400" />
            <span>+ Add Character</span>
          </button>
          {packageData && (
            <>
              <button
                onClick={handleValidate}
                disabled={loading || committing}
                className="px-3.5 py-1.5 text-xs font-medium rounded-lg bg-ink-800 hover:bg-ink-750 border border-white/10 text-ink-200 hover:text-white flex items-center gap-1.5 transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Verify Coherence</span>
              </button>
              <button
                onClick={handleApproveCanon}
                disabled={loading || committing}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#eee] hover:bg-white text-[#141414] flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
                title="Commit all synthesized characters and visual style to authoritative Story Bible canon"
              >
                {committing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <BookPlus className="w-3.5 h-3.5" />}
                <span>Commit Universe to Story Bible</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Commit Success Notification Banner */}
      {commitSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between gap-3 animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{commitSuccess}</span>
          </div>
          {onNavigate && (
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => onNavigate('bible')}
                className="px-3 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 font-semibold text-xs flex items-center gap-1 transition-colors border border-emerald-500/30"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>View in Story Bible</span>
                <span>↗</span>
              </button>
              <button
                onClick={() => onNavigate('agent')}
                className="px-3 py-1 rounded-lg bg-emerald-400 hover:bg-emerald-300 text-ink-950 font-semibold text-xs flex items-center gap-1 transition-colors shadow-sm"
              >
                <span>Go to Agent Studio</span>
                <span>↗</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Human Approval Required Banner */}
      {packageData?.has_pending_approval && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-amber-300">Pending Human Canon Mutation Approval</h3>
              <p className="text-xs text-ink-300 mt-0.5">
                The Creative Director detected proposals that modify approved Story Bible invariants. Per InkLoop defensive invariants, canon will not silently mutate without your explicit approval.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleApproveCanon}
              disabled={loading}
              className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-amber-400 hover:bg-amber-300 text-ink-950 flex items-center gap-1.5 transition-colors shadow-sm"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Approve & Commit to Canon</span>
            </button>
          </div>
        </div>
      )}

      {/* Input Composer Section */}
      <Card className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-semibold text-ink-400 uppercase tracking-wider">Mode:</span>
            <div className="flex flex-wrap p-1 rounded-xl bg-ink-950 border border-white/10 gap-1">
              {(
                [
                  { id: 'quick_concept', label: 'Quick Concept' },
                  { id: 'full_production_bible', label: 'Full Production Bible' },
                  { id: 'character_deep_dive', label: 'Character Focus' },
                  { id: 'ensemble_builder', label: 'Ensemble' },
                  { id: 'visual_worldbuilding', label: 'Visual Style' },
                ] as const
              ).map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  className={`px-3 py-1 text-xs rounded-lg font-medium transition-all ${
                    mode === m.id
                      ? 'bg-ink-800 text-white border border-white/15 shadow-sm'
                      : 'text-ink-400 hover:text-ink-200 hover:bg-ink-900/50'
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Textarea */}
        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            placeholder="Describe your story, world, characters, visual medium, or emotional tone in natural language..."
            className="w-full p-3.5 rounded-xl bg-ink-950 border border-white/10 text-sm text-ink-100 placeholder-ink-500 focus:outline-none focus:border-white/30 transition-all font-sans leading-relaxed"
          />
        </div>

        {/* Production Presets */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-ink-500 font-medium">Production Presets:</span>
          {sampleStarters.map((s, idx) => (
            <button
              key={idx}
              onClick={() => setPrompt(s.text)}
              className="text-xs px-2.5 py-1 rounded-lg bg-ink-950 hover:bg-ink-800 text-ink-300 hover:text-white border border-white/10 transition-colors"
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-between pt-1 border-t border-white/5">
          <span className="text-xs text-ink-500">
            16-stage pipeline · Live AI synthesis with deterministic contract compilation
          </span>
          <button
            onClick={handleDevelop}
            disabled={loading || !prompt.trim()}
            className="px-4 py-2 rounded-xl bg-[#eee] hover:bg-white text-[#141414] text-xs font-semibold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Synthesizing Production Bible...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Develop Universe</span>
              </>
            )}
          </button>
        </div>
      </Card>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Package Inspector & Tabs */}
      {packageData && (
        <div className="space-y-5">
          {/* Deliverables Navigation Tabs */}
          <div className="flex items-center gap-1 border-b border-white/10 overflow-x-auto pb-1">
            {[
              { id: 'story', label: 'Story Bible', icon: <BookOpen className="w-4 h-4" /> },
              { id: 'characters', label: `Characters (${Object.keys(packageData.characters).length})`, icon: <Users className="w-4 h-4" /> },
              { id: 'relationships', label: 'Ensemble Graph', icon: <Layers className="w-4 h-4" /> },
              { id: 'world', label: 'World & Magic Rules', icon: <Compass className="w-4 h-4" /> },
              { id: 'locations', label: `Location Studio (${Object.keys(packageData.world_bible.locations).length})`, icon: <Compass className="w-4 h-4" /> },
              { id: 'narrative', label: 'Narrative Structure', icon: <FileText className="w-4 h-4" /> },
              { id: 'style', label: 'Visual Style', icon: <Palette className="w-4 h-4" /> },
              { id: 'sheets', label: 'Sheet Plans', icon: <Eye className="w-4 h-4" /> },
              { id: 'contracts', label: 'Contracts & QA', icon: <ShieldCheck className="w-4 h-4" /> },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? 'bg-ink-800 text-white border border-white/15 shadow-sm'
                    : 'text-ink-400 hover:text-ink-200 hover:bg-ink-800/40'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* TAB 1: STORY BIBLE */}
          {activeTab === 'story' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="md:col-span-2 space-y-4">
                <Card className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-bold text-white">{packageData.story_bible.title}</h2>
                    <Badge variant="studio" size="sm">
                      {packageData.story_bible.genre}
                    </Badge>
                  </div>
                  <p className="text-sm text-ink-200 italic border-l-2 border-white/20 pl-3 py-0.5 font-serif">
                    "{packageData.story_bible.logline}"
                  </p>
                  <div className="pt-2">
                    <h4 className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-1.5">Synopsis</h4>
                    <p className="text-xs text-ink-300 leading-relaxed font-sans">
                      {packageData.story_bible.synopsis_expanded}
                    </p>
                  </div>
                </Card>

                <Card className="space-y-3">
                  <h4 className="text-xs font-semibold text-ink-400 uppercase tracking-wider">Themes & Motifs</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {packageData.story_bible.themes.map((t, idx) => (
                      <Badge key={idx} variant="neutral" size="sm">
                        {t}
                      </Badge>
                    ))}
                    {packageData.story_bible.motifs.map((m, idx) => (
                      <span key={idx} className="text-xs px-2.5 py-1 rounded-lg bg-ink-950 text-ink-400 border border-white/5 italic">
                        #{m}
                      </span>
                    ))}
                  </div>
                </Card>
              </div>

              {/* Story Spec Metadata */}
              <div className="space-y-4">
                <Card className="space-y-3 text-xs">
                  <h4 className="font-semibold text-ink-400 uppercase tracking-wider">Production Boundaries</h4>
                  <div className="space-y-2.5">
                    <div>
                      <span className="text-ink-500 block">Central Dramatic Question:</span>
                      <span className="text-ink-200 font-medium">{packageData.story_bible.central_dramatic_question}</span>
                    </div>
                    <div>
                      <span className="text-ink-500 block">Stakes:</span>
                      <span className="text-ink-300">{packageData.story_bible.stakes}</span>
                    </div>
                    <div>
                      <span className="text-ink-500 block">Pacing & Voice:</span>
                      <span className="text-ink-300">{packageData.story_bible.narrative_voice} ({packageData.story_bible.pacing_and_rhythm})</span>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* TAB 2: CHARACTERS */}
          {activeTab === 'characters' && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
              {/* Character Selector List */}
              <div className="space-y-2">
                <div className="flex items-center justify-between px-1 mb-1">
                  <span className="text-xs font-semibold text-ink-400 uppercase tracking-wider block">Cast Members</span>
                  <button
                    onClick={() => setShowAddCharModal(true)}
                    className="px-2 py-0.5 text-[11px] font-medium rounded-md bg-ink-800 hover:bg-ink-750 text-ink-200 hover:text-white border border-white/10 flex items-center gap-1 transition-colors"
                    title="Add a new character to this universe"
                  >
                    <Plus className="w-3 h-3 text-emerald-400" />
                    <span>Add</span>
                  </button>
                </div>
                {Object.entries(packageData.characters).map(([cid, char]) => (
                  <button
                    key={cid}
                    onClick={() => setSelectedCharacterId(cid)}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      selectedCharacterId === cid
                        ? 'bg-ink-800 border-white/20 shadow-sm'
                        : 'bg-ink-900/60 border-white/10 hover:bg-ink-800/40 text-ink-400'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        {committedChars[cid] && (
                          <span title="Committed to Story Bible Canon" className="text-emerald-400 text-xs font-bold">✓</span>
                        )}
                        <span className="font-bold text-sm text-white">{char.name}</span>
                      </div>
                      <Badge variant={committedChars[cid] ? "success" : "neutral"} size="sm">
                        {char.role}
                      </Badge>
                    </div>
                    <p className="text-xs text-ink-400 truncate mt-1">{char.narrative_function}</p>
                  </button>
                ))}
              </div>

              {/* Selected Character Profile Card */}
              {(() => {
                const activeId = packageData.characters[selectedCharacterId]
                  ? selectedCharacterId
                  : Object.keys(packageData.characters)[0];
                const c = activeId ? packageData.characters[activeId] : null;
                if (!c) return null;
                const isCommitted = Boolean(committedChars[activeId]);
                return (
                  <div className="md:col-span-3 space-y-4">
                    <Card className="space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <h3 className="text-lg font-bold text-white">{c.name}</h3>
                          <p className="text-xs text-ink-400">{c.narrative_function} · Age: {c.age_range}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          {isCommitted ? (
                            <>
                              <Badge variant="success" size="sm">
                                <Check className="w-3 h-3 mr-1 inline" />
                                In Story Bible Canon
                              </Badge>
                              {onNavigate && (
                                <>
                                  <button
                                    onClick={() => onNavigate('bible')}
                                    className="px-2.5 py-1 text-xs rounded-lg bg-ink-800 hover:bg-ink-750 text-ink-200 hover:text-white border border-white/10 flex items-center gap-1 transition-colors"
                                    title={`View ${c.name} in Story Bible & Canon Studio`}
                                  >
                                    <BookOpen className="w-3 h-3 text-ink-400" />
                                    <span>Story Bible</span>
                                    <span className="text-[10px]">↗</span>
                                  </button>
                                  <button
                                    onClick={() => onNavigate('agent')}
                                    className="px-2.5 py-1 text-xs rounded-lg bg-ink-800 hover:bg-ink-750 text-ink-200 hover:text-white border border-white/10 flex items-center gap-1 transition-colors"
                                    title={`Start creation session with ${c.name} in Agent Studio`}
                                  >
                                    <Send className="w-3 h-3 text-emerald-400" />
                                    <span>Chat in Agent</span>
                                    <span className="text-[10px]">↗</span>
                                  </button>
                                </>
                              )}
                            </>
                          ) : (
                            <button
                              onClick={() => handleCommitSingleCharacter(activeId)}
                              disabled={loading || committing}
                              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#eee] hover:bg-white text-[#141414] flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
                              title={`Commit ${c.name} to Story Bible canon so Agent and downstream tools can use this character`}
                            >
                              {committing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserPlus className="w-3.5 h-3.5" />}
                              <span>Import to Story Bible & Agent</span>
                            </button>
                          )}
                        </div>
                      </div>

                        {/* Canonical Reference Anchor Card */}
                        {(() => {
                          const bibleChar = committedChars[activeId];
                          const refAnchor = bibleChar?.reference_assets?.[0];
                          const isGenerating = generatingAnchor === activeId;
                          return (
                            <div className="p-3.5 rounded-xl bg-ink-950 border border-white/10 space-y-3">
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-2.5">
                                <div className="flex items-center gap-2">
                                  <ImageIcon className="w-4 h-4 text-ink-300" />
                                  <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                                    Canonical Reference Anchor
                                  </h4>
                                </div>
                                {refAnchor ? (
                                  <Badge variant="success" size="sm">
                                    <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                                    Anchor Active
                                  </Badge>
                                ) : (
                                  <Badge variant="neutral" size="sm">
                                    <AlertTriangle className="w-3 h-3 mr-1 inline text-amber-400" />
                                    No Anchor Image
                                  </Badge>
                                )}
                              </div>

                              {anchorSuccessMsg && anchorSuccessMsg.id === activeId && (
                                <div className={`p-2.5 rounded-lg text-xs flex items-center gap-2 ${
                                  anchorSuccessMsg.isError ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20' : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                                }`}>
                                  {anchorSuccessMsg.isError ? <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> : <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />}
                                  <span>{anchorSuccessMsg.text}</span>
                                </div>
                              )}

                              {refAnchor ? (
                                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1">
                                  <div className="flex items-center gap-3">
                                    <img
                                      src={`/api/v1/assets/${refAnchor.asset_id}/file`}
                                      alt={c.name}
                                      className="w-14 h-16 rounded-lg object-cover bg-ink-900 border border-white/15 shadow-sm"
                                      onError={(e) => {
                                        (e.currentTarget as HTMLElement).style.display = 'none';
                                      }}
                                    />
                                    <div className="space-y-0.5 text-xs">
                                      <div className="font-mono text-white font-semibold">{refAnchor.asset_id}</div>
                                      <div className="font-mono text-ink-400 text-2xs truncate max-w-xs">
                                        SHA: {refAnchor.expected_hash?.slice(0, 16)}...
                                      </div>
                                      <div className="text-emerald-400 text-2xs">✓ Identity reference locked for Agent & panel synthesis</div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <button
                                      onClick={() => handleGenerateAnchor(activeId)}
                                      disabled={isGenerating}
                                      className="px-2.5 py-1.5 text-xs rounded-lg bg-ink-800 hover:bg-ink-750 text-ink-200 hover:text-white border border-white/10 flex items-center gap-1.5 transition-colors disabled:opacity-50"
                                      title="Regenerate character model sheet anchor portrait"
                                    >
                                      {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-amber-400" />}
                                      <span>Re-generate</span>
                                    </button>
                                    <label className="px-2.5 py-1.5 text-xs rounded-lg bg-ink-800 hover:bg-ink-750 text-ink-200 hover:text-white border border-white/10 flex items-center gap-1.5 cursor-pointer transition-colors">
                                      <Upload className="w-3.5 h-3.5 text-ink-400" />
                                      <span>Replace</span>
                                      <input
                                        type="file"
                                        accept="image/*"
                                        className="hidden"
                                        onChange={(e) => {
                                          const file = e.target.files?.[0];
                                          if (file) handleUploadAnchor(activeId, file);
                                        }}
                                      />
                                    </label>
                                  </div>
                                </div>
                              ) : (
                                <div className="space-y-2.5">
                                  <p className="text-xs text-ink-400 leading-relaxed">
                                    This character has declared visual invariants, but no verified reference portrait anchor on file.
                                    Downstream tools and Agent Studio require an anchor before generating panels to preserve facial identity.
                                  </p>
                                  <div className="flex flex-wrap items-center gap-2 pt-1">
                                    <button
                                      onClick={() => handleGenerateAnchor(activeId)}
                                      disabled={isGenerating}
                                      className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-white text-black hover:bg-ink-200 flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
                                    >
                                      {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                                      <span>Generate Anchor Portrait</span>
                                    </button>
                                    <label className="px-3 py-2 text-xs rounded-lg bg-ink-800 hover:bg-ink-750 text-ink-200 hover:text-white border border-white/10 flex items-center gap-1.5 cursor-pointer transition-colors">
                                      <Upload className="w-3.5 h-3.5 text-ink-400" />
                                      <span>Upload Reference Image</span>
                                      <input
                                        type="file"
                                        accept="image/*"
                                        className="hidden"
                                        onChange={(e) => {
                                          const file = e.target.files?.[0];
                                          if (file) handleUploadAnchor(activeId, file);
                                        }}
                                      />
                                    </label>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })()}

                        {/* Mandatory Invariants */}
                        <div>
                          <h4 className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-white" />
                            <span>Mandatory Visual Invariants (Compiled into Every Prompt)</span>
                          </h4>
                          <div className="space-y-1.5">
                            {c.visual_invariants.map((inv, idx) => (
                              <div key={idx} className="flex items-center gap-2 p-2.5 rounded-lg bg-ink-950 border border-white/10 text-xs text-ink-200">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                                <span>{inv}</span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Wardrobe & Base Outfit */}
                        {c.base_outfit && (
                          <div className="p-3.5 rounded-xl bg-ink-950 border border-white/10 text-xs space-y-1.5">
                            <span className="font-semibold text-ink-400 uppercase tracking-wider block">Default Wardrobe:</span>
                            <div className="flex flex-wrap gap-1.5">
                              {c.base_outfit.garments.map((g, idx) => (
                                <span key={idx} className="px-2 py-0.5 rounded-md bg-ink-800 text-ink-300 border border-white/5">
                                  {g}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Forbidden Visual Drift */}
                        <div>
                          <h4 className="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                            <X className="w-3.5 h-3.5" />
                            <span>Forbidden Visual Drift (Negative Prompt Invariants)</span>
                          </h4>
                          <div className="flex flex-wrap gap-1.5">
                            {c.forbidden_visual_drift.map((drift, idx) => (
                              <span key={idx} className="text-xs px-2.5 py-0.5 rounded-md bg-rose-500/10 text-rose-300 border border-rose-500/20">
                                {drift}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Psychological Invariants */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-3 border-t border-white/10">
                          <div>
                            <span className="text-ink-500 block">External Goal:</span>
                            <span className="text-ink-200">{c.external_goal}</span>
                          </div>
                          <div>
                            <span className="text-ink-500 block">Internal Need:</span>
                            <span className="text-ink-200">{c.internal_need}</span>
                          </div>
                          <div>
                            <span className="text-ink-500 block">Core Fear:</span>
                            <span className="text-ink-200">{c.core_fear}</span>
                          </div>
                          <div>
                            <span className="text-ink-500 block">Wound / Ghost:</span>
                            <span className="text-ink-200">{c.wound_or_ghost}</span>
                          </div>
                        </div>
                      </Card>
                    </div>
                  );
                })()}
            </div>
          )}

          {/* TAB 3: RELATIONSHIPS */}
          {activeTab === 'relationships' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {packageData.relationship_graph.edges.map((edge, idx) => (
                  <Card key={idx} className="space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-sm capitalize">
                        {edge.source_character_id} ↔ {edge.target_character_id}
                      </span>
                      <Badge variant="studio" size="sm">
                        {edge.status}
                      </Badge>
                    </div>
                    <p className="text-ink-300"><span className="text-ink-500">Core Dynamic:</span> {edge.core_dynamic}</p>
                    <p className="text-ink-400"><span className="text-ink-500">Tension Point:</span> {edge.point_of_tension}</p>
                    {edge.secret_or_unspoken_truth && (
                      <p className="text-ink-400 italic"><span className="text-ink-500 not-italic">Subtext:</span> "{edge.secret_or_unspoken_truth}"</p>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: WORLD & MAGIC RULES */}
          {activeTab === 'world' && (
            <div className="space-y-5">
              {/* Supernatural / Technology Rules (Must enforce costs & limits) */}
              <Card className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Supernatural Rules & Abilities (Anti-God-Mode Stakes Enforced)
                  </h3>
                  <Badge variant="success" size="sm">
                    Bounded Costs Enforced
                  </Badge>
                </div>
                <div className="space-y-3">
                  {packageData.world_bible.supernatural_or_tech_rules.map((rule, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-ink-950 border border-white/10 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-sm">{rule.name}</span>
                        <span className="text-ink-400 font-mono">Users: {rule.practitioners.join(', ')}</span>
                      </div>
                      <p className="text-ink-300">{rule.description}</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-white/5">
                        <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300">
                          <span className="font-semibold block text-2xs uppercase tracking-wider mb-0.5">Mandatory Cost / Physical Strain:</span>
                          <span>{rule.cost_or_strain}</span>
                        </div>
                        <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300">
                          <span className="font-semibold block text-2xs uppercase tracking-wider mb-0.5">Absolute Limitation / Failure Boundary:</span>
                          <span>{rule.absolute_limit}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

            </div>
          )}

          {activeTab === 'locations' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-white">Location Studio</h2>
                  <p className="text-xs text-ink-400 mt-1">Save reusable places separately from scene specific weather, lighting, and damage.</p>
                </div>
                <button onClick={() => openLocationEditor()} className="px-3 py-2 rounded-lg bg-white text-black text-xs font-semibold flex items-center gap-2">
                  <Plus className="w-3.5 h-3.5" /> Add Location
                </button>
              </div>
              {Object.keys(packageData.world_bible.locations).length === 0 ? (
                <Card className="p-8 text-center">
                  <Compass className="w-8 h-8 mx-auto text-ink-500 mb-3" />
                  <h3 className="text-sm font-semibold text-white">No locations yet</h3>
                  <p className="text-xs text-ink-400 mt-2">Create a location profile to give story scenes a consistent place to return to.</p>
                </Card>
              ) : (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  {Object.entries(packageData.world_bible.locations).map(([locationId, location]) => (
                    <Card key={locationId} className="space-y-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="text-sm font-semibold text-white">{location.name}</h3>
                          <div className="text-[10px] text-ink-500 font-mono mt-1">{locationId} · v{location.version || 1}{location.location_type ? ` · ${location.location_type}` : ''}</div>
                        </div>
                        <div className="flex shrink-0 gap-1">
                          <button type="button" onClick={() => openLocationEditor(location, true)} className="px-2 py-1 rounded-md border border-white/10 text-[10px] text-ink-300 hover:text-white">Duplicate</button>
                          <button type="button" onClick={() => openLocationEditor(location)} className="px-2 py-1 rounded-md border border-white/10 text-[10px] text-ink-300 hover:text-white">Edit</button>
                          <button type="button" onClick={() => deleteLocation(locationId)} className="px-2 py-1 rounded-md border border-rose-500/20 text-[10px] text-rose-300 hover:bg-rose-500/10">Delete</button>
                        </div>
                      </div>
                      <p className="text-xs text-ink-300">{location.atmosphere || 'No atmosphere notes yet.'}</p>
                      <p className="text-xs text-ink-400"><span className="text-ink-500">Layout:</span> {location.spatial_layout || 'Not defined'}</p>
                      {location.zones?.length ? <p className="text-xs text-ink-400"><span className="text-ink-500">Zones:</span> {location.zones.join(', ')}</p> : null}
                      <div className="flex flex-wrap gap-1">
                        {location.visual_anchors.map((anchor, index) => <span key={`${locationId}-${index}`} className="px-2 py-0.5 rounded bg-ink-950 text-ink-400 border border-white/5 text-2xs">{anchor}</span>)}
                      </div>
                      <div className="text-[10px] text-ink-500">{location.state_variants?.length || 0} scene state variants · {location.version_history?.length || 0} saved revisions</div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: NARRATIVE STRUCTURE */}
          {activeTab === 'narrative' && (
            <div className="space-y-5">
              {/* Macro 3-Act Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(packageData.narrative_structure.macro_arc_beats).map(([act, beat]) => (
                  <Card key={act} className="space-y-1.5 text-xs">
                    <span className="font-bold text-ink-300 uppercase tracking-wider text-2xs">{act.replace('_', ' ')}</span>
                    <p className="text-ink-200">{beat}</p>
                  </Card>
                ))}
              </div>

              {/* Chapters & Scene Candidates */}
              <div className="space-y-3">
                {packageData.narrative_structure.chapters.map((ch) => (
                  <Card key={ch.chapter_number} className="space-y-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-sm">
                        Chapter {ch.chapter_number}: {ch.title}
                      </span>
                      <span className="text-ink-400 italic">{ch.emotional_shift}</span>
                    </div>
                    <p className="text-ink-300">{ch.purpose_in_arc}</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                      {ch.scene_candidates.map((sc) => (
                        <div key={sc.scene_id} className="p-2.5 rounded-lg bg-ink-950 border border-white/10">
                          <span className="font-semibold text-ink-200 block">{sc.title}</span>
                          <span className="text-ink-400 text-2xs">{sc.key_action_or_revelation}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* TAB 6: VISUAL STYLE */}
          {activeTab === 'style' && (
            <Card className="space-y-4 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">{packageData.style_profile.name}</h3>
                  <p className="text-ink-400">{packageData.style_profile.medium} · {packageData.style_profile.shape_language}</p>
                </div>
                <Badge variant="studio">
                  Style Copier Profile
                </Badge>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div className="p-3.5 rounded-xl bg-ink-950 border border-white/10 space-y-1.5">
                  <span className="font-semibold text-ink-400 uppercase tracking-wider block">Line Art & Tonal Rules</span>
                  {packageData.style_profile.line_art_rules.map((r, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-ink-300">
                      <span className="w-1.5 h-1.5 rounded-full bg-ink-400 shrink-0" />
                      <span>{r}</span>
                    </div>
                  ))}
                </div>

                <div className="p-3.5 rounded-xl bg-ink-950 border border-white/10 space-y-1.5">
                  <span className="font-semibold text-ink-400 uppercase tracking-wider block">Lighting & Palette</span>
                  {packageData.style_profile.lighting_rules.map((r, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-ink-300">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}

          {/* TAB 7: SHEET PLANS */}
          {activeTab === 'sheets' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(packageData.character_sheet_plans).map(([cid, plan]) => (
                <Card key={cid} className="space-y-3 text-xs">
                  <span className="font-bold text-white text-sm capitalize">{plan.character_name} Reference Sheet Plan</span>
                  <div className="space-y-1.5">
                    {plan.views.map((v) => (
                      <div key={v.view_id} className="p-2.5 rounded-lg bg-ink-950 border border-white/10 flex items-center justify-between">
                        <span className="font-medium text-ink-200 capitalize">{v.view_type.replace('_', ' ')}</span>
                        <span className="text-ink-400 text-2xs">{v.camera_angle}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* TAB 8: CONTRACTS & QA & PROMPT COMPILER SANDBOX */}
          {activeTab === 'contracts' && (
            <div className="space-y-6">
              {/* Prompt Compiler Sandbox */}
              <Card className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-white" />
                    <span>Downstream Prompt Compiler Sandbox</span>
                  </h3>
                  <Badge variant="studio" size="sm">
                    CreativeContractsPackage
                  </Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div>
                    <label className="text-ink-400 block mb-1">Character:</label>
                    <select
                      value={selectedCharacterId}
                      onChange={(e) => setSelectedCharacterId(e.target.value)}
                      className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-ink-200 focus:outline-none focus:border-white/30"
                    >
                      {Object.keys(packageData.characters).map((cid) => (
                        <option key={cid} value={cid}>
                          {packageData.characters[cid].name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-ink-400 block mb-1">Emotion:</label>
                    <input
                      type="text"
                      value={compilerEmotion}
                      onChange={(e) => setCompilerEmotion(e.target.value)}
                      className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-ink-200 focus:outline-none focus:border-white/30"
                    />
                  </div>

                  <div className="flex items-center gap-2 pt-6">
                    <input
                      type="checkbox"
                      id="actionShot"
                      checked={compilerActionShot}
                      onChange={(e) => setCompilerActionShot(e.target.checked)}
                      className="rounded bg-ink-950 border-white/10 text-white focus:ring-0"
                    />
                    <label htmlFor="actionShot" className="text-ink-300 text-xs">
                      Dynamic Action Shot
                    </label>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-ink-400 block mb-1">Scene Action Description:</label>
                  <input
                    type="text"
                    value={compilerAction}
                    onChange={(e) => setCompilerAction(e.target.value)}
                    className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-xs text-ink-200 focus:outline-none focus:border-white/30"
                  />
                </div>

                <div className="flex items-center justify-start">
                  <button
                    onClick={handleCompilePrompt}
                    disabled={compiling}
                    className="px-3.5 py-1.5 rounded-lg bg-ink-800 hover:bg-ink-750 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors border border-white/15"
                  >
                    {compiling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                    <span>Compile Production Prompt</span>
                  </button>
                </div>

                {compiledResult && (
                  <div className="space-y-3 pt-3 border-t border-white/10 text-xs">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-emerald-400">Positive Prompt:</span>
                        <button
                          onClick={handleCopyPositive}
                          className="flex items-center gap-1 text-2xs text-ink-400 hover:text-white transition-colors"
                        >
                          {copiedPrompt ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedPrompt ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <div className="p-3.5 rounded-xl bg-ink-950 border border-white/10 font-mono text-ink-200 leading-relaxed break-words select-all">
                        {compiledResult.positive}
                      </div>
                    </div>
                    <div>
                      <span className="font-semibold text-rose-400 block mb-1">Negative Constraints:</span>
                      <div className="p-3.5 rounded-xl bg-ink-950 border border-white/10 font-mono text-rose-300/80 text-2xs leading-relaxed break-words select-all">
                        {compiledResult.negative}
                      </div>
                    </div>
                  </div>
                )}
              </Card>

              {/* Validation Findings Report */}
              <Card className="space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-white uppercase tracking-wider">
                    Cross-Document Coherence Audit
                  </h3>
                  <Badge
                    variant={packageData.validation.is_coherent ? 'success' : 'danger'}
                    size="sm"
                  >
                    {packageData.validation.is_coherent ? 'All Invariants Verified' : 'Findings Require Attention'}
                  </Badge>
                </div>

                {packageData.validation.findings.length === 0 ? (
                  <p className="text-ink-400 italic">No contradictions or dropped invariants detected.</p>
                ) : (
                  <div className="space-y-2">
                    {packageData.validation.findings.map((f, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border ${
                          f.severity === 'ERROR'
                            ? 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                            : f.severity === 'WARNING'
                            ? 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                            : 'bg-ink-800/60 border-white/10 text-ink-300'
                        }`}
                      >
                        <div className="flex items-center justify-between font-semibold">
                          <span>{f.title || f.finding_id}</span>
                          <span className="text-2xs font-mono">{f.severity}</span>
                        </div>
                        <p className="text-ink-200 mt-1">{f.message}</p>
                        {f.evidence && <p className="text-ink-400 text-2xs mt-1">Evidence: {f.evidence}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ADD CHARACTER MODAL */}
      <Modal
        isOpen={showAddCharModal}
        onClose={() => setShowAddCharModal(false)}
        title="Add Character to Universe & Canon"
        maxWidth="md"
        footer={
          <div className="flex items-center justify-between w-full">
            <span className="text-2xs text-ink-500">
              Monotonic Canon Invariant Guard
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowAddCharModal(false)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-ink-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="add-creative-char-form"
                disabled={creatingChar || !newCharName.trim()}
                className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold flex items-center gap-2 transition-all disabled:opacity-50 shadow-sm"
              >
                {creatingChar ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Creating Character...</span>
                  </>
                ) : (
                  <>
                    <UserPlus className="w-3.5 h-3.5" />
                    <span>Create Character</span>
                  </>
                )}
              </button>
            </div>
          </div>
        }
      >
        <form id="add-creative-char-form" onSubmit={handleCreateCustomCharacter} className="space-y-4 text-xs">
          <p className="text-ink-400">
            Define character identity and visual invariants. Characters can be committed directly into the Story Bible canon so the Agent Studio can immediately generate consistent panels with them.
          </p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-ink-300 font-semibold mb-1">Character Name *</label>
              <input
                type="text"
                required
                value={newCharName}
                onChange={(e) => setNewCharName(e.target.value)}
                placeholder="e.g. Kaelen, Zara, Dr. Vance"
                className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-white placeholder-ink-600 focus:outline-none focus:border-white/30 text-xs"
              />
            </div>
            <div>
              <label className="block text-ink-300 font-semibold mb-1">Role</label>
              <select
                value={newCharRole}
                onChange={(e) => setNewCharRole(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-white focus:outline-none focus:border-white/30 text-xs"
              >
                <option value="Protagonist">Protagonist</option>
                <option value="Foil & Ally">Foil & Scavenger Ally</option>
                <option value="Antagonist">Antagonist / Rival</option>
                <option value="Deuteragonist">Deuteragonist</option>
                <option value="Mentor">Mentor / Guide</option>
                <option value="Supporting Character">Supporting Character</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-ink-300 font-semibold mb-1">Age Range</label>
              <input
                type="text"
                value={newCharAge}
                onChange={(e) => setNewCharAge(e.target.value)}
                placeholder="e.g. 19-22"
                className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-white placeholder-ink-600 focus:outline-none focus:border-white/30 text-xs"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-ink-300 font-semibold mb-1">Narrative Function</label>
              <input
                type="text"
                value={newCharDesc}
                onChange={(e) => setNewCharDesc(e.target.value)}
                placeholder="e.g. Black-market relic scavenger who guides Nour through sunken canals"
                className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-white placeholder-ink-600 focus:outline-none focus:border-white/30 text-xs"
              />
            </div>
          </div>

          <div>
            <label className="block text-ink-300 font-semibold mb-1">
              Visual Invariants (One per line)
            </label>
            <textarea
              rows={3}
              value={newCharInvariants}
              onChange={(e) => setNewCharInvariants(e.target.value)}
              placeholder={"Brass dive goggles on forehead\nCoral scar along left arm\nBraided sea-green hair"}
              className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-white placeholder-ink-600 focus:outline-none focus:border-white/30 text-xs font-mono leading-relaxed"
            />
          </div>

          <div>
            <label className="block text-ink-300 font-semibold mb-1">
              Default Wardrobe & Garments (One per line)
            </label>
            <textarea
              rows={2}
              value={newCharGarments}
              onChange={(e) => setNewCharGarments(e.target.value)}
              placeholder={"Reinforced diver vest\nCanvas trousers with utility loops"}
              className="w-full p-2.5 rounded-lg bg-ink-950 border border-white/10 text-white placeholder-ink-600 focus:outline-none focus:border-white/30 text-xs font-mono leading-relaxed"
            />
          </div>

          <div className="pt-2 border-t border-white/10">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={newCharCommitToCanon}
                onChange={(e) => setNewCharCommitToCanon(e.target.checked)}
                className="w-4 h-4 rounded bg-ink-950 border-white/20 text-white focus:ring-0 cursor-pointer"
              />
              <span className="text-xs text-ink-200">
                Commit immediately to Story Bible Canon (Instantly active in Agent Studio & Canvas)
              </span>
            </label>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={Boolean(locationDraft)}
        onClose={() => setLocationDraft(null)}
        title={locationDraft?.version ? 'Edit Location' : locationDraft?.source_location_id ? 'Duplicate Location' : 'Create Location'}
        size="2xl"
        footer={(
          <div className="flex items-center justify-between w-full">
            <span className="text-[10px] text-ink-500">Project revision {packageData?.version ?? '—'}</span>
            <div className="flex gap-2">
              <button type="button" onClick={() => setLocationDraft(null)} className="px-3 py-2 rounded-lg text-xs text-ink-300 hover:text-white">Cancel</button>
              <button type="submit" form="location-profile-form" disabled={savingLocation} className="px-4 py-2 rounded-lg bg-white text-black text-xs font-semibold disabled:opacity-50">
                {savingLocation ? 'Saving…' : 'Save Location'}
              </button>
            </div>
          </div>
        )}
      >
        {locationDraft && (
          <form id="location-profile-form" onSubmit={saveLocation} className="space-y-4 text-xs">
            <p className="text-ink-400">The location profile stores lasting layout and visual anchors. Scene conditions below remain separate variants.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Name *</span><input required value={locationDraft.name} onChange={(e) => setLocationDraft({ ...locationDraft, name: e.target.value })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Stable ID *</span><input required readOnly={Boolean(locationDraft.version)} value={locationDraft.location_id} onChange={(e) => setLocationDraft({ ...locationDraft, location_id: e.target.value })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white font-mono read-only:opacity-60" /></label>
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Type</span><input value={locationDraft.location_type || ''} onChange={(e) => setLocationDraft({ ...locationDraft, location_type: e.target.value })} placeholder="City, room, landscape…" className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Scale</span><input value={locationDraft.scale || ''} onChange={(e) => setLocationDraft({ ...locationDraft, scale: e.target.value })} placeholder="Room, neighborhood, region…" className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
              <label className="space-y-1 sm:col-span-2"><span className="block text-ink-300 font-medium">World / geographic context</span><input value={locationDraft.geographic_context || ''} onChange={(e) => setLocationDraft({ ...locationDraft, geographic_context: e.target.value })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
              <label className="space-y-1 sm:col-span-2"><span className="block text-ink-300 font-medium">Parent location</span><select value={locationDraft.parent_location_id || ''} onChange={(e) => setLocationDraft({ ...locationDraft, parent_location_id: e.target.value || null })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white"><option value="">No parent</option>{Object.entries(packageData?.world_bible.locations || {}).filter(([id]) => id !== locationDraft.location_id).map(([id, parent]) => <option key={id} value={id}>{parent.name}</option>)}</select></label>
            </div>
            <label className="block space-y-1"><span className="block text-ink-300 font-medium">Atmosphere</span><textarea rows={2} value={locationDraft.atmosphere} onChange={(e) => setLocationDraft({ ...locationDraft, atmosphere: e.target.value })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
            <label className="block space-y-1"><span className="block text-ink-300 font-medium">Permanent spatial layout</span><textarea rows={2} value={locationDraft.spatial_layout} onChange={(e) => setLocationDraft({ ...locationDraft, spatial_layout: e.target.value })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Zones / rooms (one per line)</span><textarea rows={3} value={(locationDraft.zones || []).join('\n')} onChange={(e) => setLocationDraft({ ...locationDraft, zones: e.target.value.split('\n').map((part) => part.trim()).filter(Boolean) })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Visual anchors (one per line)</span><textarea rows={3} value={locationDraft.visual_anchors.join('\n')} onChange={(e) => setLocationDraft({ ...locationDraft, visual_anchors: e.target.value.split('\n').map((part) => part.trim()).filter(Boolean) })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Aliases (one per line)</span><textarea rows={2} value={(locationDraft.aliases || []).join('\n')} onChange={(e) => setLocationDraft({ ...locationDraft, aliases: e.target.value.split('\n').map((part) => part.trim()).filter(Boolean) })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Environment details (key: value per line)</span><textarea rows={2} value={Object.entries(locationDraft.environment_details || {}).map(([key, value]) => `${key}: ${value}`).join('\n')} onChange={(e) => setLocationDraft({ ...locationDraft, environment_details: Object.fromEntries(e.target.value.split('\n').map((line) => line.split(/:(.*)/s)).filter((parts) => parts[0]?.trim() && parts[1]?.trim()).map(([key, value]) => [key.trim(), value.trim()])) })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Lighting continuity</span><textarea rows={2} value={locationDraft.lighting_conditions} onChange={(e) => setLocationDraft({ ...locationDraft, lighting_conditions: e.target.value })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
              <label className="space-y-1"><span className="block text-ink-300 font-medium">Narrative use</span><textarea rows={2} value={locationDraft.narrative_use} onChange={(e) => setLocationDraft({ ...locationDraft, narrative_use: e.target.value })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
            </div>
            <label className="block space-y-1"><span className="block text-ink-300 font-medium">Continuity rules (one per line)</span><textarea rows={2} value={locationDraft.continuity_rules.join('\n')} onChange={(e) => setLocationDraft({ ...locationDraft, continuity_rules: e.target.value.split('\n').map((part) => part.trim()).filter(Boolean) })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" /></label>
            <div className="rounded-xl border border-white/10 p-3 space-y-3">
              <div><h4 className="font-semibold text-white">Scene condition variants</h4><p className="text-[10px] text-ink-500 mt-1">Add temporary time, weather, lighting, or damage without changing the location's permanent layout.</p></div>
              <div className="flex flex-wrap gap-2">
                {(locationDraft.state_variants || []).map((variant) => <span key={variant.variant_id} className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-ink-800 text-ink-200">{variant.name}<button type="button" aria-label={`Remove ${variant.name}`} onClick={() => setLocationDraft({ ...locationDraft, state_variants: locationDraft.state_variants?.filter((item) => item.variant_id !== variant.variant_id) })} className="text-ink-400 hover:text-white">×</button></span>)}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                <input aria-label="Variant name" placeholder="Name" value={locationVariantDraft.name} onChange={(e) => setLocationVariantDraft({ ...locationVariantDraft, name: e.target.value })} className="p-2 rounded-lg bg-ink-950 border border-white/10 text-white" />
                <input aria-label="Time of day" placeholder="Time of day" value={locationVariantDraft.time_of_day || ''} onChange={(e) => setLocationVariantDraft({ ...locationVariantDraft, time_of_day: e.target.value })} className="p-2 rounded-lg bg-ink-950 border border-white/10 text-white" />
                <input aria-label="Season" placeholder="Season" value={locationVariantDraft.season || ''} onChange={(e) => setLocationVariantDraft({ ...locationVariantDraft, season: e.target.value })} className="p-2 rounded-lg bg-ink-950 border border-white/10 text-white" />
                <input aria-label="Weather" placeholder="Weather" value={locationVariantDraft.weather || ''} onChange={(e) => setLocationVariantDraft({ ...locationVariantDraft, weather: e.target.value })} className="p-2 rounded-lg bg-ink-950 border border-white/10 text-white" />
                <input aria-label="Lighting" placeholder="Lighting" value={locationVariantDraft.lighting || ''} onChange={(e) => setLocationVariantDraft({ ...locationVariantDraft, lighting: e.target.value })} className="p-2 rounded-lg bg-ink-950 border border-white/10 text-white" />
              </div>
              <input aria-label="Scene condition and visible changes" placeholder="Scene condition / visible changes" value={locationVariantDraft.scene_condition || ''} onChange={(e) => setLocationVariantDraft({ ...locationVariantDraft, scene_condition: e.target.value, visible_changes: e.target.value ? [e.target.value] : [] })} className="w-full p-2 rounded-lg bg-ink-950 border border-white/10 text-white" />
              <button type="button" onClick={() => {
                if (!locationVariantDraft.name.trim()) return;
                const variantId = `${locationDraft.location_id || 'location'}_state_${(locationDraft.state_variants || []).length + 1}`;
                setLocationDraft({ ...locationDraft, state_variants: [...(locationDraft.state_variants || []), { ...locationVariantDraft, variant_id: variantId, name: locationVariantDraft.name.trim() }] });
                setLocationVariantDraft({ name: '', visible_changes: [] });
              }} className="px-2.5 py-1.5 rounded-md border border-white/10 text-[10px] text-ink-200 hover:bg-white/5">Add condition</button>
            </div>
            {locationSaveError && <p role="alert" className="text-xs text-rose-300">{locationSaveError}</p>}
          </form>
        )}
      </Modal>
    </div>
  );
};
