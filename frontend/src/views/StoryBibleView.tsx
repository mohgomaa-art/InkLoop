import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Save,
  ShieldAlert,
  GitBranch,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Plus,
  Trash2,
  FileText,
  User,
  Palette,
  MapPin,
  Package,
  Edit3,
  X,
  Copy,
  Check,
  ChevronRight,
  Clock,
  Layers,
  ArrowRight,
  Upload,
  Image as ImageIcon,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface StoryBibleViewProps {
  currentProject: string;
}

// Helper for rendering and editing tag lists
const TagListEditor: React.FC<{
  label: string;
  tags: string[];
  isEditing: boolean;
  onAdd: (tag: string) => void;
  onRemove: (index: number) => void;
  placeholder?: string;
  variant?: 'purple' | 'amber' | 'rose' | 'neutral' | 'emerald';
}> = ({ label, tags, isEditing, onAdd, onRemove, placeholder = 'Add item...', variant = 'neutral' }) => {
  const [inputVal, setInputVal] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const trimmed = inputVal.trim();
      if (trimmed) {
        onAdd(trimmed);
        setInputVal('');
      }
    }
  };

  const handleAddClick = () => {
    const trimmed = inputVal.trim();
    if (trimmed) {
      onAdd(trimmed);
      setInputVal('');
    }
  };

  const variantClasses = {
    purple: 'bg-purple-500/15 border-purple-500/30 text-purple-300',
    amber: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
    rose: 'bg-rose-500/15 border-rose-500/30 text-rose-300',
    emerald: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
    neutral: 'bg-white/5 border-white/10 text-ink-200',
  }[variant];

  return (
    <div className="space-y-2">
      <label className="text-xs font-medium text-ink-300 block">{label}</label>
      <div className="flex flex-wrap gap-1.5 min-h-[32px] p-2 rounded-xl bg-ink-950/80 border border-white/5">
        {tags && tags.length > 0 ? (
          tags.map((tag, idx) => (
            <span
              key={idx}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${variantClasses}`}
            >
              <span>{tag}</span>
              {isEditing && (
                <button
                  type="button"
                  onClick={() => onRemove(idx)}
                  className="hover:text-white p-0.5 rounded transition-colors"
                  aria-label="Remove tag"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </span>
          ))
        ) : (
          <span className="text-xs text-ink-500 italic p-1">No items declared</span>
        )}
      </div>
      {isEditing && (
        <div className="flex gap-2">
          <input
            type="text"
            placeholder={placeholder}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-ink-950 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/20"
          />
          <button
            type="button"
            onClick={handleAddClick}
            disabled={!inputVal.trim()}
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-ink-200 hover:text-white font-medium transition-colors disabled:opacity-40"
          >
            Add
          </button>
        </div>
      )}
    </div>
  );
};

export const StoryBibleView: React.FC<StoryBibleViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();
  const [bible, setBible] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'characters' | 'style' | 'locations' | 'props' | 'story'>('characters');

  // Optimistic concurrency conflict state
  const [conflictData, setConflictData] = useState<any | null>(null);

  // Proposal modal state
  const [showProposalModal, setShowProposalModal] = useState(false);
  const [proposalsTab, setProposalsTab] = useState<'pending' | 'custom'>('pending');
  const [pendingProposals, setPendingProposals] = useState<any[]>([]);
  const [loadingProposals, setLoadingProposals] = useState(false);
  const [mutationTargetType, setMutationTargetType] = useState('character');
  const [mutationTargetId, setMutationTargetId] = useState('');
  const [mutationDescription, setMutationDescription] = useState('');
  const [mutationChangesJson, setMutationChangesJson] = useState('{\n  "notes": "Custom mutation delta"\n}');
  const [submittingProposal, setSubmittingProposal] = useState(false);

  // Proposal Review & Confirmation Modal
  const [proposalPreview, setProposalPreview] = useState<{
    targetType: string;
    targetId: string;
    description: string;
    changes: any;
    isOpen: boolean;
  }>({
    targetType: '',
    targetId: '',
    description: '',
    changes: null,
    isOpen: false,
  });

  // 1. CHARACTERS STATE
  const [selectedCharacterId, setSelectedCharacterId] = useState('nour');
  const [isEditingCharacter, setIsEditingCharacter] = useState(false);
  const [characterDraft, setCharacterDraft] = useState<any>(null);
  const [showAddCharacterModal, setShowAddCharacterModal] = useState(false);
  const [newChar, setNewChar] = useState({
    name: '',
    id: '',
    role: 'Supporting Character',
    entityKind: 'unspecified being',
    desc: '',
    invariants: [] as string[],
    clothing: [] as string[],
    restrictions: [] as string[],
    minFacePx: 80,
    faceCheckApplicable: false,
  });
  const [showDeleteCharModal, setShowDeleteCharModal] = useState(false);
  const [charToDelete, setCharToDelete] = useState('');

  // 2. STYLE STATE
  const [isEditingStyle, setIsEditingStyle] = useState(false);
  const [styleDraft, setStyleDraft] = useState<any>(null);

  // 3. LOCATIONS STATE
  const [selectedLocationId, setSelectedLocationId] = useState('');
  const [isEditingLocation, setIsEditingLocation] = useState(false);
  const [locationDraft, setLocationDraft] = useState<any>(null);
  const [showAddLocationModal, setShowAddLocationModal] = useState(false);
  const [newLoc, setNewLoc] = useState({
    id: '',
    name: '',
    desc: '',
    requiredAttributes: [] as string[],
    permittedVariations: [] as string[],
  });
  const [showDeleteLocModal, setShowDeleteLocModal] = useState(false);
  const [locToDelete, setLocToDelete] = useState('');

  // 4. PROPS STATE
  const [selectedPropId, setSelectedPropId] = useState('');
  const [isEditingProp, setIsEditingProp] = useState(false);
  const [propDraft, setPropDraft] = useState<any>(null);
  const [showAddPropModal, setShowAddPropModal] = useState(false);
  const [newProp, setNewProp] = useState({
    id: '',
    name: '',
    desc: '',
    requiredAttributes: [] as string[],
    associatedCharacters: [] as string[],
    permittedVariations: [] as string[],
  });
  const [showDeletePropModal, setShowDeletePropModal] = useState(false);
  const [propToDelete, setPropToDelete] = useState('');

  // 5. STORY TEXT STATE
  const [isRevisingStory, setIsRevisingStory] = useState(false);
  const [storyDraft, setStoryDraft] = useState('');
  const [copiedBrief, setCopiedBrief] = useState(false);

  // Fetch Bible
  const fetchBible = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getProjectBible(currentProject);
      setBible(data);
      setConflictData(null);

      // Default selection if unselected
      const charIds = Object.keys(data.characters || {});
      if (charIds.length > 0 && (!selectedCharacterId || !data.characters[selectedCharacterId])) {
        setSelectedCharacterId(charIds[0]);
      }
      const locIds = Object.keys(data.locations || {});
      if (locIds.length > 0 && (!selectedLocationId || !data.locations[selectedLocationId])) {
        setSelectedLocationId(locIds[0]);
      }
      const propIds = Object.keys(data.props || {});
      if (propIds.length > 0 && (!selectedPropId || !data.props[selectedPropId])) {
        setSelectedPropId(propIds[0]);
      }
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to load Story Bible', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  const fetchProposals = async () => {
    try {
      setLoadingProposals(true);
      const list = await apiClient.listProposals(currentProject);
      setPendingProposals(list);
    } catch (err: any) {
      // Fallback silently if no proposals file yet
      setPendingProposals([]);
    } finally {
      setLoadingProposals(false);
    }
  };

  const [generatingAnchor, setGeneratingAnchor] = useState<string | null>(null);

  const handleGenerateAnchor = async (characterId: string) => {
    setGeneratingAnchor(characterId);
    try {
      const res = await fetch(`/api/v1/projects/${currentProject}/characters/${characterId}/generate-anchor`, {
        method: 'POST',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || 'Failed to generate anchor portrait');
      }
      const data = await res.json();
      await fetchBible();
      showToast({ type: 'success', title: 'Anchor Portrait Generated', message: `Registered canonical anchor (${data.asset_id})` });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Anchor Generation Failed', message: err.message });
    } finally {
      setGeneratingAnchor(null);
    }
  };

  const handleUploadAnchor = async (characterId: string, file: File) => {
    setGeneratingAnchor(characterId);
    try {
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
      await fetchBible();
      showToast({ type: 'success', title: 'Anchor Uploaded', message: `Registered canonical anchor (${data.asset_id})` });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Anchor Upload Failed', message: err.message });
    } finally {
      setGeneratingAnchor(null);
    }
  };

  useEffect(() => {
    fetchBible();
  }, [currentProject]);

  // Synchronize drafts when selection changes or editing begins
  useEffect(() => {
    if (bible?.characters && selectedCharacterId && bible.characters[selectedCharacterId]) {
      setCharacterDraft(JSON.parse(JSON.stringify(bible.characters[selectedCharacterId])));
    }
  }, [selectedCharacterId, bible]);

  useEffect(() => {
    if (bible?.style) {
      setStyleDraft(JSON.parse(JSON.stringify(bible.style)));
    }
  }, [bible]);

  useEffect(() => {
    if (bible?.locations && selectedLocationId && bible.locations[selectedLocationId]) {
      setLocationDraft(JSON.parse(JSON.stringify(bible.locations[selectedLocationId])));
    }
  }, [selectedLocationId, bible]);

  useEffect(() => {
    if (bible?.props && selectedPropId && bible.props[selectedPropId]) {
      setPropDraft(JSON.parse(JSON.stringify(bible.props[selectedPropId])));
    }
  }, [selectedPropId, bible]);

  useEffect(() => {
    if (bible?.user_story_text !== undefined) {
      setStoryDraft(bible.user_story_text || '');
    }
  }, [bible]);

  // Execute Proposal workflow (propose -> apply -> refresh)
  const applyCanonProposal = async (
    targetType: string,
    targetId: string,
    description: string,
    proposedChanges: any
  ) => {
    try {
      setSubmittingProposal(true);

      // 1. Propose mutation
      const proposal = await apiClient.proposeMutation(currentProject, {
        target_type: targetType,
        target_id: targetId,
        change_description: description,
        proposed_changes: proposedChanges,
      });

      // 2. Apply mutation to create monotonic version
      const applied = await apiClient.applyMutation(currentProject, {
        proposal_id: proposal.proposal_id,
        caller_authorized: true,
      });

      // 3. Update local state with returned canonical Bible
      setBible(applied.bible);
      setConflictData(null);
      setProposalPreview((prev) => ({ ...prev, isOpen: false }));

      showToast({
        type: 'success',
        title: 'Canon Mutation Applied',
        message: `Monotonic v${applied.bible_version} &bull; Hash: ${applied.canon_hash.substring(0, 12)}...`,
      });

      return applied;
    } catch (err: any) {
      showToast({
        type: 'error',
        title: 'Canon Mutation Rejected',
        message: err.payload?.message || err.message || 'Operation failed',
      });
      throw err;
    } finally {
      setSubmittingProposal(false);
    }
  };

  // Direct Save Canon button (with optimistic concurrency check)
  const handleSaveBibleDirect = async () => {
    if (!bible) return;
    try {
      setSaving(true);
      const res = await apiClient.updateProjectBible(currentProject, {
        bible,
        expected_canon_hash: bible.canon_hash,
        expected_version: bible.bible_version,
      });
      setBible(res.bible);
      setConflictData(null);
      setIsRevisingStory(false);
      showToast({
        type: 'success',
        title: 'Story Bible Saved & Canon Snapshotted',
        message: `Version ${res.bible_version} &bull; Hash: ${res.canon_hash.substring(0, 12)}...`,
      });
    } catch (err: any) {
      if (err.payload?.status === 409 || err.payload?.error_code === 'ERR_1006_VERSION_MISMATCH') {
        setConflictData(err.payload.detail || err.payload);
        showToast({
          type: 'error',
          title: 'Version Conflict (409)',
          message: 'The Story Bible was modified concurrently. Your edits are preserved below.',
        });
      } else {
        showToast({
          type: 'error',
          title: 'Validation Error',
          message: err.payload?.message || err.message,
        });
      }
    } finally {
      setSaving(false);
    }
  };

  // =========================================================================
  // CHARACTER HANDLERS
  // =========================================================================

  const handleSaveCharacter = async () => {
    if (!characterDraft) return;
    const nameTrimmed = characterDraft.name?.trim();
    if (!nameTrimmed) {
      showToast({ type: 'error', title: 'Name Required', message: 'Character must have a valid display name.' });
      return;
    }

    const proposedChanges = {
      action: 'update',
      name: nameTrimmed,
      description: characterDraft.description || '',
      visual_invariants: characterDraft.visual_invariants || [],
      clothing_attributes: characterDraft.clothing_attributes || [],
      restrictions: characterDraft.restrictions || [],
      tolerances: characterDraft.tolerances || { min_face_px_for_check: 80 },
      attributes: characterDraft.attributes || [],
    };

    setProposalPreview({
      targetType: 'character',
      targetId: selectedCharacterId,
      description: `Update character ${nameTrimmed} (${selectedCharacterId}) traits and invariants`,
      changes: proposedChanges,
      isOpen: true,
    });
  };

  const handleCreateNewCharacter = async (e: React.FormEvent) => {
    e.preventDefault();
    const nameTrimmed = newChar.name.trim();
    if (!nameTrimmed) {
      showToast({ type: 'error', title: 'Name Required', message: 'Please enter a character name.' });
      return;
    }
    const resolvedId = (newChar.id.trim() || nameTrimmed)
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, '_')
      .replace(/^_+|_+$/g, '');

    if (!resolvedId) {
      showToast({ type: 'error', title: 'Invalid ID', message: 'Character slug must contain alphanumeric characters.' });
      return;
    }

    if (bible?.characters && bible.characters[resolvedId]) {
      showToast({ type: 'error', title: 'Character Exists', message: `Character '${resolvedId}' already exists in canon.` });
      return;
    }

    const proposedChanges = {
      action: 'add',
      name: nameTrimmed,
      entity_kind: newChar.entityKind,
      description: newChar.desc.trim() || `${newChar.entityKind}: ${nameTrimmed} (${newChar.role})`,
      visual_invariants: newChar.invariants,
      clothing_attributes: newChar.clothing,
      restrictions: newChar.restrictions,
      tolerances: { min_face_px_for_check: newChar.minFacePx || 80, face_check_applicable: newChar.faceCheckApplicable },
      attributes: [
        {
          id: `${resolvedId}_appearance`,
          text: newChar.desc.trim() || `${nameTrimmed} canonical appearance`,
          required: true,
        },
      ],
      approval_status: 'approved',
    };

    try {
      await applyCanonProposal(
        'character',
        resolvedId,
        `Declare canonical character ${nameTrimmed} (${resolvedId})`,
        proposedChanges
      );
      setSelectedCharacterId(resolvedId);
      setShowAddCharacterModal(false);
      setNewChar({
        name: '',
        id: '',
        role: 'Supporting Character',
        entityKind: 'unspecified being',
        desc: '',
        invariants: [],
        clothing: [],
        restrictions: [],
        minFacePx: 80,
        faceCheckApplicable: false,
      });
    } catch {
      // Toast already shown in applyCanonProposal
    }
  };

  const handleDeleteCharacter = async () => {
    if (!charToDelete) return;
    try {
      await applyCanonProposal(
        'character',
        charToDelete,
        `Remove character ${charToDelete} from canon`,
        { action: 'delete' }
      );
      setShowDeleteCharModal(false);
      setCharToDelete('');
      const remainingIds = Object.keys(bible?.characters || {}).filter((id) => id !== charToDelete);
      if (remainingIds.length > 0) setSelectedCharacterId(remainingIds[0]);
    } catch {
      // Error handled
    }
  };

  // =========================================================================
  // STYLE HANDLERS
  // =========================================================================

  const handleSaveStyle = async () => {
    if (!styleDraft) return;
    const nameTrimmed = styleDraft.name?.trim();
    if (!nameTrimmed) {
      showToast({ type: 'error', title: 'Style Name Required', message: 'Style must have a display name.' });
      return;
    }

    const proposedChanges = {
      action: 'update',
      name: nameTrimmed,
      medium: styleDraft.medium?.trim() || 'digital ink',
      rendering_approach: styleDraft.rendering_approach?.trim() || 'black-and-white high contrast',
      line_art_rules: styleDraft.line_art_rules || [],
      tonal_rules: styleDraft.tonal_rules || [],
      background_detail_rules: styleDraft.background_detail_rules || '',
      lighting_constraints: styleDraft.lighting_constraints || [],
      positive_constraints: styleDraft.positive_constraints || [],
      negative_constraints: styleDraft.negative_constraints || [],
    };

    setProposalPreview({
      targetType: 'style',
      targetId: bible.style.style_id,
      description: `Update project visual style definition (${nameTrimmed})`,
      changes: proposedChanges,
      isOpen: true,
    });
  };

  // =========================================================================
  // LOCATION HANDLERS
  // =========================================================================

  const handleSaveLocation = async () => {
    if (!locationDraft) return;
    const nameTrimmed = locationDraft.name?.trim();
    if (!nameTrimmed) {
      showToast({ type: 'error', title: 'Location Name Required', message: 'Location must have a valid display name.' });
      return;
    }

    const proposedChanges = {
      action: 'update',
      name: nameTrimmed,
      description: locationDraft.description || '',
      required_attributes: locationDraft.required_attributes || [],
      permitted_variations: locationDraft.permitted_variations || [],
      state_relevant_properties: locationDraft.state_relevant_properties || ['time_of_day', 'weather', 'lighting'],
    };

    setProposalPreview({
      targetType: 'location',
      targetId: selectedLocationId,
      description: `Update canonical location ${nameTrimmed} (${selectedLocationId})`,
      changes: proposedChanges,
      isOpen: true,
    });
  };

  const handleCreateNewLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    const nameTrimmed = newLoc.name.trim();
    if (!nameTrimmed) {
      showToast({ type: 'error', title: 'Name Required', message: 'Please enter a location name.' });
      return;
    }
    const resolvedId = (newLoc.id.trim() || nameTrimmed)
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, '_')
      .replace(/^_+|_+$/g, '');

    if (!resolvedId) {
      showToast({ type: 'error', title: 'Invalid ID', message: 'Location identifier must be alphanumeric.' });
      return;
    }

    if (bible?.locations && bible.locations[resolvedId]) {
      showToast({ type: 'error', title: 'Location Exists', message: `Location '${resolvedId}' already declared.` });
      return;
    }

    const proposedChanges = {
      action: 'add',
      name: nameTrimmed,
      description: newLoc.desc.trim() || `Canonical location ${nameTrimmed}`,
      required_attributes: newLoc.requiredAttributes.length > 0 ? newLoc.requiredAttributes : ['distinctive architectural setting'],
      permitted_variations: newLoc.permittedVariations,
      state_relevant_properties: ['time_of_day', 'weather', 'lighting', 'damage_state'],
      approval_status: 'approved',
    };

    try {
      await applyCanonProposal(
        'location',
        resolvedId,
        `Declare canonical location ${nameTrimmed} (${resolvedId})`,
        proposedChanges
      );
      setSelectedLocationId(resolvedId);
      setShowAddLocationModal(false);
      setNewLoc({
        id: '',
        name: '',
        desc: '',
        requiredAttributes: [],
        permittedVariations: [],
      });
    } catch {
      // Error caught
    }
  };

  const handleDeleteLocation = async () => {
    if (!locToDelete) return;
    try {
      await applyCanonProposal(
        'location',
        locToDelete,
        `Remove location ${locToDelete} from canon`,
        { action: 'delete' }
      );
      setShowDeleteLocModal(false);
      setLocToDelete('');
      const remainingIds = Object.keys(bible?.locations || {}).filter((id) => id !== locToDelete);
      setSelectedLocationId(remainingIds[0] || '');
    } catch {
      // Error caught
    }
  };

  // =========================================================================
  // PROP HANDLERS
  // =========================================================================

  const handleSaveProp = async () => {
    if (!propDraft) return;
    const nameTrimmed = propDraft.name?.trim();
    if (!nameTrimmed) {
      showToast({ type: 'error', title: 'Prop Name Required', message: 'Prop must have a valid display name.' });
      return;
    }

    const proposedChanges = {
      action: 'update',
      name: nameTrimmed,
      description: propDraft.description || '',
      required_attributes: propDraft.required_attributes || [],
      associated_character_ids: propDraft.associated_character_ids || [],
      permitted_variations: propDraft.permitted_variations || [],
      state_relevant_properties: propDraft.state_relevant_properties || ['holder_id', 'condition'],
    };

    setProposalPreview({
      targetType: 'prop',
      targetId: selectedPropId,
      description: `Update canonical prop ${nameTrimmed} (${selectedPropId})`,
      changes: proposedChanges,
      isOpen: true,
    });
  };

  const handleCreateNewProp = async (e: React.FormEvent) => {
    e.preventDefault();
    const nameTrimmed = newProp.name.trim();
    if (!nameTrimmed) {
      showToast({ type: 'error', title: 'Name Required', message: 'Please enter a prop name.' });
      return;
    }
    const resolvedId = (newProp.id.trim() || nameTrimmed)
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, '_')
      .replace(/^_+|_+$/g, '');

    if (!resolvedId) {
      showToast({ type: 'error', title: 'Invalid ID', message: 'Prop slug must be alphanumeric.' });
      return;
    }

    if (bible?.props && bible.props[resolvedId]) {
      showToast({ type: 'error', title: 'Prop Exists', message: `Prop '${resolvedId}' already declared.` });
      return;
    }

    const proposedChanges = {
      action: 'add',
      name: nameTrimmed,
      description: newProp.desc.trim() || `Canonical prop ${nameTrimmed}`,
      required_attributes: newProp.requiredAttributes.length > 0 ? newProp.requiredAttributes : ['distinctive item appearance'],
      associated_character_ids: newProp.associatedCharacters,
      permitted_variations: newProp.permittedVariations,
      state_relevant_properties: ['holder_id', 'condition', 'location_id'],
      approval_status: 'approved',
    };

    try {
      await applyCanonProposal(
        'prop',
        resolvedId,
        `Declare canonical prop ${nameTrimmed} (${resolvedId})`,
        proposedChanges
      );
      setSelectedPropId(resolvedId);
      setShowAddPropModal(false);
      setNewProp({
        id: '',
        name: '',
        desc: '',
        requiredAttributes: [],
        associatedCharacters: [],
        permittedVariations: [],
      });
    } catch {
      // Error caught
    }
  };

  const handleDeleteProp = async () => {
    if (!propToDelete) return;
    try {
      await applyCanonProposal(
        'prop',
        propToDelete,
        `Remove prop ${propToDelete} from canon`,
        { action: 'delete' }
      );
      setShowDeletePropModal(false);
      setPropToDelete('');
      const remainingIds = Object.keys(bible?.props || {}).filter((id) => id !== propToDelete);
      setSelectedPropId(remainingIds[0] || '');
    } catch {
      // Error caught
    }
  };

  // =========================================================================
  // CREATIVE BRIEF HANDLERS
  // =========================================================================

  const handleSaveRevisedBrief = async () => {
    const copy = { ...bible, user_story_text: storyDraft };
    try {
      setSaving(true);
      const res = await apiClient.updateProjectBible(currentProject, {
        bible: copy,
        expected_canon_hash: bible.canon_hash,
        expected_version: bible.bible_version,
      });
      setBible(res.bible);
      setIsRevisingStory(false);
      showToast({
        type: 'success',
        title: 'Creative Brief Updated in Canon',
        message: `Version ${res.bible_version} &bull; New Hash: ${res.canon_hash.substring(0, 12)}...`,
      });
    } catch (err: any) {
      showToast({
        type: 'error',
        title: 'Failed to Update Brief',
        message: err.payload?.message || err.message,
      });
    } finally {
      setSaving(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedBrief(true);
    setTimeout(() => setCopiedBrief(false), 2000);
    showToast({ type: 'success', title: 'Copied', message: 'Creative brief copied to clipboard.' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-ink-400 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-white animate-ping" />
          Loading Story Bible & Canon Hash...
        </div>
      </div>
    );
  }

  const characterEntries = Object.entries(bible?.characters || {}) as Array<[string, any]>;
  const locationEntries = Object.entries(bible?.locations || {}) as Array<[string, any]>;
  const propEntries = Object.entries(bible?.props || {}) as Array<[string, any]>;

  const activeCharacter = characterEntries.find(([id]) => id === selectedCharacterId)?.[1] || characterEntries[0]?.[1];
  const activeLocation = locationEntries.find(([id]) => id === selectedLocationId)?.[1];
  const activeProp = propEntries.find(([id]) => id === selectedPropId)?.[1];
  const style = bible?.style;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner & Hash Inspection */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-3">
              <TabCharacterIcon tab="bible" size={38} />
              Story Bible & Canon Studio
            </h1>
            <Badge variant="neutral" size="sm">
              v{bible?.bible_version || 1} Monotonic
            </Badge>
            <Badge variant={bible?.status === 'validated' ? 'success' : 'neutral'} size="sm">
              {bible?.status || 'draft'}
            </Badge>
          </div>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <span className="text-xs text-ink-400">Cryptographic Canon Hash:</span>
            <span className="font-mono text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">
              {bible?.canon_hash || 'Uncomputed'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={() => {
              fetchProposals();
              setShowProposalModal(true);
            }}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-medium transition-colors"
          >
            <GitBranch className="w-4 h-4 text-white" />
            Formal Proposals
          </button>
          <button
            onClick={handleSaveBibleDirect}
            disabled={saving}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            title="Persists any direct Story Bible changes and verifies cryptographic snapshot integrity"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving & Hashing...' : 'Save Canon'}
          </button>
        </div>
      </div>

      {/* Optimistic Concurrency Conflict Alert */}
      {conflictData && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-200 flex items-start justify-between gap-4 animate-in slide-in-from-top-2">
          <div className="flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-rose-100">
                Optimistic Concurrency Conflict (409)
              </h4>
              <p className="text-xs text-rose-300 mt-1 leading-relaxed">
                Another session or process updated this Story Bible on disk. Your in-memory edits have been preserved.
                Reload the on-disk canon to inspect recent changes, or re-save with the latest hash.
              </p>
              <div className="mt-2 text-[11px] font-mono text-rose-400">
                Current On-Disk Hash: {conflictData.current_canon_hash?.substring(0, 16)}...
              </div>
            </div>
          </div>
          <button
            onClick={fetchBible}
            className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 text-xs font-medium text-white transition-colors flex items-center gap-1.5 shrink-0"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reload On-Disk Canon
          </button>
        </div>
      )}

      {/* Category Tabs */}
      <div className="flex items-center gap-2 border-b border-white/5 pb-2 overflow-x-auto">
        {[
          { id: 'characters', label: `Characters (${characterEntries.length})`, icon: <User className="w-4 h-4" /> },
          { id: 'style', label: 'Style Bible & Constraints', icon: <Palette className="w-4 h-4" /> },
          { id: 'locations', label: `Locations (${locationEntries.length})`, icon: <MapPin className="w-4 h-4" /> },
          { id: 'props', label: `Props (${propEntries.length})`, icon: <Package className="w-4 h-4" /> },
          { id: 'story', label: 'Original Creative Brief', icon: <FileText className="w-4 h-4" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-white/10 text-white border border-white/20 font-semibold '
                : 'text-ink-400 hover:text-white hover:bg-white/5 border border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* ==================================================================== */}
      {/* 1. CHARACTERS TAB */}
      {/* ==================================================================== */}
      {activeTab === 'characters' && (
        <div className="space-y-6">
          {/* Character selector bar */}
          <div className="flex flex-wrap items-center gap-2">
            {characterEntries.map(([id, character]) => (
              <button
                key={id}
                type="button"
                className={`character-tab ${selectedCharacterId === id ? 'active' : ''}`}
                onClick={() => {
                  setSelectedCharacterId(id);
                  setIsEditingCharacter(false);
                }}
              >
                <div className="font-semibold text-white">{character.name || id}</div>
                <small className="font-mono text-ink-400">{id}</small>
              </button>
            ))}
            <button
              type="button"
              className="character-add"
              onClick={() => setShowAddCharacterModal(true)}
            >
              <Plus className="w-3.5 h-3.5" />
              Add character
            </button>
          </div>

          {activeCharacter ? (
            <Card
              title={
                isEditingCharacter
                  ? `Editing: ${characterDraft?.name || selectedCharacterId}`
                  : `Character: ${activeCharacter.name || selectedCharacterId}`
              }
              subtitle="Declared visual appearance and verification constraints compiled into prompts."
              action={
                <div className="flex items-center gap-2">
                  <Badge variant={Boolean(activeCharacter.reference_assets?.length) ? 'purple' : 'neutral'} size="sm">
                    {Boolean(activeCharacter.reference_assets?.length) ? 'Canonical Anchor' : 'No Anchor'}
                  </Badge>
                  <Badge variant="neutral" size="sm">
                    v{activeCharacter.canon_version || 1}
                  </Badge>
                  {isEditingCharacter ? (
                    <>
                      <button
                        onClick={() => {
                          setIsEditingCharacter(false);
                          setCharacterDraft(JSON.parse(JSON.stringify(activeCharacter)));
                        }}
                        className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium text-ink-300 hover:text-white transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveCharacter}
                        disabled={submittingProposal}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all"
                      >
                        <Check className="w-3.5 h-3.5" />
                        Apply Mutation
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => setIsEditingCharacter(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        Edit Character
                      </button>
                      <button
                        onClick={() => {
                          setCharToDelete(selectedCharacterId);
                          setShowDeleteCharModal(true);
                        }}
                        className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 hover:text-rose-100 border border-rose-500/20 transition-colors"
                        title="Delete character"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                </div>
              }
            >
              <div className="space-y-4 pt-2">
                {/* Canonical Reference Anchor Card */}
                {(() => {
                  const refAnchor = activeCharacter.reference_assets?.[0];
                  const isGenerating = generatingAnchor === selectedCharacterId;
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

                      {refAnchor ? (
                        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1">
                          <div className="flex items-center gap-3">
                            <img
                              src={`/api/v1/assets/${refAnchor.asset_id}/file`}
                              alt={activeCharacter.name}
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
                              onClick={() => handleGenerateAnchor(selectedCharacterId)}
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
                                  if (file) handleUploadAnchor(selectedCharacterId, file);
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
                              onClick={() => handleGenerateAnchor(selectedCharacterId)}
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
                                  if (file) handleUploadAnchor(selectedCharacterId, file);
                                }}
                              />
                            </label>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-ink-300 block mb-1">
                      Display Name <span className="text-white">*</span>
                    </label>
                    {isEditingCharacter ? (
                      <input
                        type="text"
                        value={characterDraft?.name || ''}
                        onChange={(e) => setCharacterDraft({ ...characterDraft, name: e.target.value })}
                        className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20 font-medium"
                      />
                    ) : (
                      <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs text-white font-medium">
                        {activeCharacter.name}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="text-xs font-medium text-ink-300 block mb-1">
                      Face Landmark Check
                    </label>
                    {isEditingCharacter ? (
                      <input
                        checked={characterDraft?.tolerances?.face_check_applicable === true}
                        onChange={(e) => setCharacterDraft({ ...characterDraft, tolerances: { ...characterDraft.tolerances, face_check_applicable: e.target.checked } })}
                        className="accent-white"
                        type="checkbox"
                      />
                    ) : (
                      <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs font-mono text-ink-300">
                        {activeCharacter.tolerances?.face_check_applicable ? `${activeCharacter.tolerances?.min_face_px_for_check || 80}px face landmarks` : 'Not applicable'}
                      </div>
                    )}
                  </div>
                </div>

                {/* Role & Description */}
                <div>
                  <label className="text-xs font-medium text-ink-300 block mb-1">
                    Narrative Role & Personality Description
                  </label>
                  {isEditingCharacter ? (
                    <textarea
                      rows={3}
                      value={characterDraft?.description || ''}
                      onChange={(e) => setCharacterDraft({ ...characterDraft, description: e.target.value })}
                      placeholder="Narrative role, form, personality, and background. Human anatomy is optional."
                      className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
                    />
                  ) : (
                    <div className="p-3 rounded-xl bg-ink-950 border border-white/5 text-xs text-ink-200 leading-relaxed">
                      {activeCharacter.description || <span className="italic text-ink-500">No narrative description declared</span>}
                    </div>
                  )}
                </div>

                {/* Visual Invariants */}
                <TagListEditor
                  label="Character Visual Invariants (Compiled into Every Prompt)"
                  tags={isEditingCharacter ? characterDraft?.visual_invariants || [] : activeCharacter.visual_invariants || []}
                  isEditing={isEditingCharacter}
                  variant="emerald"
                  onAdd={(tag) =>
                    setCharacterDraft({
                      ...characterDraft,
                      visual_invariants: [...(characterDraft.visual_invariants || []), tag],
                    })
                  }
                  onRemove={(idx) =>
                    setCharacterDraft({
                      ...characterDraft,
                      visual_invariants: characterDraft.visual_invariants.filter((_: any, i: number) => i !== idx),
                    })
                  }
                  placeholder="e.g. sharp white streak on left hair, wireframe round glasses..."
                />

                {/* Clothing Traits */}
                <TagListEditor
                  label="Recurring Outfit & Clothing Traits"
                  tags={isEditingCharacter ? characterDraft?.clothing_attributes || [] : activeCharacter.clothing_attributes || []}
                  isEditing={isEditingCharacter}
                  variant="neutral"
                  onAdd={(tag) =>
                    setCharacterDraft({
                      ...characterDraft,
                      clothing_attributes: [...(characterDraft.clothing_attributes || []), tag],
                    })
                  }
                  onRemove={(idx) =>
                    setCharacterDraft({
                      ...characterDraft,
                      clothing_attributes: characterDraft.clothing_attributes.filter((_: any, i: number) => i !== idx),
                    })
                  }
                  placeholder="e.g. dark oversized hooded jacket, yellow lightning emblem..."
                />

                {/* Negative Constraints */}
                <TagListEditor
                  label="Character-Specific Negative Constraints & Prohibitions"
                  tags={isEditingCharacter ? characterDraft?.restrictions || [] : activeCharacter.restrictions || []}
                  isEditing={isEditingCharacter}
                  variant="rose"
                  onAdd={(tag) =>
                    setCharacterDraft({
                      ...characterDraft,
                      restrictions: [...(characterDraft.restrictions || []), tag],
                    })
                  }
                  onRemove={(idx) =>
                    setCharacterDraft({
                      ...characterDraft,
                      restrictions: characterDraft.restrictions.filter((_: any, i: number) => i !== idx),
                    })
                  }
                  placeholder="e.g. no modern smartwatch, no colored contact lenses..."
                />

                {/* Attributes Checklist */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-medium text-ink-300">
                      Machine-Readable Verification Attributes (L2 Judge Checklist)
                    </label>
                    {isEditingCharacter && (
                      <button
                        type="button"
                        onClick={() =>
                          setCharacterDraft({
                            ...characterDraft,
                            attributes: [
                              ...(characterDraft.attributes || []),
                              {
                                id: `${selectedCharacterId}_trait_${(characterDraft.attributes?.length || 0) + 1}`,
                                text: 'Distinctive visual trait',
                                required: true,
                              },
                            ],
                          })
                        }
                        className="text-[11px] font-medium text-white hover:text-white flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" /> Add Attribute Check
                      </button>
                    )}
                  </div>

                  <div className="space-y-2">
                    {(isEditingCharacter ? characterDraft?.attributes : activeCharacter.attributes)?.map(
                      (attr: any, idx: number) => (
                        <div
                          key={attr.id || idx}
                          className="flex items-center gap-3 p-3 rounded-xl bg-ink-950/70 border border-white/5"
                        >
                          <span className="font-mono text-xs text-white font-semibold w-24 shrink-0">
                            {attr.id}
                          </span>
                          {isEditingCharacter ? (
                            <>
                              <input
                                type="text"
                                value={attr.text}
                                onChange={(e) => {
                                  const copyAttrs = [...characterDraft.attributes];
                                  copyAttrs[idx].text = e.target.value;
                                  setCharacterDraft({ ...characterDraft, attributes: copyAttrs });
                                }}
                                className="flex-1 bg-ink-900 border border-white/10 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none"
                              />
                              <label className="flex items-center gap-1.5 text-xs text-ink-300 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={attr.required}
                                  onChange={(e) => {
                                    const copyAttrs = [...characterDraft.attributes];
                                    copyAttrs[idx].required = e.target.checked;
                                    setCharacterDraft({ ...characterDraft, attributes: copyAttrs });
                                  }}
                                  className="accent-white"
                                />
                                Required
                              </label>
                              <button
                                type="button"
                                onClick={() => {
                                  const copyAttrs = characterDraft.attributes.filter((_: any, i: number) => i !== idx);
                                  setCharacterDraft({ ...characterDraft, attributes: copyAttrs });
                                }}
                                className="text-rose-400 hover:text-rose-200 p-1"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </>
                          ) : (
                            <>
                              <span className="flex-1 text-xs text-ink-200">{attr.text}</span>
                              <Badge variant={attr.required ? 'purple' : 'neutral'} size="sm">
                                {attr.required ? 'Required' : 'Optional'}
                              </Badge>
                            </>
                          )}
                        </div>
                      )
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ) : (
            <Card className="text-center py-12">
              <User className="w-10 h-10 text-ink-500 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-white">No Characters Registered</h3>
              <p className="text-xs text-ink-400 mt-1 max-w-sm mx-auto">
                Add canonical characters with visual invariants so the Agent and E1 prompt compiler can anchor identity.
              </p>
              <button
                type="button"
                onClick={() => setShowAddCharacterModal(true)}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm"
              >
                <Plus className="w-4 h-4" /> Add First Character
              </button>
            </Card>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* 2. STYLE TAB */}
      {/* ==================================================================== */}
      {activeTab === 'style' && (
        <Card
          title={isEditingStyle ? 'Editing: Style Bible & Constraints' : 'Style Bible & Constraints'}
          subtitle="Global rendering medium, line art conventions, tonal shading, and negative prompt rules."
          action={
            isEditingStyle ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setIsEditingStyle(false);
                    setStyleDraft(JSON.parse(JSON.stringify(bible.style)));
                  }}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium text-ink-300 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveStyle}
                  disabled={submittingProposal}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all"
                >
                  <Check className="w-3.5 h-3.5" />
                  Apply Mutation
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsEditingStyle(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
              >
                <Edit3 className="w-3.5 h-3.5" />
                Edit Style Bible
              </button>
            )
          }
        >
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">
                  Style Name <span className="text-white">*</span>
                </label>
                {isEditingStyle ? (
                  <input
                    type="text"
                    value={styleDraft?.name || ''}
                    onChange={(e) => setStyleDraft({ ...styleDraft, name: e.target.value })}
                    className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
                  />
                ) : (
                  <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs text-white font-medium">
                    {style?.name || 'Untitled Style'}
                  </div>
                )}
              </div>

              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">Medium</label>
                {isEditingStyle ? (
                  <input
                    type="text"
                    value={styleDraft?.medium || ''}
                    onChange={(e) => setStyleDraft({ ...styleDraft, medium: e.target.value })}
                    className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
                  />
                ) : (
                  <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs text-white font-medium">
                    {style?.medium || 'digital ink'}
                  </div>
                )}
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">Visual Rendering Approach</label>
              {isEditingStyle ? (
                <textarea
                  rows={2}
                  value={styleDraft?.rendering_approach || ''}
                  onChange={(e) => setStyleDraft({ ...styleDraft, rendering_approach: e.target.value })}
                  placeholder="e.g. black-and-white high contrast with screentone shading and solid black shadows"
                  className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
                />
              ) : (
                <div className="p-3 rounded-xl bg-ink-950 border border-white/5 text-xs text-ink-200">
                  {style?.rendering_approach || <span className="italic text-ink-500">Not specified</span>}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Line Art Rules */}
              <TagListEditor
                label="Line Art Rules"
                tags={isEditingStyle ? styleDraft?.line_art_rules || [] : style?.line_art_rules || []}
                isEditing={isEditingStyle}
                variant="neutral"
                onAdd={(tag) =>
                  setStyleDraft({
                    ...styleDraft,
                    line_art_rules: [...(styleDraft.line_art_rules || []), tag],
                  })
                }
                onRemove={(idx) =>
                  setStyleDraft({
                    ...styleDraft,
                    line_art_rules: styleDraft.line_art_rules.filter((_: any, i: number) => i !== idx),
                  })
                }
                placeholder="e.g. clean contour lines, variable line weight..."
              />

              {/* Tonal Rules */}
              <TagListEditor
                label="Tonal Shading Rules"
                tags={isEditingStyle ? styleDraft?.tonal_rules || [] : style?.tonal_rules || []}
                isEditing={isEditingStyle}
                variant="neutral"
                onAdd={(tag) =>
                  setStyleDraft({
                    ...styleDraft,
                    tonal_rules: [...(styleDraft.tonal_rules || []), tag],
                  })
                }
                onRemove={(idx) =>
                  setStyleDraft({
                    ...styleDraft,
                    tonal_rules: styleDraft.tonal_rules.filter((_: any, i: number) => i !== idx),
                  })
                }
                placeholder="e.g. 60-line screentone, solid black fill, hatched shading..."
              />
            </div>

            {/* Background Detail Rules */}
            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">Background Detail Rules</label>
              {isEditingStyle ? (
                <input
                  type="text"
                  value={styleDraft?.background_detail_rules || ''}
                  onChange={(e) => setStyleDraft({ ...styleDraft, background_detail_rules: e.target.value })}
                  placeholder="e.g. architectural backgrounds in wide shots; minimalist focus on character in closeups"
                  className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
                />
              ) : (
                <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs text-ink-200">
                  {style?.background_detail_rules || <span className="italic text-ink-500">Not specified</span>}
                </div>
              )}
            </div>

            {/* Negative Constraints */}
            <TagListEditor
              label="Style Negative Constraints (Forbidden Visual Artifacts)"
              tags={isEditingStyle ? styleDraft?.negative_constraints || [] : style?.negative_constraints || []}
              isEditing={isEditingStyle}
              variant="amber"
              onAdd={(tag) =>
                setStyleDraft({
                  ...styleDraft,
                  negative_constraints: [...(styleDraft.negative_constraints || []), tag],
                })
              }
              onRemove={(idx) =>
                setStyleDraft({
                  ...styleDraft,
                  negative_constraints: styleDraft.negative_constraints.filter((_: any, i: number) => i !== idx),
                })
              }
              placeholder="e.g. no color, no 3D photorealism, no baked-in dialogue bubbles..."
            />

            {/* Positive Constraints */}
            <TagListEditor
              label="Style Positive Constraints (Mandatory Prompt Clauses)"
              tags={isEditingStyle ? styleDraft?.positive_constraints || [] : style?.positive_constraints || []}
              isEditing={isEditingStyle}
              variant="emerald"
              onAdd={(tag) =>
                setStyleDraft({
                  ...styleDraft,
                  positive_constraints: [...(styleDraft.positive_constraints || []), tag],
                })
              }
              onRemove={(idx) =>
                setStyleDraft({
                  ...styleDraft,
                  positive_constraints: styleDraft.positive_constraints.filter((_: any, i: number) => i !== idx),
                })
              }
              placeholder="e.g. manga aesthetic, clean inking, high contrast monochrome..."
            />
          </div>
        </Card>
      )}

      {/* ==================================================================== */}
      {/* 3. LOCATIONS TAB */}
      {/* ==================================================================== */}
      {activeTab === 'locations' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              {locationEntries.map(([id, loc]) => (
                <button
                  key={id}
                  type="button"
                  className={`character-tab ${selectedLocationId === id ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedLocationId(id);
                    setIsEditingLocation(false);
                  }}
                >
                  <div className="font-semibold text-white">{loc.name || id}</div>
                  <small className="font-mono text-ink-400">{id}</small>
                </button>
              ))}
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all"
              onClick={() => setShowAddLocationModal(true)}
            >
              <Plus className="w-3.5 h-3.5" /> Add Location
            </button>
          </div>

          {activeLocation ? (
            <Card
              title={
                isEditingLocation
                  ? `Editing Location: ${locationDraft?.name || selectedLocationId}`
                  : `Location: ${activeLocation.name || selectedLocationId}`
              }
              subtitle="Declared canonical environment for consistent architecture, lighting, and weather."
              action={
                isEditingLocation ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setIsEditingLocation(false);
                        setLocationDraft(JSON.parse(JSON.stringify(activeLocation)));
                      }}
                      className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium text-ink-300 hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveLocation}
                      disabled={submittingProposal}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Apply Mutation
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setIsEditingLocation(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      Edit Location
                    </button>
                    <button
                      onClick={() => {
                        setLocToDelete(selectedLocationId);
                        setShowDeleteLocModal(true);
                      }}
                      className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 hover:text-rose-100 border border-rose-500/20 transition-colors"
                      title="Delete location"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )
              }
            >
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-ink-300 block mb-1">
                      Location Display Name <span className="text-white">*</span>
                    </label>
                    {isEditingLocation ? (
                      <input
                        type="text"
                        value={locationDraft?.name || ''}
                        onChange={(e) => setLocationDraft({ ...locationDraft, name: e.target.value })}
                        className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
                      />
                    ) : (
                      <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs text-white font-medium">
                        {activeLocation.name}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="text-xs font-medium text-ink-300 block mb-1">Location Identifier</label>
                    <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs font-mono text-ink-400">
                      {selectedLocationId}
                    </div>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium text-ink-300 block mb-1">Architectural Description</label>
                  {isEditingLocation ? (
                    <textarea
                      rows={3}
                      value={locationDraft?.description || ''}
                      onChange={(e) => setLocationDraft({ ...locationDraft, description: e.target.value })}
                      placeholder="Detailed spatial layout, materials, furniture, lighting defaults..."
                      className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
                    />
                  ) : (
                    <div className="p-3 rounded-xl bg-ink-950 border border-white/5 text-xs text-ink-200 leading-relaxed">
                      {activeLocation.description || <span className="italic text-ink-500">No description declared</span>}
                    </div>
                  )}
                </div>

                {/* Required Attributes */}
                <TagListEditor
                  label="Required Visual Features (Mandatory Architecture)"
                  tags={isEditingLocation ? locationDraft?.required_attributes || [] : activeLocation.required_attributes || []}
                  isEditing={isEditingLocation}
                  variant="neutral"
                  onAdd={(tag) =>
                    setLocationDraft({
                      ...locationDraft,
                      required_attributes: [...(locationDraft.required_attributes || []), tag],
                    })
                  }
                  onRemove={(idx) =>
                    setLocationDraft({
                      ...locationDraft,
                      required_attributes: locationDraft.required_attributes.filter((_: any, i: number) => i !== idx),
                    })
                  }
                  placeholder="e.g. neon sign in window, copper counter, large wall clock..."
                />

                {/* Permitted Variations */}
                <TagListEditor
                  label="Permitted Environmental Variations"
                  tags={isEditingLocation ? locationDraft?.permitted_variations || [] : activeLocation.permitted_variations || []}
                  isEditing={isEditingLocation}
                  variant="neutral"
                  onAdd={(tag) =>
                    setLocationDraft({
                      ...locationDraft,
                      permitted_variations: [...(locationDraft.permitted_variations || []), tag],
                    })
                  }
                  onRemove={(idx) =>
                    setLocationDraft({
                      ...locationDraft,
                      permitted_variations: locationDraft.permitted_variations.filter((_: any, i: number) => i !== idx),
                    })
                  }
                  placeholder="e.g. night illumination, rainy exterior through glass..."
                />
              </div>
            </Card>
          ) : (
            <Card className="text-center py-12">
              <MapPin className="w-10 h-10 text-ink-500 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-white">No Canonical Locations Registered</h3>
              <p className="text-xs text-ink-400 mt-1 max-w-sm mx-auto">
                Define canonical settings so character interactions and background details maintain spatial continuity.
              </p>
              <button
                type="button"
                onClick={() => setShowAddLocationModal(true)}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm"
              >
                <Plus className="w-4 h-4" /> Add First Location
              </button>
            </Card>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* 4. PROPS TAB */}
      {/* ==================================================================== */}
      {activeTab === 'props' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              {propEntries.map(([id, prop]) => (
                <button
                  key={id}
                  type="button"
                  className={`character-tab ${selectedPropId === id ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedPropId(id);
                    setIsEditingProp(false);
                  }}
                >
                  <div className="font-semibold text-white">{prop.name || id}</div>
                  <small className="font-mono text-ink-400">{id}</small>
                </button>
              ))}
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all"
              onClick={() => setShowAddPropModal(true)}
            >
              <Plus className="w-3.5 h-3.5" /> Add Prop
            </button>
          </div>

          {activeProp ? (
            <Card
              title={
                isEditingProp
                  ? `Editing Prop: ${propDraft?.name || selectedPropId}`
                  : `Prop: ${activeProp.name || selectedPropId}`
              }
              subtitle="Declared recurring object with verified physical dimensions, material, and character ownership."
              action={
                isEditingProp ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setIsEditingProp(false);
                        setPropDraft(JSON.parse(JSON.stringify(activeProp)));
                      }}
                      className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium text-ink-300 hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveProp}
                      disabled={submittingProposal}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Apply Mutation
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setIsEditingProp(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      Edit Prop
                    </button>
                    <button
                      onClick={() => {
                        setPropToDelete(selectedPropId);
                        setShowDeletePropModal(true);
                      }}
                      className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 hover:text-rose-100 border border-rose-500/20 transition-colors"
                      title="Delete prop"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )
              }
            >
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-ink-300 block mb-1">
                      Prop Name <span className="text-white">*</span>
                    </label>
                    {isEditingProp ? (
                      <input
                        type="text"
                        value={propDraft?.name || ''}
                        onChange={(e) => setPropDraft({ ...propDraft, name: e.target.value })}
                        className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
                      />
                    ) : (
                      <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs text-white font-medium">
                        {activeProp.name}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="text-xs font-medium text-ink-300 block mb-1">Prop Identifier</label>
                    <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 text-xs font-mono text-ink-400">
                      {selectedPropId}
                    </div>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium text-ink-300 block mb-1">Visual & Physical Description</label>
                  {isEditingProp ? (
                    <textarea
                      rows={3}
                      value={propDraft?.description || ''}
                      onChange={(e) => setPropDraft({ ...propDraft, description: e.target.value })}
                      placeholder="Shape, materials, distinctive engravings, scale relative to hands..."
                      className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
                    />
                  ) : (
                    <div className="p-3 rounded-xl bg-ink-950 border border-white/5 text-xs text-ink-200 leading-relaxed">
                      {activeProp.description || <span className="italic text-ink-500">No description declared</span>}
                    </div>
                  )}
                </div>

                {/* Required Attributes */}
                <TagListEditor
                  label="Required Visual Attributes (Materials & Markings)"
                  tags={isEditingProp ? propDraft?.required_attributes || [] : activeProp.required_attributes || []}
                  isEditing={isEditingProp}
                  variant="neutral"
                  onAdd={(tag) =>
                    setPropDraft({
                      ...propDraft,
                      required_attributes: [...(propDraft.required_attributes || []), tag],
                    })
                  }
                  onRemove={(idx) =>
                    setPropDraft({
                      ...propDraft,
                      required_attributes: propDraft.required_attributes.filter((_: any, i: number) => i !== idx),
                    })
                  }
                  placeholder="e.g. brushed brass surface, carved eagle sigil..."
                />

                {/* Associated Characters */}
                <TagListEditor
                  label="Associated Character Owners / Users"
                  tags={isEditingProp ? propDraft?.associated_character_ids || [] : activeProp.associated_character_ids || []}
                  isEditing={isEditingProp}
                  variant="emerald"
                  onAdd={(tag) =>
                    setPropDraft({
                      ...propDraft,
                      associated_character_ids: [...(propDraft.associated_character_ids || []), tag.toLowerCase()],
                    })
                  }
                  onRemove={(idx) =>
                    setPropDraft({
                      ...propDraft,
                      associated_character_ids: propDraft.associated_character_ids.filter((_: any, i: number) => i !== idx),
                    })
                  }
                  placeholder="e.g. nour, layla..."
                />
              </div>
            </Card>
          ) : (
            <Card className="text-center py-12">
              <Package className="w-10 h-10 text-ink-500 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-white">No Canonical Props Declared</h3>
              <p className="text-xs text-ink-400 mt-1 max-w-sm mx-auto">
                Declare significant narrative objects and weapons to prevent visual drift and verify continuity across panels.
              </p>
              <button
                type="button"
                onClick={() => setShowAddPropModal(true)}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm"
              >
                <Plus className="w-4 h-4" /> Add First Prop
              </button>
            </Card>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* 5. ORIGINAL USER TEXT (CREATIVE BRIEF) */}
      {/* ==================================================================== */}
      {activeTab === 'story' && (
        <Card
          title="Preserved Creative Brief (Immutable Story Source)"
          subtitle="Original user narrative preserved byte-for-byte in accordance with ADR-008. Primary input for scene extraction."
          action={
            isRevisingStory ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setIsRevisingStory(false);
                    setStoryDraft(bible?.user_story_text || '');
                  }}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium text-ink-300 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveRevisedBrief}
                  disabled={saving}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all"
                >
                  <Save className="w-3.5 h-3.5" />
                  Save Revised Brief
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => copyToClipboard(bible?.user_story_text || '')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
                >
                  {copiedBrief ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedBrief ? 'Copied' : 'Copy'}
                </button>
                <button
                  onClick={() => setIsRevisingStory(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  Revise Brief
                </button>
              </div>
            )
          }
        >
          <div className="space-y-4 pt-2">
            {isRevisingStory ? (
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    Modifying the creative brief updates the project source narrative input and recalculates the canon hash upon save.
                  </span>
                </div>
                <textarea
                  dir="auto"
                  rows={10}
                  value={storyDraft}
                  onChange={(e) => setStoryDraft(e.target.value)}
                  placeholder="Enter story brief or scene script (Arabic RTL or English supported)..."
                  className="w-full bg-ink-950 border border-white/10 rounded-xl p-4 text-xs text-white focus:outline-none focus:border-white/20 font-sans leading-relaxed"
                />
              </div>
            ) : (
              <div className="space-y-3">
                <div
                  dir="auto"
                  className="w-full min-h-[160px] max-h-[420px] overflow-y-auto p-4 rounded-xl bg-ink-950 border border-white/5 text-xs text-ink-100 font-sans leading-relaxed whitespace-pre-wrap select-text"
                >
                  {bible?.user_story_text ? (
                    bible.user_story_text
                  ) : (
                    <span className="italic text-ink-500">No creative brief or user story text recorded.</span>
                  )}
                </div>

                <div className="flex items-center justify-between text-[11px] text-ink-400 px-1">
                  <span>
                    {bible?.user_story_text ? `${bible.user_story_text.length} characters` : '0 characters'}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    Preserved byte-for-byte in Story Bible
                  </span>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* ==================================================================== */}
      {/* PROPOSAL PREVIEW & CONFIRMATION MODAL */}
      {/* ==================================================================== */}
      <Modal
        isOpen={proposalPreview.isOpen}
        onClose={() => setProposalPreview((prev) => ({ ...prev, isOpen: false }))}
        title="Review & Apply Canon Mutation"
        maxWidth="md"
        footer={
          <>
            <button
              type="button"
              onClick={() => setProposalPreview((prev) => ({ ...prev, isOpen: false }))}
              disabled={submittingProposal}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() =>
                applyCanonProposal(
                  proposalPreview.targetType,
                  proposalPreview.targetId,
                  proposalPreview.description,
                  proposalPreview.changes
                )
              }
              disabled={submittingProposal}
              className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              {submittingProposal ? 'Applying Mutation...' : 'Approve & Apply to Canon'}
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-ink-300">
            Confirming this mutation will create an approved record in the audit log, increment monotonic version to{' '}
            <strong className="text-white">v{(bible?.bible_version || 1) + 1}</strong>, and update the cryptographic canon hash.
          </p>

          <div className="p-3 rounded-xl bg-ink-950 border border-white/5 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-ink-400">Target Entity:</span>
              <span className="font-semibold text-white capitalize">
                {proposalPreview.targetType}: <span className="font-mono text-white">{proposalPreview.targetId}</span>
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-ink-400">Operation:</span>
              <Badge variant={proposalPreview.changes?.action === 'delete' ? 'danger' : 'purple'} size="sm">
                {proposalPreview.changes?.action?.toUpperCase() || 'UPDATE'}
              </Badge>
            </div>
            <div className="pt-1">
              <span className="text-ink-400 block mb-1">Description / Rationale:</span>
              <p className="text-ink-200 italic">{proposalPreview.description}</p>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Proposed Delta</label>
            <pre className="p-3 rounded-xl bg-ink-950 font-mono text-[11px] text-white max-h-48 overflow-auto border border-white/5">
              {JSON.stringify(proposalPreview.changes, null, 2)}
            </pre>
          </div>
        </div>
      </Modal>

      {/* ==================================================================== */}
      {/* FORMAL PROPOSALS AUDIT / CUSTOM MODAL */}
      {/* ==================================================================== */}
      <Modal
        isOpen={showProposalModal}
        onClose={() => setShowProposalModal(false)}
        title="Formal Canon Mutation Proposals"
        maxWidth="lg"
        footer={
          <button
            onClick={() => setShowProposalModal(false)}
            className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white transition-colors"
          >
            Close
          </button>
        }
      >
        <div className="space-y-4">
          <div className="flex gap-2 border-b border-white/5 pb-2">
            <button
              onClick={() => setProposalsTab('pending')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                proposalsTab === 'pending'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-ink-400 hover:text-white'
              }`}
            >
              Audit History ({pendingProposals.length})
            </button>
            <button
              onClick={() => setProposalsTab('custom')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                proposalsTab === 'custom'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-ink-400 hover:text-white'
              }`}
            >
              Manual Proposal
            </button>
          </div>

          {proposalsTab === 'pending' ? (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {loadingProposals ? (
                <div className="py-8 text-center text-xs text-ink-400">Loading audit history...</div>
              ) : pendingProposals.length === 0 ? (
                <div className="py-8 text-center text-xs text-ink-400">No mutation proposals recorded yet.</div>
              ) : (
                pendingProposals.map((p, idx) => (
                  <div key={p.proposal_id || idx} className="p-3 rounded-xl bg-ink-950 border border-white/5 text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-white font-semibold">{p.proposal_id}</span>
                      <Badge
                        variant={p.status === 'approved' ? 'success' : p.status === 'rejected' ? 'danger' : 'warning'}
                        size="sm"
                      >
                        {p.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 text-ink-400">
                      <span className="capitalize">{p.target_type}: {p.target_id}</span>
                      <span>&bull;</span>
                      <span>{p.created_at ? new Date(p.created_at).toLocaleString() : 'Recent'}</span>
                    </div>
                    <p className="text-ink-200">{p.change_description}</p>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-ink-300 block mb-1">Target Type</label>
                  <select
                    value={mutationTargetType}
                    onChange={(e) => setMutationTargetType(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
                  >
                    <option value="character">Character</option>
                    <option value="style">Style</option>
                    <option value="location">Location</option>
                    <option value="prop">Prop</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-ink-300 block mb-1">Target ID</label>
                  <input
                    type="text"
                    value={mutationTargetId}
                    onChange={(e) => setMutationTargetId(e.target.value)}
                    placeholder="e.g. nour, cafe_interior..."
                    className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">Proposal Rationale</label>
                <input
                  type="text"
                  placeholder="e.g. Update battle costume for Scene 4"
                  value={mutationDescription}
                  onChange={(e) => setMutationDescription(e.target.value)}
                  className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-ink-300 block mb-1">Proposed JSON Delta</label>
                <textarea
                  rows={4}
                  value={mutationChangesJson}
                  onChange={(e) => setMutationChangesJson(e.target.value)}
                  className="w-full font-mono bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
                />
              </div>

              <button
                type="button"
                onClick={async () => {
                  try {
                    const parsed = JSON.parse(mutationChangesJson);
                    await applyCanonProposal(mutationTargetType, mutationTargetId, mutationDescription, parsed);
                    setShowProposalModal(false);
                  } catch (err: any) {
                    showToast({ type: 'error', title: 'Invalid JSON', message: err.message });
                  }
                }}
                disabled={submittingProposal || !mutationDescription.trim() || !mutationTargetId.trim()}
                className="w-full py-2.5 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm disabled:opacity-40"
              >
                {submittingProposal ? 'Applying Mutation...' : 'Submit & Apply Custom Proposal'}
              </button>
            </div>
          )}
        </div>
      </Modal>

      {/* ==================================================================== */}
      {/* ADD CHARACTER MODAL */}
      {/* ==================================================================== */}
      <Modal
        isOpen={showAddCharacterModal}
        onClose={() => setShowAddCharacterModal(false)}
        title="Add Canonical Character"
        maxWidth="md"
        footer={
          <>
            <button
              type="button"
              onClick={() => setShowAddCharacterModal(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              form="add-character-form"
              disabled={submittingProposal || !newChar.name.trim()}
              className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              {submittingProposal ? 'Adding...' : 'Add Character to Canon'}
            </button>
          </>
        }
      >
        <form id="add-character-form" onSubmit={handleCreateNewCharacter} className="space-y-4">
          <p className="text-xs text-ink-300">
            Define any being once so the Agent can preserve its declared shape and identity features across generated panels.
          </p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">
                Character Name <span className="text-white">*</span>
              </label>
              <input
                type="text"
                autoFocus
                placeholder="e.g. Aya"
                value={newChar.name}
                onChange={(e) => {
                  const val = e.target.value;
                  setNewChar((prev) => ({
                    ...prev,
                    name: val,
                    id: !prev.id || prev.id === prev.name.toLowerCase().replace(/[^a-z0-9_]/g, '_')
                      ? val.toLowerCase().replace(/[^a-z0-9_]/g, '_')
                      : prev.id,
                  }));
                }}
                className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">Slug / ID</label>
              <input
                type="text"
                placeholder="e.g. aya"
                value={newChar.id}
                onChange={(e) => setNewChar({ ...newChar, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-white/20"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Role in Story</label>
            <input
              type="text"
              placeholder="e.g. Rival Hacker, Supporting Detective, Squad Leader"
              value={newChar.role}
              onChange={(e) => setNewChar({ ...newChar, role: e.target.value })}
              className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Kind of being (open-ended)</label>
            <input
              value={newChar.entityKind}
              onChange={(e) => setNewChar({ ...newChar, entityKind: e.target.value })}
              placeholder="Human, animal, monster, masked figure, headless creature, smiling circle, or anything else"
              className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Visual Appearance & Silhouette</label>
            <textarea
              rows={3}
              placeholder="Describe any form: a smiling circle, masked traveler, headless creature, monster, animal, or person"
              value={newChar.desc}
              onChange={(e) => setNewChar({ ...newChar, desc: e.target.value })}
              className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>

          <TagListEditor
            label="Visual Invariants (Hard Non-Negotiables)"
            tags={newChar.invariants}
            isEditing={true}
            variant="emerald"
            onAdd={(tag) => setNewChar({ ...newChar, invariants: [...newChar.invariants, tag] })}
            onRemove={(idx) => setNewChar({ ...newChar, invariants: newChar.invariants.filter((_, i) => i !== idx) })}
            placeholder="e.g. exactly circular, one painted smile, no head or limbs..."
          />
          <label className="flex items-center gap-2 text-xs text-ink-300">
            <input type="checkbox" checked={newChar.faceCheckApplicable} onChange={(e) => setNewChar({ ...newChar, faceCheckApplicable: e.target.checked })} className="accent-white" />
            Face landmarks apply to this being
          </label>
        </form>
      </Modal>

      {/* ==================================================================== */}
      {/* ADD LOCATION MODAL */}
      {/* ==================================================================== */}
      <Modal
        isOpen={showAddLocationModal}
        onClose={() => setShowAddLocationModal(false)}
        title="Add Canonical Location"
        maxWidth="md"
        footer={
          <>
            <button
              type="button"
              onClick={() => setShowAddLocationModal(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              form="add-location-form"
              disabled={submittingProposal || !newLoc.name.trim()}
              className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              {submittingProposal ? 'Adding...' : 'Add Location to Canon'}
            </button>
          </>
        }
      >
        <form id="add-location-form" onSubmit={handleCreateNewLocation} className="space-y-4">
          <p className="text-xs text-ink-300">
            Define canonical architectural features so background generation maintains spatial fidelity across scene cuts.
          </p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">
                Location Name <span className="text-white">*</span>
              </label>
              <input
                type="text"
                autoFocus
                placeholder="e.g. Neon Cafe"
                value={newLoc.name}
                onChange={(e) => {
                  const val = e.target.value;
                  setNewLoc((prev) => ({
                    ...prev,
                    name: val,
                    id: !prev.id || prev.id === prev.name.toLowerCase().replace(/[^a-z0-9_]/g, '_')
                      ? val.toLowerCase().replace(/[^a-z0-9_]/g, '_')
                      : prev.id,
                  }));
                }}
                className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">Location Slug / ID</label>
              <input
                type="text"
                placeholder="e.g. neon_cafe"
                value={newLoc.id}
                onChange={(e) => setNewLoc({ ...newLoc, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-white/20"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Architectural Description</label>
            <textarea
              rows={3}
              placeholder="e.g. Grimy cyberpunk noodle bar with rain-slicked glass counter and hanging lanterns..."
              value={newLoc.desc}
              onChange={(e) => setNewLoc({ ...newLoc, desc: e.target.value })}
              className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>

          <TagListEditor
            label="Required Visual Features"
            tags={newLoc.requiredAttributes}
            isEditing={true}
            variant="neutral"
            onAdd={(tag) => setNewLoc({ ...newLoc, requiredAttributes: [...newLoc.requiredAttributes, tag] })}
            onRemove={(idx) => setNewLoc({ ...newLoc, requiredAttributes: newLoc.requiredAttributes.filter((_, i) => i !== idx) })}
            placeholder="e.g. neon sign in window, copper counter, large wall clock..."
          />
        </form>
      </Modal>

      {/* ==================================================================== */}
      {/* ADD PROP MODAL */}
      {/* ==================================================================== */}
      <Modal
        isOpen={showAddPropModal}
        onClose={() => setShowAddPropModal(false)}
        title="Add Canonical Prop"
        maxWidth="md"
        footer={
          <>
            <button
              type="button"
              onClick={() => setShowAddPropModal(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              form="add-prop-form"
              disabled={submittingProposal || !newProp.name.trim()}
              className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              {submittingProposal ? 'Adding...' : 'Add Prop to Canon'}
            </button>
          </>
        }
      >
        <form id="add-prop-form" onSubmit={handleCreateNewProp} className="space-y-4">
          <p className="text-xs text-ink-300">
            Define canonical objects, weapons, or relics to anchor visual continuity and character ownership.
          </p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">
                Prop Name <span className="text-white">*</span>
              </label>
              <input
                type="text"
                autoFocus
                placeholder="e.g. Brass Skeleton Key"
                value={newProp.name}
                onChange={(e) => {
                  const val = e.target.value;
                  setNewProp((prev) => ({
                    ...prev,
                    name: val,
                    id: !prev.id || prev.id === prev.name.toLowerCase().replace(/[^a-z0-9_]/g, '_')
                      ? val.toLowerCase().replace(/[^a-z0-9_]/g, '_')
                      : prev.id,
                  }));
                }}
                className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/20"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-ink-300 block mb-1">Prop Slug / ID</label>
              <input
                type="text"
                placeholder="e.g. brass_key"
                value={newProp.id}
                onChange={(e) => setNewProp({ ...newProp, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                className="w-full bg-ink-950 border border-white/10 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-white/20"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-ink-300 block mb-1">Visual & Physical Description</label>
            <textarea
              rows={3}
              placeholder="e.g. Heavy tarnished brass key with intricate clockwork gear teeth and worn leather cord..."
              value={newProp.desc}
              onChange={(e) => setNewProp({ ...newProp, desc: e.target.value })}
              className="w-full bg-ink-950 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/20"
            />
          </div>

          <TagListEditor
            label="Required Visual Markings / Materials"
            tags={newProp.requiredAttributes}
            isEditing={true}
            variant="neutral"
            onAdd={(tag) => setNewProp({ ...newProp, requiredAttributes: [...newProp.requiredAttributes, tag] })}
            onRemove={(idx) => setNewProp({ ...newProp, requiredAttributes: newProp.requiredAttributes.filter((_, i) => i !== idx) })}
            placeholder="e.g. tarnished brass, engraved gear emblem..."
          />

          <TagListEditor
            label="Associated Character Slugs (Owners/Holders)"
            tags={newProp.associatedCharacters}
            isEditing={true}
            variant="emerald"
            onAdd={(tag) => setNewProp({ ...newProp, associatedCharacters: [...newProp.associatedCharacters, tag.toLowerCase()] })}
            onRemove={(idx) => setNewProp({ ...newProp, associatedCharacters: newProp.associatedCharacters.filter((_, i) => i !== idx) })}
            placeholder="e.g. nour..."
          />
        </form>
      </Modal>

      {/* ==================================================================== */}
      {/* DELETE CONFIRMATION MODALS */}
      {/* ==================================================================== */}
      <Modal
        isOpen={showDeleteCharModal}
        onClose={() => setShowDeleteCharModal(false)}
        title="Remove Character from Canon"
        maxWidth="sm"
        footer={
          <>
            <button
              onClick={() => setShowDeleteCharModal(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDeleteCharacter}
              disabled={submittingProposal}
              className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-600 text-white text-xs font-semibold  transition-all"
            >
              {submittingProposal ? 'Removing...' : 'Confirm Delete'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-xs text-ink-200">
            Are you sure you want to remove <strong className="text-white">{charToDelete}</strong> from the Story Bible?
          </p>
          <p className="text-xs text-ink-400">
            This will record a formal deletion mutation, increment the canon version, and update the cryptographic snapshot hash.
          </p>
        </div>
      </Modal>

      <Modal
        isOpen={showDeleteLocModal}
        onClose={() => setShowDeleteLocModal(false)}
        title="Remove Location from Canon"
        maxWidth="sm"
        footer={
          <>
            <button
              onClick={() => setShowDeleteLocModal(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDeleteLocation}
              disabled={submittingProposal}
              className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-600 text-white text-xs font-semibold  transition-all"
            >
              {submittingProposal ? 'Removing...' : 'Confirm Delete'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-xs text-ink-200">
            Are you sure you want to remove location <strong className="text-white">{locToDelete}</strong> from canon?
          </p>
          <p className="text-xs text-ink-400">
            This will create an approved deletion proposal and increment the canon version.
          </p>
        </div>
      </Modal>

      <Modal
        isOpen={showDeletePropModal}
        onClose={() => setShowDeletePropModal(false)}
        title="Remove Prop from Canon"
        maxWidth="sm"
        footer={
          <>
            <button
              onClick={() => setShowDeletePropModal(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-ink-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDeleteProp}
              disabled={submittingProposal}
              className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-600 text-white text-xs font-semibold  transition-all"
            >
              {submittingProposal ? 'Removing...' : 'Confirm Delete'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-xs text-ink-200">
            Are you sure you want to remove prop <strong className="text-white">{propToDelete}</strong> from canon?
          </p>
          <p className="text-xs text-ink-400">
            This will create an approved deletion proposal and increment the canon version.
          </p>
        </div>
      </Modal>
    </div>
  );
};
