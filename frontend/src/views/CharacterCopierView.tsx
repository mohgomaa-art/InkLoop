import React, { useEffect, useState, useRef } from 'react';
import {
  UserCheck,
  Sparkles,
  Upload,
  Trash2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Eye,
  Info,
  Camera,
  Layers,
  FileCode,
  AlertTriangle,
  BookOpen,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { useToast } from '../components/common/Toast';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import type {
  CharacterCopierProfile,
  StyleProfile,
  ProviderCapabilities,
  ReferenceBinding,
  CharacterViewRole,
  SemanticReferenceRole,
  CreativeGenerationResult,
} from '../types/creative';

interface CharacterCopierViewProps {
  currentProject: string;
}

export const CharacterCopierView: React.FC<CharacterCopierViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();

  // State
  const [profiles, setProfiles] = useState<CharacterCopierProfile[]>([]);
  const [activeProfile, setActiveProfile] = useState<CharacterCopierProfile | null>(null);
  const [canonCharacterIds, setCanonCharacterIds] = useState<string[]>([]);
  const [capabilities, setCapabilities] = useState<ProviderCapabilities | null>(null);
  const [availableAssets, setAvailableAssets] = useState<any[]>([]);
  const [availableStyles, setAvailableStyles] = useState<StyleProfile[]>([]);
  const [selectedStyleId, setSelectedStyleId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingSheet, setGeneratingSheet] = useState(false);
  const [renderingSheet, setRenderingSheet] = useState(false);
  const [renderedSheet, setRenderedSheet] = useState<any | null>(null);
  const [proposingCanon, setProposingCanon] = useState(false);
  const [assetModalOpen, setAssetModalOpen] = useState(false);
  const [canonModalOpen, setCanonModalOpen] = useState(false);
  const [canonReason, setCanonReason] = useState('');
  const [sheetPlan, setSheetPlan] = useState<any | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Combined generation states
  const [testActionPrompt, setTestActionPrompt] = useState('reacting with intense emotion in a pivotal dramatic scene');
  const [testShotType, setTestShotType] = useState('Dynamic low-angle hero shot');
  const [generatingTest, setGeneratingTest] = useState(false);
  const [testResult, setTestResult] = useState<CreativeGenerationResult | null>(null);

  // Form states
  const [characterId, setCharacterId] = useState('');
  const [name, setName] = useState('');
  const [entityKind, setEntityKind] = useState('unspecified being');
  const [morphology, setMorphology] = useState('');
  const [surfaceDescription, setSurfaceDescription] = useState('');
  const [partsText, setPartsText] = useState('');
  const [sensoryFeaturesText, setSensoryFeaturesText] = useState('');
  const [locomotion, setLocomotion] = useState('');
  const [faceCheckApplicable, setFaceCheckApplicable] = useState(false);
  const [promptIdentityCore, setPromptIdentityCore] = useState('');
  const [invariants, setInvariants] = useState<string[]>([]);
  const [newInvariant, setNewInvariant] = useState('');
  const [variations, setVariations] = useState<string[]>([]);
  const [newVariation, setNewVariation] = useState('');
  const [forbiddenDrift, setForbiddenDrift] = useState<string[]>([]);
  const [newForbidden, setNewForbidden] = useState('');
  const [uncertainTraits, setUncertainTraits] = useState<string[]>([]);
  const [references, setReferences] = useState<ReferenceBinding[]>([]);

  // Load initial data
  const loadData = async () => {
    try {
      setLoading(true);
      const [caps, profs, assets, styles, bible] = await Promise.all([
        apiClient.getCreativeCapabilities(currentProject).catch(() => null),
        apiClient.listCharacterProfiles(currentProject).catch(() => []),
        apiClient.listAssets({ project_id: currentProject }).catch(() => []),
        apiClient.listStyleProfiles(currentProject).catch(() => []),
        apiClient.getProjectBible(currentProject).catch(() => null),
      ]);

      if (caps) setCapabilities(caps);
      setProfiles(profs);
      setAvailableAssets(assets);
      setAvailableStyles(styles);
      setCanonCharacterIds(Object.keys(bible?.characters || {}));
      if (styles.length > 0 && !selectedStyleId) {
        setSelectedStyleId(styles[0].profile_id);
      }

      if (profs.length > 0 && !activeProfile) {
        selectProfile(profs[0]);
      } else if (profs.length === 0) {
        createNewProfile();
      }
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to load Character Copier data', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [currentProject]);

  const selectProfile = (p: CharacterCopierProfile) => {
    setActiveProfile(p);
    setCharacterId(p.character_id);
    setName(p.name);
    setEntityKind(p.entity_kind || 'unspecified being');
    setMorphology(p.morphology || '');
    setSurfaceDescription(p.surface_description || '');
    setPartsText((p.appendages_or_parts || []).join('\n'));
    setSensoryFeaturesText((p.sensory_features || []).join('\n'));
    setLocomotion(p.locomotion || '');
    setFaceCheckApplicable(p.face_check_applicable === true);
    setPromptIdentityCore(p.prompt_identity_core);
    setInvariants(p.identity_invariants || []);
    setVariations(p.allowed_variations || []);
    setForbiddenDrift(p.forbidden_drift || []);
    setUncertainTraits(p.uncertain_traits || []);
    setReferences(p.references || []);
    setSheetPlan(null);
  };

  const createNewProfile = () => {
    const freshId = `char_${Date.now().toString(36)}`;
    const fresh: CharacterCopierProfile = {
      profile_id: freshId,
      project_id: currentProject,
      character_id: freshId,
      name: 'New Character',
      entity_kind: 'unspecified being',
      version: 1,
      status: 'draft',
      references: [],
      identity_invariants: [],
      allowed_variations: [],
      forbidden_drift: [],
      uncertain_traits: [],
      prompt_identity_core: '',
    };
    setActiveProfile(fresh);
    setCharacterId(fresh.character_id);
    setName(fresh.name);
    setEntityKind(fresh.entity_kind || 'unspecified being');
    setMorphology('');
    setSurfaceDescription('');
    setPartsText('');
    setSensoryFeaturesText('');
    setLocomotion('');
    setFaceCheckApplicable(false);
    setPromptIdentityCore('');
    setInvariants([]);
    setVariations([]);
    setForbiddenDrift([]);
    setUncertainTraits([]);
    setReferences([]);
    setSheetPlan(null);
  };

  // Add reference images with automatic profile persistence
  const addReferenceAssets = async (assetIds: string[]) => {
    const uniqueIds = assetIds.filter((id) => !references.some((r) => r.asset_id === id));
    if (uniqueIds.length === 0) {
      if (assetIds.length === 1) {
        showToast({ type: 'info', title: 'Already added', message: 'Asset is already in character references.' });
      }
      return;
    }

    const newBindings: ReferenceBinding[] = uniqueIds.map((id, index) => {
      // Intelligently assign role if multiple angles are uploaded
      const viewRole: CharacterViewRole = 'other';

      return {
        asset_id: id,
        role: 'character_reference' as SemanticReferenceRole,
        view_role: viewRole,
        character_id: characterId,
        weight: 1.0,
        notes: 'Character identity and appearance reference',
      };
    });

    const nextRefs = [...references, ...newBindings];
    setReferences(nextRefs);
    setAssetModalOpen(false);

    // Auto-persist to active profile immediately so references are never lost
    if (activeProfile) {
      try {
        const payload: CharacterCopierProfile = {
          ...activeProfile,
          character_id: characterId || activeProfile.character_id,
          name: name || activeProfile.name || 'Unnamed Character',
          entity_kind: entityKind,
          morphology,
          surface_description: surfaceDescription,
          appendages_or_parts: partsText.split('\n').map((value) => value.trim()).filter(Boolean),
          sensory_features: sensoryFeaturesText.split('\n').map((value) => value.trim()).filter(Boolean),
          locomotion,
          face_check_applicable: faceCheckApplicable,
          prompt_identity_core: promptIdentityCore,
          identity_invariants: invariants,
          allowed_variations: variations,
          forbidden_drift: forbiddenDrift,
          uncertain_traits: uncertainTraits,
          references: nextRefs,
        };
        const saved = await apiClient.saveCharacterProfile(currentProject, payload);
        setActiveProfile(saved);
        setProfiles((prev) => prev.map((p) => (p.profile_id === saved.profile_id ? saved : p)));
      } catch (err: any) {
        console.warn('Auto-save character profile reference failed:', err);
      }
    }
  };

  const addReferenceAsset = async (assetId: string) => {
    await addReferenceAssets([assetId]);
  };

  const removeReference = async (assetId: string) => {
    const nextRefs = references.filter((r) => r.asset_id !== assetId);
    setReferences(nextRefs);
    if (activeProfile) {
      try {
        const payload: CharacterCopierProfile = {
          ...activeProfile,
          references: nextRefs,
        };
        const saved = await apiClient.saveCharacterProfile(currentProject, payload);
        setActiveProfile(saved);
        setProfiles((prev) => prev.map((p) => (p.profile_id === saved.profile_id ? saved : p)));
      } catch (err: any) {
        console.warn('Auto-save character profile reference removal failed:', err);
      }
    }
  };

  const updateReferenceViewRole = (assetId: string, view_role: CharacterViewRole) => {
    const nextRefs = references.map((r) => (r.asset_id === assetId ? { ...r, view_role } : r));
    setReferences(nextRefs);
    if (activeProfile) {
      apiClient.saveCharacterProfile(currentProject, { ...activeProfile, references: nextRefs }).catch(console.warn);
    }
  };

  const updateReferenceWeight = (assetId: string, weight: number) => {
    const nextRefs = references.map((r) => (r.asset_id === assetId ? { ...r, weight } : r));
    setReferences(nextRefs);
    if (activeProfile) {
      apiClient.saveCharacterProfile(currentProject, { ...activeProfile, references: nextRefs }).catch(console.warn);
    }
  };

  // Unified multi-file processor for both input change and drag & drop
  const processUploadFiles = async (files: FileList | File[]) => {
    const fileList = Array.from(files);
    if (fileList.length === 0) return;

    try {
      setLoading(true);
      const uploadedIds: string[] = [];

      for (const file of fileList) {
        try {
          const asset = await apiClient.uploadImageAsset(file, currentProject, 'image_reference');
          if (asset && asset.asset_id) {
            uploadedIds.push(asset.asset_id);
          }
        } catch (itemErr: any) {
          showToast({ type: 'error', title: `Failed uploading ${file.name}`, message: itemErr.message });
        }
      }

      if (uploadedIds.length > 0) {
        await addReferenceAssets(uploadedIds);
        const updatedAssets = await apiClient.listAssets({ project_id: currentProject }).catch(() => []);
        setAvailableAssets(updatedAssets);
        showToast({
          type: 'success',
          title: 'Reference(s) Uploaded',
          message: `Successfully bound ${uploadedIds.length} character reference image(s).`,
        });
      }
    } catch (err: any) {
      showToast({ type: 'error', title: 'Upload failed', message: err.message });
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleUploadReference = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) await processUploadFiles(files);
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) await processUploadFiles(files);
  };

  // Analyze Character
  const handleAnalyzeCharacter = async () => {
    if (references.length === 0) {
      showToast({ type: 'error', title: 'No references', message: 'Please attach at least one character reference image to analyze.' });
      return;
    }
    try {
      setAnalyzing(true);
      const targetName = name.trim() || 'New Character';
      const targetCharId = characterId.trim() || `char_${Date.now().toString(36)}`;
      const result = await apiClient.analyzeCharacterReferences(currentProject, {
        character_id: targetCharId,
        name: targetName,
        references,
        known_canon_facts: (activeProfile?.status === 'approved' && invariants.length > 0) ? invariants : [],
      });

      const nextInvariants = result.identity_invariants && result.identity_invariants.length > 0
        ? result.identity_invariants
        : [];
      const nextVariations = result.allowed_variations && result.allowed_variations.length > 0
        ? result.allowed_variations
        : [];
      const nextForbidden = result.forbidden_drift && result.forbidden_drift.length > 0
        ? result.forbidden_drift
        : [];
      const nextPromptCore = result.prompt_identity_core || '';

      setInvariants(nextInvariants);
      setVariations(nextVariations);
      setForbiddenDrift(nextForbidden);
      setPromptIdentityCore(nextPromptCore);

      const resolvedName = (result.name && result.name !== 'Extracted Character') ? result.name : (name || targetName);
      if (!name || name === 'New Character') {
        setName(resolvedName);
      }
      if (!characterId) {
        setCharacterId(targetCharId);
      }

      // Auto-persist analysis results immediately to active character profile
      if (activeProfile) {
        const payload: CharacterCopierProfile = {
          ...activeProfile,
          character_id: characterId || targetCharId,
          name: resolvedName,
          prompt_identity_core: nextPromptCore,
          identity_invariants: nextInvariants,
          allowed_variations: nextVariations,
          forbidden_drift: nextForbidden,
          references,
        };
        apiClient.saveCharacterProfile(currentProject, payload).then((saved) => {
          setActiveProfile(saved);
          setProfiles((prev) => prev.map((p) => (p.profile_id === saved.profile_id ? saved : p)));
        }).catch((err) => console.warn('Auto-save character analysis failed:', err));
      }

      showToast({
        type: 'success',
        title: 'Analysis Complete',
        message: `Extracted ${nextInvariants.length} invariants & ${nextVariations.length} variation dimensions from visual evidence.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Analysis failed', message: err.message });
    } finally {
      setAnalyzing(false);
    }
  };

  // Save Character Profile
  const handleSaveProfile = async (approved = false) => {
    if (!activeProfile) return;
    const cleanName = name.trim();
    if (!cleanName || cleanName === 'New Character') {
      showToast({ type: 'error', title: 'Add a character name', message: 'Enter a display name before adding this character.' });
      return;
    }
    const isNewToLibrary = !profiles.some((profile) => profile.profile_id === activeProfile.profile_id);
    try {
      setLoading(true);
      const payload: CharacterCopierProfile = {
        ...activeProfile,
        character_id: characterId,
        name: cleanName,
        entity_kind: entityKind,
        morphology,
        surface_description: surfaceDescription,
        appendages_or_parts: partsText.split('\n').map((value) => value.trim()).filter(Boolean),
        sensory_features: sensoryFeaturesText.split('\n').map((value) => value.trim()).filter(Boolean),
        locomotion,
        face_check_applicable: faceCheckApplicable,
        prompt_identity_core: promptIdentityCore,
        identity_invariants: invariants,
        allowed_variations: variations,
        forbidden_drift: forbiddenDrift,
        uncertain_traits: uncertainTraits,
        references,
        status: approved ? 'approved' : (isNewToLibrary ? 'draft' : 'ready'),
        approved_by_user: approved,
      };

      const saved = await apiClient.saveCharacterProfile(currentProject, payload);
      if (approved) {
        const formallyApproved = await apiClient.approveCharacterProfile(currentProject, saved.profile_id);
        setActiveProfile(formallyApproved);
      } else {
        setActiveProfile(saved);
      }

      await loadData();
      showToast({
        type: 'success',
        title: approved ? 'Profile Approved' : (isNewToLibrary ? 'Character Draft Saved' : 'Character Saved'),
        message: approved
          ? `Profile version ${saved.version} approved. This does not change Canon.`
          : isNewToLibrary
            ? `${cleanName} is saved as a Character Copier draft. Use Add to Story Bible to place it in the Characters roster.`
            : `Version ${saved.version} saved successfully.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to save profile', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleAddToStoryBible = async () => {
    if (!activeProfile) return;
    const cleanName = name.trim();
    const stableId = characterId.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_').replace(/^_+|_+$/g, '');
    if (!cleanName || cleanName === 'New Character') {
      showToast({ type: 'error', title: 'Add a character name', message: 'Enter a display name before adding this character.' });
      return;
    }
    if (!stableId) {
      showToast({ type: 'error', title: 'Character ID required', message: 'Add a stable character ID before adding this character to the Story Bible.' });
      return;
    }
    if (canonCharacterIds.includes(stableId)) {
      showToast({ type: 'error', title: 'Already in Story Bible', message: `The Characters roster already contains “${stableId}”.` });
      return;
    }

    let savedProfile: CharacterCopierProfile | null = null;
    try {
      setLoading(true);
      const profilePayload: CharacterCopierProfile = {
        ...activeProfile,
        character_id: stableId,
        name: cleanName,
        entity_kind: entityKind,
        morphology,
        surface_description: surfaceDescription,
        appendages_or_parts: partsText.split('\n').map((value) => value.trim()).filter(Boolean),
        sensory_features: sensoryFeaturesText.split('\n').map((value) => value.trim()).filter(Boolean),
        locomotion,
        face_check_applicable: faceCheckApplicable,
        prompt_identity_core: promptIdentityCore,
        identity_invariants: invariants,
        allowed_variations: variations,
        forbidden_drift: forbiddenDrift,
        uncertain_traits: uncertainTraits,
        references,
        status: 'draft',
        approved_by_user: false,
      };
      savedProfile = await apiClient.saveCharacterProfile(currentProject, profilePayload);
      setCharacterId(stableId);
      setActiveProfile(savedProfile);
      setProfiles((prev) => prev.some((profile) => profile.profile_id === savedProfile!.profile_id)
        ? prev.map((profile) => profile.profile_id === savedProfile!.profile_id ? savedProfile! : profile)
        : [savedProfile!, ...prev]);

      const referenceAssets = await Promise.all(references.map(async (reference) => {
        const asset = await apiClient.getAsset(reference.asset_id);
        if (asset.project_id !== currentProject) {
          throw new Error(`Reference asset ${reference.asset_id} belongs to another project.`);
        }
        if (!asset.managed_path || !asset.content_sha256 || !asset.mime_type) {
          throw new Error(`Reference asset ${reference.asset_id} is missing the metadata required for a Canon link.`);
        }
        return {
          asset_id: asset.asset_id,
          path: String(asset.managed_path).replace(/\\/g, '/'),
          asset_type: 'character_sheet',
          expected_hash: asset.content_sha256,
          mime_type: asset.mime_type,
          file_size_bytes: asset.byte_size,
          provenance: { project_id: currentProject, source_profile_id: savedProfile!.profile_id, source_profile_version: savedProfile!.version },
        };
      }));

      const formDescription = [entityKind, morphology, surfaceDescription, promptIdentityCore].filter(Boolean).join('. ') || `${cleanName} character profile`;
      const attributeFacts = invariants.length > 0
        ? invariants
        : [formDescription];
      const proposal = await apiClient.proposeMutation(currentProject, {
        target_type: 'character',
        target_id: stableId,
        change_description: `Add ${cleanName} from Character Copier to Story Bible Characters.`,
        proposed_changes: {
          action: 'add',
          name: cleanName,
          entity_kind: entityKind,
          morphology,
          surface_description: surfaceDescription,
          description: formDescription,
          visual_invariants: invariants,
          restrictions: forbiddenDrift,
          clothing_attributes: activeProfile.base_outfit?.garments || [],
          tolerances: { face_check_applicable: faceCheckApplicable },
          attributes: attributeFacts.map((fact, index) => ({ id: `${stableId}_identity_${index + 1}`, text: fact, required: true })),
          reference_assets: referenceAssets,
          approval_status: 'approved',
        },
      });
      const applied = await apiClient.applyMutation(currentProject, { proposal_id: proposal.proposal_id, caller_authorized: true });
      const nextCanonIds = Object.keys(applied.bible?.characters || {});
      setCanonCharacterIds(nextCanonIds.length > 0 ? nextCanonIds : [...canonCharacterIds, stableId]);

      let finalProfile = savedProfile;
      let profileApprovalFailed = false;
      try {
        finalProfile = await apiClient.approveCharacterProfile(currentProject, savedProfile.profile_id);
        setActiveProfile(finalProfile);
        setProfiles((prev) => prev.map((profile) => profile.profile_id === finalProfile!.profile_id ? finalProfile! : profile));
      } catch {
        // Canon is already committed; keep the saved profile visible and report the sync issue in the success message.
        profileApprovalFailed = true;
      }

      showToast({
        type: 'success',
        title: 'Added to Story Bible Characters',
        message: profileApprovalFailed
          ? `${cleanName} is in the Story Bible Characters roster (Canon v${applied.bible_version}), but its Character Copier approval did not sync. The profile may still show as a draft.`
          : `${cleanName} is now visible in the Story Bible Characters roster (Canon v${applied.bible_version}).`,
      });
    } catch (err: any) {
      const detail = err?.payload?.message || err?.message || 'The character could not be added.';
      showToast({
        type: 'error',
        title: savedProfile ? 'Draft Saved, Story Bible Add Failed' : 'Could Not Add Character',
        message: savedProfile ? `${detail} The profile draft is saved; try Add to Story Bible again.` : detail,
      });
    } finally {
      setLoading(false);
    }
  };

  // Generate Character Sheet Plan
  const handleGenerateSheetPlan = async () => {
    if (!activeProfile) return;
    try {
      setGeneratingSheet(true);
      await handleSaveProfile(false);
      const plan = await apiClient.generateCharacterSheetPlan(currentProject, activeProfile.profile_id);
      setSheetPlan(plan);
      showToast({ type: 'success', title: 'Turnaround Plan Created', message: `${plan.views.length} turnaround view specs generated.` });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to create sheet plan', message: err.message });
    } finally {
      setGeneratingSheet(false);
    }
  };

  // Propose to Canon
  const handleProposeToCanon = async () => {
    if (!activeProfile) return;
    try {
      setProposingCanon(true);
      await handleSaveProfile(false);
      const res = await apiClient.proposeCharacterInvariantsToCanon(
        currentProject,
        activeProfile.profile_id,
        { change_description: canonReason.trim() || undefined }
      );
      setCanonModalOpen(false);
      setCanonReason('');
      showToast({
        type: 'success',
        title: 'Canon Proposal Submitted',
        message: res.message || 'Invariants submitted to Story Bible queue awaiting user review.',
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Canon proposal failed', message: err.message });
    } finally {
      setProposingCanon(false);
    }
  };

  // Render Turnaround Sheet
  const handleRenderTurnaroundSheet = async () => {
    if (!activeProfile) return;
    try {
      setRenderingSheet(true);
      await handleSaveProfile(false);
      const result = await apiClient.generateCharacterTurnaroundSheet(currentProject, activeProfile.profile_id, {
        style_profile_id: selectedStyleId || undefined,
        max_attempts: 2,
      });
      setRenderedSheet(result);
      showToast({
        type: 'success',
        title: 'Turnaround Views Rendered',
        message: `Generated ${result.total_views} view panels with automated QA.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Turnaround rendering failed', message: err.message });
    } finally {
      setRenderingSheet(false);
    }
  };

  // Combined Studio: Test Generate Character in Style
  const handleCharacterTestGenerate = async () => {
    if (!activeProfile) return;
    try {
      setGeneratingTest(true);
      setTestResult(null);
      await handleSaveProfile(false);
      const genResult = await apiClient.generateWithCreativeProfiles(currentProject, {
        scene_action: `${name || 'Character'}: ${testActionPrompt}`,
        shot_type: testShotType,
        character_profile_ids: [activeProfile.profile_id],
        style_profile_id: selectedStyleId || undefined,
        panel_id: 'char_test_01',
        scene_id: 'character_studio',
        max_attempts: 2,
      });
      setTestResult(genResult);
      const score = genResult.qa_result?.overall_score ?? genResult.qa_result?.identity_score;
      showToast({
        type: genResult.is_simulated ? 'info' : 'success',
        title: genResult.is_simulated ? 'Simulated Draft Generated' : 'Generation Complete',
        message: score == null ? 'Output generated; character identity and pose remain unverified.' : `Measured QA score: ${Math.round(score)}%.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Generation failed', message: err.message });
    } finally {
      setGeneratingTest(false);
    }
  };

  // List manipulation helpers
  const addItem = (list: string[], setList: (l: string[]) => void, item: string, setItem: (s: string) => void) => {
    if (!item.trim()) return;
    if (!list.includes(item.trim())) {
      setList([...list, item.trim()]);
    }
    setItem('');
  };

  const removeItem = (list: string[], setList: (l: string[]) => void, item: string) => {
    setList(list.filter((x) => x !== item));
  };

  const activeCharacterIsCanonical = !!characterId && canonCharacterIds.includes(characterId.trim().toLowerCase());

  return (
    <div className="space-y-6">
      {/* Top Header & Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <TabCharacterIcon tab="character-copier" size={38} />
            <h1 className="text-xl font-bold text-white tracking-tight">Characters</h1>
            {activeProfile && (
              <Badge
                variant={activeProfile.approved_by_user ? 'success' : 'neutral'}
                size="sm"
              >
                {activeProfile.approved_by_user ? 'Ready to use' : activeCharacterIsCanonical ? 'In Characters' : 'New character'}
              </Badge>
            )}
          </div>
          <p className="text-xs text-ink-400 mt-1">
            Describe a character, add pictures if you have them, then add it to your story.
          </p>
        </div>

        {/* Profile Switcher & Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={activeProfile?.profile_id || ''}
            onChange={(e) => {
              const found = profiles.find((p) => p.profile_id === e.target.value);
              if (found) selectProfile(found);
            }}
            className="bg-ink-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
          >
            {profiles.map((p) => (
              <option key={p.profile_id} value={p.profile_id}>
                {p.name}
              </option>
            ))}
          </select>

          <button
            onClick={createNewProfile}
            className="px-3 py-1.5 bg-ink-800 hover:bg-ink-700 text-white rounded-lg text-xs font-medium flex items-center gap-1 transition-colors border border-white/10"
          >
            <Plus className="w-3.5 h-3.5" />
            New
          </button>

          <button
            onClick={() => activeCharacterIsCanonical ? handleSaveProfile(false) : handleAddToStoryBible()}
            disabled={loading}
            className="px-3 py-1.5 bg-white text-black hover:bg-ink-200 disabled:opacity-50 rounded-lg text-xs font-semibold transition-colors"
          >
            {loading ? 'Saving…' : activeCharacterIsCanonical ? 'Save Changes' : 'Add to Story Bible'}
          </button>

          {activeCharacterIsCanonical && <details className="text-xs">
            <summary className="cursor-pointer text-ink-400 px-2 py-1">More</summary>
            <div className="mt-2 flex flex-col gap-2">
              <button
                onClick={() => setCanonModalOpen(true)}
                className="px-3 py-1.5 bg-ink-800 hover:bg-ink-700 text-white rounded-lg border border-white/10"
              >
                Edit Canon details
              </button>
              <button
                onClick={() => handleSaveProfile(true)}
                disabled={loading}
                title="Approves the reusable profile; it does not change story membership."
                className="px-3 py-1.5 bg-ink-800 hover:bg-ink-700 text-white disabled:opacity-50 rounded-lg border border-white/10"
              >
                Approve profile
              </button>
            </div>
          </details>}
        </div>
      </div>

      {/* Honest Capability & Identity Notice */}
      <div className="p-3 rounded-xl bg-ink-900/80 border border-white/10 text-xs text-ink-300 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-ink-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <div className="font-semibold text-white">
            About character pictures
          </div>
          <p className="text-ink-400 leading-relaxed">
            Pictures help guide generated results, but the character may still look different. Your character can be a person, creature, object, simple shape, or anything else.
          </p>
        </div>
      </div>

      {/* Main Grid: References Left, Invariants/Variations Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Multi-view References (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card
            title={
              <div className="flex items-center justify-between w-full">
                <span>Pictures ({references.length})</span>
                <span className="text-xs text-ink-400 font-normal">Role: character_reference</span>
              </div>
            }
            subtitle="Attach images showing the forms and features you want to preserve"
          >
            <div className="space-y-4">
              {/* Add & Upload Toolbar */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setAssetModalOpen(true)}
                  className="flex-1 py-2 px-3 bg-ink-850 hover:bg-ink-800 text-white rounded-xl text-xs font-medium border border-white/10 flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Select from Library
                </button>

                <button
                  type="button"
                  onClick={() => {
                    if (fileInputRef.current) {
                      fileInputRef.current.value = '';
                      fileInputRef.current.click();
                    }
                  }}
                  className="flex-1 py-2 px-3 bg-ink-850 hover:bg-ink-800 text-white rounded-xl text-xs font-medium border border-white/10 flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
                >
                  <Upload className="w-3.5 h-3.5 pointer-events-none" />
                  Upload Image
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/png,image/jpeg,image/webp,image/*"
                  onChange={handleUploadReference}
                  className="hidden"
                  style={{ display: 'none' }}
                />
              </div>

              {/* References List & Interactive Dropzone */}
              {references.length === 0 ? (
                <div
                  onClick={() => {
                    if (fileInputRef.current) {
                      fileInputRef.current.value = '';
                      fileInputRef.current.click();
                    }
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  className={`p-8 rounded-xl border-2 border-dashed transition-colors motion-interactive text-center space-y-3 cursor-pointer group ${
                    isDragging
                      ? 'border-indigo-500 bg-indigo-500/10'
                      : 'border-white/10 hover:border-white/30 hover:bg-white/[0.02]'
                  }`}
                >
                  <div className="w-12 h-12 rounded-full bg-ink-900 border border-white/10 flex items-center justify-center mx-auto group-hover:scale-105 transition-transform">
                    <Upload className="w-5 h-5 text-ink-300 group-hover:text-white" />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-white">Click or drag & drop reference image here</p>
                    <p className="text-[11px] text-ink-400 mt-0.5">
                      Add any useful views or reference images for this being
                    </p>
                  </div>
                  <div className="pt-1 flex items-center justify-center gap-2">
                    <span className="px-2.5 py-1 bg-ink-850 text-ink-300 text-[10px] rounded border border-white/10">
                      Or Select from Library above
                    </span>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {references.map((ref) => (
                    <div
                      key={ref.asset_id}
                      className="p-3 rounded-xl bg-ink-900 border border-white/5 flex gap-3 items-center"
                    >
                      {/* Image Thumbnail */}
                      <div className="w-16 h-16 rounded-lg bg-black border border-white/10 overflow-hidden shrink-0 flex items-center justify-center">
                        <img
                          src={apiClient.getAssetFileUrl(ref.asset_id)}
                          alt={ref.asset_id}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      </div>

                      {/* Info & View Angle Selector */}
                      <div className="flex-1 min-w-0 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono text-ink-300 truncate">
                            {ref.asset_id}
                          </span>
                          <button
                            onClick={() => removeReference(ref.asset_id)}
                            className="text-ink-500 hover:text-rose-400 p-1"
                            title="Remove reference"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        <div className="flex items-center gap-2">
                          <label className="text-[10px] text-ink-400">View Role:</label>
                          <select
                            value={ref.view_role || 'other'}
                            onChange={(e) =>
                              updateReferenceViewRole(ref.asset_id, e.target.value as CharacterViewRole)
                            }
                            className="bg-ink-950 border border-white/10 rounded px-2 py-0.5 text-[10px] text-white focus:outline-none"
                          >
                            <option value="front">Front</option>
                            <option value="three_quarter">Angled</option>
                            <option value="side">Side</option>
                            <option value="full_body">Whole character</option>
                            <option value="full_form">Whole shape</option>
                            <option value="expression">Expression</option>
                            <option value="outfit">Clothes</option>
                            <option value="action_pose">Action pose</option>
                          </select>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-ink-400">Weight:</span>
                          <input
                            type="range"
                            min="0.2"
                            max="1.8"
                            step="0.1"
                            value={ref.weight}
                            onChange={(e) =>
                              updateReferenceWeight(ref.asset_id, parseFloat(e.target.value))
                            }
                            className="w-20 accent-white"
                          />
                          <span className="text-[10px] font-mono text-white">
                            {ref.weight.toFixed(1)}x
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Quick Add Strip when references exist */}
                  <div
                    onClick={() => {
                      if (fileInputRef.current) {
                        fileInputRef.current.value = '';
                        fileInputRef.current.click();
                      }
                    }}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragging(true);
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                    className={`py-2.5 px-3 rounded-xl border border-dashed transition-colors motion-interactive text-center cursor-pointer flex items-center justify-center gap-2 group ${
                      isDragging
                        ? 'border-indigo-500 bg-indigo-500/10'
                        : 'border-white/10 hover:border-white/30 hover:bg-white/[0.02]'
                    }`}
                  >
                    <Plus className="w-3.5 h-3.5 text-ink-400 group-hover:text-white" />
                    <span className="text-xs text-ink-400 group-hover:text-ink-200">
                      Add more pictures (optional)
                    </span>
                  </div>
                </div>
              )}

              <details className="rounded-lg border border-white/10 p-3">
                <summary className="cursor-pointer text-xs text-ink-300">Optional: describe from pictures or make a reference sheet</summary>
              <div className="space-y-2">
                <button
                  onClick={handleAnalyzeCharacter}
                  disabled={analyzing || references.length === 0}
                  className="w-full py-2.5 px-4 bg-white text-black hover:bg-ink-200 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  {analyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Looking at the pictures…
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Describe this character from pictures
                    </>
                  )}
                </button>

                <button
                  onClick={handleGenerateSheetPlan}
                  disabled={generatingSheet || !activeProfile}
                  className="w-full py-2 px-4 bg-ink-850 hover:bg-ink-800 text-white rounded-xl text-xs font-medium border border-white/10 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  {generatingSheet ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Preparing reference views…
                    </>
                  ) : (
                    <>
                      <Layers className="w-3.5 h-3.5" />
                      Plan reference views
                    </>
                  )}
                </button>
              </div>
              </details>
            </div>
          </Card>

          {/* Turnaround Sheet Plan Preview & Execution */}
          {sheetPlan && (
            <Card
              title={`Turnaround Sheet Plan: ${sheetPlan.character_name}`}
              subtitle="Planned views for a character reference sheet"
            >
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  {sheetPlan.views.map((v: any, idx: number) => (
                    <div
                      key={v.view_type || idx}
                      className="p-2.5 rounded-lg bg-ink-900 border border-white/5 space-y-1 text-xs"
                    >
                      <div className="font-bold text-white uppercase text-[10px] tracking-wider">
                        {v.view_type?.replace('_', ' ')}
                      </div>
                      <div className="text-[11px] text-ink-300 font-medium">{v.camera_angle || 'Eye-level'}</div>
                      <p className="text-[10px] text-ink-400 line-clamp-2">{v.prompt || v.pose_description}</p>
                    </div>
                  ))}
                </div>

                <div className="pt-1">
                  <button
                    onClick={handleRenderTurnaroundSheet}
                    disabled={renderingSheet || !activeProfile}
                    className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                  >
                    {renderingSheet ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Rendering All Turnaround Views...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Render All Turnaround Views (E1)
                      </>
                    )}
                  </button>
                </div>

                {/* Rendered Turnaround Results */}
                {renderedSheet && (
                  <div className="space-y-3 pt-2 border-t border-white/10">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white">Rendered Turnaround Views</span>
                      <Badge variant={renderedSheet.all_passed_qa ? 'success' : 'warning'} size="sm">
                        {renderedSheet.all_passed_qa ? 'All Views Passed QA' : 'Attention Needed'}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      {renderedSheet.views.map((view: any, idx: number) => (
                        <div
                          key={idx}
                          className="p-2.5 rounded-xl bg-ink-950 border border-white/10 space-y-2 text-xs"
                        >
                          <div className="aspect-square rounded-lg bg-black overflow-hidden flex items-center justify-center border border-white/5">
                            {view.asset_id ? (
                              <img
                                src={apiClient.getAssetFileUrl(view.asset_id)}
                                alt={view.label}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <span className="text-ink-500 text-[10px]">Render Pending</span>
                            )}
                          </div>
                          <div>
                            <div className="font-semibold text-white text-[11px] truncate">{view.label}</div>
                            <div className="text-[10px] text-ink-400">QA: {view.qa_score == null ? 'Not verified' : `${Math.round(view.qa_score)}%`}</div>
                          </div>
                          {view.asset_id && (
                            <button
                              onClick={() => addReferenceAsset(view.asset_id)}
                              className="w-full py-1 px-2 bg-ink-850 hover:bg-ink-800 text-white rounded text-[10px] font-medium border border-white/10 flex items-center justify-center gap-1"
                            >
                              <Plus className="w-3 h-3" />
                              Add as Reference
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Invariants vs Variations & Core Prompt (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card
            title="Character details"
            subtitle="Describe the parts that matter. You can leave anything that does not apply blank."
          >
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-ink-300 mb-1">Character name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-ink-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                  placeholder="What should this character be called?"
                />
                <p className="text-[10px] text-ink-500 mt-1">We create the technical ID automatically.</p>
              </div>

              <div className="rounded-xl bg-ink-900/60 border border-white/10 p-3 space-y-3">
                <div>
                  <div className="text-xs font-semibold text-white">What does this character look like?</div>
                  <p className="text-[11px] text-ink-400 mt-1">Any kind of being or shape is welcome. Fill in only what applies.</p>
                </div>
                <label className="block text-xs text-ink-300">Kind of character (optional)
                  <input value={entityKind} onChange={(e) => setEntityKind(e.target.value)} placeholder="e.g. smiling circle creature, masked wanderer, headless stone guardian" className="mt-1 w-full bg-ink-950 border border-white/10 rounded-lg px-3 py-2 text-xs text-white" />
                </label>
                <label className="block text-xs text-ink-300">Shape and form (optional)
                  <textarea rows={2} value={morphology} onChange={(e) => setMorphology(e.target.value)} placeholder="Shape, proportions, visible parts, or explicitly no body/head/limbs" className="mt-1 w-full bg-ink-950 border border-white/10 rounded-lg p-3 text-xs text-white" />
                </label>
                <label className="block text-xs text-ink-300">Color and surface (optional)
                  <textarea rows={2} value={surfaceDescription} onChange={(e) => setSurfaceDescription(e.target.value)} placeholder="e.g. flat yellow circle with a drawn smile; glossy porcelain; mist-like edges" className="mt-1 w-full bg-ink-950 border border-white/10 rounded-lg p-3 text-xs text-white" />
                </label>
                <details className="pt-1">
                  <summary className="cursor-pointer text-xs text-ink-300">More details (optional)</summary>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <label className="block text-xs text-ink-300">Parts / appendages (one per line)
                    <textarea rows={3} value={partsText} onChange={(e) => setPartsText(e.target.value)} placeholder="Tentacles\nFloating hands\nNo appendages" className="mt-1 w-full bg-ink-950 border border-white/10 rounded-lg p-3 text-xs text-white" />
                  </label>
                  <label className="block text-xs text-ink-300">Sensors / face-like features (one per line)
                    <textarea rows={3} value={sensoryFeaturesText} onChange={(e) => setSensoryFeaturesText(e.target.value)} placeholder="Two glowing eyes\nA painted smile\nNo face or sensory features" className="mt-1 w-full bg-ink-950 border border-white/10 rounded-lg p-3 text-xs text-white" />
                  </label>
                </div>
                <label className="block text-xs text-ink-300">How it moves, if applicable
                  <input value={locomotion} onChange={(e) => setLocomotion(e.target.value)} placeholder="Rolls, floats, crawls, walks, or does not move" className="mt-1 w-full bg-ink-950 border border-white/10 rounded-lg px-3 py-2 text-xs text-white" />
                </label>
                <label className="flex items-center gap-2 text-xs text-ink-300">
                  <input type="checkbox" checked={faceCheckApplicable} onChange={(e) => setFaceCheckApplicable(e.target.checked)} className="accent-white" />
                  This character has a face
                </label>
                </details>
              </div>

              {/* Core Likeness Prompt */}
              <details className="rounded-lg border border-white/10 p-3">
                <summary className="cursor-pointer text-xs text-ink-300">Optional: fine-tune what stays the same</summary>
              <div className="space-y-4 pt-3">
              <div>
                <label className="block text-xs font-medium text-ink-300 mb-1">
                  Anything else to remember (optional)
                </label>
                <textarea
                  rows={2}
                  value={promptIdentityCore}
                  onChange={(e) => setPromptIdentityCore(e.target.value)}
                  className="w-full bg-ink-900 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/30 font-mono leading-relaxed"
                  placeholder="Add any extra detail you want the image model to remember"
                />
              </div>

              {/* SECTION 1: MANDATORY INVARIANTS (Locked) */}
              <div className="p-3 rounded-xl bg-ink-900/60 border border-white/10 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Keep these details the same
                    </span>
                  </div>
                  <span className="text-[10px] text-ink-400">Optional</span>
                </div>
                <p className="text-[11px] text-ink-400">
                  Add details that help keep this character recognizable, like a smiley face or a striped tail.
                </p>

                <div className="space-y-1.5">
                  {invariants.map((inv) => (
                    <div
                      key={inv}
                      className="p-2 rounded-lg bg-ink-950 border border-white/5 text-xs text-ink-200 flex items-center justify-between gap-2"
                    >
                      <span className="flex-1 font-medium">{inv}</span>
                      <button
                        onClick={() => removeItem(invariants, setInvariants, inv)}
                        className="text-ink-500 hover:text-rose-400"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="text"
                    value={newInvariant}
                    onChange={(e) => setNewInvariant(e.target.value)}
                    onKeyDown={(e) =>
                      e.key === 'Enter' &&
                      addItem(invariants, setInvariants, newInvariant, setNewInvariant)
                    }
                    placeholder="For example: always has three blue spots"
                    className="flex-1 bg-ink-950 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                  <button
                    onClick={() =>
                      addItem(invariants, setInvariants, newInvariant, setNewInvariant)
                    }
                    className="px-3 py-1.5 bg-ink-800 hover:bg-ink-700 text-white rounded-lg text-xs font-medium border border-white/10"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* SECTION 2: ALLOWED VARIATIONS (Encouraged) */}
              <div className="p-3 rounded-xl bg-ink-900/60 border border-white/10 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-ink-300" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      What can change in a scene
                    </span>
                  </div>
                  <span className="text-[10px] text-ink-400">Optional</span>
                </div>
                <p className="text-[11px] text-ink-400">
                  Add things that may change, like pose, expression, or clothes.
                </p>

                <div className="space-y-1.5">
                  {variations.map((v) => (
                    <div
                      key={v}
                      className="p-2 rounded-lg bg-ink-950 border border-white/5 text-xs text-ink-200 flex items-center justify-between gap-2"
                    >
                      <span className="flex-1">{v}</span>
                      <button
                        onClick={() => removeItem(variations, setVariations, v)}
                        className="text-ink-500 hover:text-rose-400"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="text"
                    value={newVariation}
                    onChange={(e) => setNewVariation(e.target.value)}
                    onKeyDown={(e) =>
                      e.key === 'Enter' &&
                      addItem(variations, setVariations, newVariation, setNewVariation)
                    }
                    placeholder="For example: can wear different hats"
                    className="flex-1 bg-ink-950 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                  <button
                    onClick={() =>
                      addItem(variations, setVariations, newVariation, setNewVariation)
                    }
                    className="px-3 py-1.5 bg-ink-800 hover:bg-ink-700 text-white rounded-lg text-xs font-medium border border-white/10"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* SECTION 3: FORBIDDEN DRIFT */}
              <div className="p-3 rounded-xl bg-ink-900/60 border border-white/10 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Things to avoid
                    </span>
                  </div>
                  <span className="text-[10px] text-ink-400">Optional</span>
                </div>

                <div className="space-y-1.5">
                  {forbiddenDrift.map((f) => (
                    <div
                      key={f}
                      className="p-2 rounded-lg bg-ink-950 border border-white/5 text-xs text-ink-200 flex items-center justify-between gap-2"
                    >
                      <span className="flex-1">{f}</span>
                      <button
                        onClick={() => removeItem(forbiddenDrift, setForbiddenDrift, f)}
                        className="text-ink-500 hover:text-rose-400"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="text"
                    value={newForbidden}
                    onChange={(e) => setNewForbidden(e.target.value)}
                    onKeyDown={(e) =>
                      e.key === 'Enter' &&
                      addItem(forbiddenDrift, setForbiddenDrift, newForbidden, setNewForbidden)
                    }
                    placeholder="For example: never add arms"
                    className="flex-1 bg-ink-950 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                  <button
                    onClick={() =>
                      addItem(forbiddenDrift, setForbiddenDrift, newForbidden, setNewForbidden)
                    }
                    className="px-3 py-1.5 bg-ink-800 hover:bg-ink-700 text-white rounded-lg text-xs font-medium border border-white/10"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>
              </details>
            </div>
          </Card>

          {/* Live Character Generation Studio Card */}
          <details className="rounded-xl border border-white/10 p-4">
            <summary className="cursor-pointer text-sm font-medium text-ink-200">Advanced: test a generated picture</summary>
            <div className="pt-4">
          <Card
            title="Generate a test picture"
            subtitle="Uses your selected character and the real image provider"
          >
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-ink-400 mb-1">Panel Scene Action Prompt</label>
                <input
                  type="text"
                  value={testActionPrompt}
                  onChange={(e) => setTestActionPrompt(e.target.value)}
                  placeholder="e.g. leaping across rooftops at dusk, drawing sword with intense focused gaze"
                  className="w-full bg-ink-900 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-ink-400 mb-1">Camera Framing & Angle</label>
                  <input
                    type="text"
                    value={testShotType}
                    onChange={(e) => setTestShotType(e.target.value)}
                    className="w-full bg-ink-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                </div>

                <div>
                  <label className="block text-xs text-ink-400 mb-1">Optional Visual Style Profile</label>
                  <select
                    value={selectedStyleId}
                    onChange={(e) => setSelectedStyleId(e.target.value)}
                    className="w-full bg-ink-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
                  >
                    <option value="">None (Raw Model Inking)</option>
                    {availableStyles.map((s) => (
                      <option key={s.profile_id} value={s.profile_id}>
                        {s.name} ({s.status})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end pt-1">
                <button
                  onClick={handleCharacterTestGenerate}
                  disabled={generatingTest || references.length === 0}
                  className="px-5 py-2.5 bg-white text-black hover:bg-ink-200 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {generatingTest ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Generating Character Panel...
                    </>
                  ) : (
                    <>
                      <Eye className="w-3.5 h-3.5" />
                      Generate Panel with Character
                    </>
                  )}
                </button>
              </div>

              {/* Generated Test Result */}
              {testResult && (
                <div className="mt-4 p-4 rounded-xl bg-ink-900 border border-white/10 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-white">Generated Panel Output</span>
                      <span className="text-[10px] font-mono text-ink-400">
                        {testResult.output_asset_id || testResult.asset_id}
                      </span>
                    </div>
                    <Badge
                      variant={testResult.qa_result?.status === 'pass' && testResult.qa_result?.passed === true ? 'success' : 'warning'}
                      size="sm"
                    >
                      {testResult.qa_result?.status === 'not_verified' ? 'Not Verified' : testResult.qa_result?.status === 'pass' && testResult.qa_result?.passed === true ? 'QA Passed' : 'QA Attention Needed'}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-lg bg-black border border-white/10 overflow-hidden aspect-square flex items-center justify-center">
                      <img
                        src={apiClient.getAssetFileUrl(testResult.output_asset_id || testResult.asset_id || '')}
                        alt="Test Character Output"
                        className="max-h-full max-w-full object-contain"
                      />
                    </div>

                    <div className="space-y-2 text-xs">
                      <div className="p-2.5 rounded-lg bg-ink-950 border border-white/5 space-y-1">
                        <div className="flex justify-between">
                          <span className="text-ink-400">Identity Retention:</span>
                          <span className="font-mono text-white font-bold">
                            {(testResult.qa_result?.identity_score ?? testResult.qa_result?.overall_score) == null ? 'Not verified' : `${Math.round(testResult.qa_result?.identity_score ?? testResult.qa_result?.overall_score!)}%`}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-ink-400">Dynamic Variation:</span>
                          <span className="font-mono text-white font-bold">
                            {(testResult.qa_result?.variation_score ?? testResult.qa_result?.dynamic_variation_score) == null ? 'Not verified' : `${Math.round(testResult.qa_result?.variation_score ?? testResult.qa_result?.dynamic_variation_score!)}%`}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-ink-400">Refinement Attempts:</span>
                          <span className="font-mono text-ink-300">
                            {testResult.attempts_performed ?? 'Unknown'}
                          </span>
                        </div>
                      </div>

                      {testResult.qa_result?.score_explanation && (
                        <p className="text-[11px] text-ink-400 italic">
                          {testResult.qa_result.score_explanation}
                        </p>
                      )}

                      {testResult.qa_result?.findings && testResult.qa_result.findings.length > 0 && (
                        <div className="space-y-1">
                          <div className="text-[10px] font-semibold text-ink-400 uppercase tracking-wider">
                            QA Verification Findings
                          </div>
                          {testResult.qa_result.findings.map((f, i) => (
                            <div
                              key={i}
                              className="p-1.5 rounded bg-ink-950 border border-white/5 text-[11px] text-ink-300 flex items-start gap-1.5"
                            >
                              <ShieldCheck className="w-3.5 h-3.5 text-ink-400 shrink-0 mt-0.5" />
                              <div>
                                <span className="font-medium text-white">{f.category || f.affected_dimension || 'Rule'}:</span> {f.message}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      <button
                        onClick={() => {
                          const assetId = testResult.output_asset_id || testResult.asset_id;
                          window.location.hash = '#/editor';
                          showToast({
                            type: 'info',
                            title: 'Sent to Page Editor',
                            message: `Asset ${assetId} ready for placement in page layout.`,
                          });
                        }}
                        className="w-full py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors mt-2"
                      >
                        <Layers className="w-3.5 h-3.5" />
                        Place in Page Editor
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>
            </div>
          </details>
        </div>
      </div>

      {/* Asset Selection Modal */}
      <Modal
        isOpen={assetModalOpen}
        onClose={() => setAssetModalOpen(false)}
        title="Select Reference Image from Library"
        size="lg"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-ink-400">
              Choose an existing image asset to bind as a character reference.
            </p>
          </div>

          {availableAssets.filter((a) =>
            a.asset_type === 'image_reference' ||
            a.asset_type === 'image_generated' ||
            a.mime_type?.startsWith('image/') ||
            /\.(png|jpg|jpeg|webp)$/i.test(a.original_filename || a.logical_filename || a.name || '')
          ).length === 0 ? (
            <div className="p-8 text-center border border-dashed border-white/10 rounded-xl space-y-2">
              <Camera className="w-8 h-8 text-ink-500 mx-auto" />
              <p className="text-xs text-ink-400">No image references found in project library.</p>
              <p className="text-[11px] text-ink-500">Upload a reference file above, then select it here.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-h-96 overflow-y-auto p-1">
              {availableAssets
                .filter((a) =>
                  a.asset_type === 'image_reference' ||
                  a.asset_type === 'image_generated' ||
                  a.mime_type?.startsWith('image/') ||
                  /\.(png|jpg|jpeg|webp)$/i.test(a.original_filename || a.logical_filename || a.name || '')
                )
                .map((asset) => (
                  <div
                    key={asset.asset_id}
                    onClick={() => addReferenceAsset(asset.asset_id)}
                    className="p-2 rounded-xl bg-ink-900 border border-white/5 hover:border-white/30 cursor-pointer space-y-1.5 motion-card text-center"
                  >
                    <div className="aspect-square rounded-lg bg-black overflow-hidden flex items-center justify-center">
                      <img
                        src={apiClient.getAssetFileUrl(asset.asset_id)}
                        alt={asset.logical_filename || asset.original_filename || asset.name || asset.asset_id}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="text-[11px] font-medium text-white truncate">
                      {asset.logical_filename || asset.original_filename || asset.name || asset.asset_id}
                    </div>
                    <div className="text-[9px] font-mono text-ink-400 truncate">
                      {asset.asset_id}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      </Modal>

      {/* Propose to Canon Modal */}
      <Modal
        isOpen={canonModalOpen}
        onClose={() => setCanonModalOpen(false)}
        title="Propose Character Invariants to Canon"
        size="md"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-xl bg-ink-900 border border-white/10 text-xs text-ink-300 space-y-1">
            <div className="font-semibold text-white">Story Bible Canon Integration</div>
            <p className="text-ink-400 leading-relaxed">
              This action submits the {invariants.length} extracted visual invariants and {forbiddenDrift.length} forbidden drift rules to the Story Bible Canon mutation proposal queue. Changes will remain proposals until explicitly approved in Story Bible.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-ink-300 mb-1">
              Proposal Rationale / Note (Optional)
            </label>
            <textarea
              rows={3}
              value={canonReason}
              onChange={(e) => setCanonReason(e.target.value)}
              placeholder="e.g. Visual invariants extracted and confirmed from turnaround references."
              className="w-full bg-ink-900 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/30"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setCanonModalOpen(false)}
              className="px-4 py-2 bg-ink-800 hover:bg-ink-700 text-white rounded-xl text-xs font-medium border border-white/10"
            >
              Cancel
            </button>
            <button
              onClick={handleProposeToCanon}
              disabled={proposingCanon}
              className="px-4 py-2 bg-white text-black hover:bg-ink-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              {proposingCanon ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Submitting Proposal...
                </>
              ) : (
                <>
                  <BookOpen className="w-3.5 h-3.5" />
                  Submit to Canon Queue
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
export default CharacterCopierView;

