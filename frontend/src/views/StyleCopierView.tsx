import React, { useEffect, useState, useRef } from 'react';
import {
  Palette,
  Sparkles,
  Upload,
  AlertCircle,
  Trash2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Eye,
  Info,
  Sliders,
  Layers,
  FileCode,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { useToast } from '../components/common/Toast';
import { TabCharacterIcon } from '../components/agent/character';
import { apiClient } from '../api/client';
import type {
  StyleProfile,
  CharacterCopierProfile,
  StyleAnalysisRecord,
  StyleControlVariable,
  CreativeGenerationResult,
  ReferenceBinding,
  SemanticReferenceRole,
  QuickStyleTemplateDto,
} from '../types/creative';

interface StyleCopierViewProps {
  currentProject: string;
}

const STYLE_VARIABLE_FIELDS = [
  ['medium', 'Medium'],
  ['linework', 'Linework'],
  ['stroke_behavior', 'Brush / stroke behavior'],
  ['edge_quality', 'Edge softness'],
  ['shading', 'Shading'],
  ['palette', 'Palette and accent colors'],
  ['lighting', 'Lighting and shadows'],
  ['background_detail', 'Background detail'],
  ['texture', 'Surface texture'],
  ['shape_language', 'Shape language'],
  ['screentones_and_fx', 'Screentones and visual effects'],
] as const;

const MAX_STYLE_ANALYSIS_REFERENCES = 3;

const isStyleReferenceAvailableInProject = (asset: any, projectId: string, trustedPreviewIds: Set<string> = new Set()) =>
  asset?.project_id === projectId
  || asset?.extra_metadata?.is_canonical_anchor === true
  || (trustedPreviewIds.has(String(asset?.asset_id || '')) && asset?.project_id === 'quick_style_preview_lab');

const mergeStyleAnalysisVariables = (
  result: StyleAnalysisRecord,
  current: Record<string, StyleControlVariable>,
): Record<string, StyleControlVariable> => {
  const variables = Object.fromEntries(
    Object.entries(result.traits || {}).map(([key, trait]) => {
      const previous = current[key];
      return [key, {
        value: previous?.pinned ? previous.value : trait.summary,
        pinned: previous?.pinned || false,
        source: previous?.pinned ? 'user_authored' : 'model_observation',
      } satisfies StyleControlVariable];
    }),
  );
  const previousMedium = current.medium;
  return {
    ...variables,
    medium: {
      value: previousMedium?.pinned ? previousMedium.value : result.medium,
      pinned: previousMedium?.pinned || false,
      source: previousMedium?.pinned ? 'user_authored' : 'model_observation',
    },
    screentones_and_fx: {
      value: current.screentones_and_fx?.pinned
        ? current.screentones_and_fx.value
        : (result.screentones_and_fx || []).join(', '),
      pinned: current.screentones_and_fx?.pinned || false,
      source: current.screentones_and_fx?.pinned ? 'user_authored' : 'model_observation',
    },
  };
};

export const StyleCopierView: React.FC<StyleCopierViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();

  // State
  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const [activeProfile, setActiveProfile] = useState<StyleProfile | null>(null);
  const [availableAssets, setAvailableAssets] = useState<any[]>([]);
  const [assetMetadataById, setAssetMetadataById] = useState<Record<string, any>>({});
  const [quickStylePreviewIds, setQuickStylePreviewIds] = useState<string[]>([]);
  const [assetLibraryLoaded, setAssetLibraryLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [assetModalOpen, setAssetModalOpen] = useState(false);

  // Form states for active profile
  const [profileName, setProfileName] = useState('');
  const [stylePromptCore, setStylePromptCore] = useState('');
  const [negativeConstraints, setNegativeConstraints] = useState<string[]>([]);
  const [newConstraint, setNewConstraint] = useState('');
  const [references, setReferences] = useState<ReferenceBinding[]>([]);
  const [analysis, setAnalysis] = useState<StyleAnalysisRecord | null>(null);
  const [styleVariables, setStyleVariables] = useState<Record<string, StyleControlVariable>>({});

  // Test generation states
  const [testPrompt, setTestPrompt] = useState('A quiet street at dusk');
  const [testShotType, setTestShotType] = useState('Medium shot, cinematic eye-level angle');
  const [selectedCharacterProfileId, setSelectedCharacterProfileId] = useState<string>('');
  const [availableCharacters, setAvailableCharacters] = useState<CharacterCopierProfile[]>([]);
  const [testResult, setTestResult] = useState<CreativeGenerationResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Load initial data
  const loadData = async () => {
    try {
      setLoading(true);
      setAssetLibraryLoaded(false);
      const [profs, assets, chars, quickStyles] = await Promise.all([
        apiClient.listStyleProfiles(currentProject).catch(() => []),
        apiClient.listAssets({ project_id: currentProject }).catch(() => null),
        apiClient.listCharacterProfiles(currentProject).catch(() => []),
        apiClient.listQuickStyleTemplates(currentProject).catch(() => []),
      ]);

      setProfiles(profs);
      const assetRows = Array.isArray(assets) ? assets : [];
      setAssetLibraryLoaded(Array.isArray(assets));
      setAssetMetadataById(Object.fromEntries(
        assetRows.filter((asset) => typeof asset?.asset_id === 'string').map((asset) => [asset.asset_id, asset]),
      ));
      const previewIds = quickStyles.map((template: QuickStyleTemplateDto) => template.preview_asset_id).filter((id): id is string => Boolean(id));
      setQuickStylePreviewIds(previewIds);
      const trustedPreviewIds = new Set(previewIds);
      setAvailableAssets(assetRows.filter((asset) => isStyleReferenceAvailableInProject(asset, currentProject, trustedPreviewIds)));
      setAvailableCharacters(chars);
      if (chars.length > 0 && !selectedCharacterProfileId) {
        setSelectedCharacterProfileId(chars[0].profile_id);
      }

      if (profs.length > 0 && !activeProfile) {
        selectProfile(profs[0]);
      } else if (profs.length === 0) {
        createNewProfile();
      }
    } catch (err: any) {
      showToast({ type: 'error', title: 'Could not load styles', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [currentProject]);

  const selectProfile = (p: StyleProfile) => {
    setActiveProfile(p);
    setProfileName(p.name);
    setStylePromptCore(p.style_prompt_core);
    setNegativeConstraints(p.negative_constraints || []);
    setReferences(p.references || []);
    setAnalysis(p.analysis || null);
    setStyleVariables(p.style_variables || {});
    setTestResult(null);
  };

  const createNewProfile = () => {
    const fresh: StyleProfile = {
      profile_id: `style_${Date.now()}`,
      project_id: currentProject,
      name: 'New Style Profile',
      version: 1,
      status: 'draft',
      references: [],
      style_prompt_core: '',
      negative_constraints: [],
    };
    setActiveProfile(fresh);
    setProfileName(fresh.name);
    setStylePromptCore('');
    setNegativeConstraints([]);
    setReferences([]);
    setAnalysis(null);
    setStyleVariables({});
    setTestResult(null);
  };

  // Add reference images with automatic profile persistence
  const addReferenceAssets = async (assetIds: string[]) => {
    const uniqueIds = assetIds.filter((id) => !references.some((r) => r.asset_id === id));
    if (uniqueIds.length === 0) {
      if (assetIds.length === 1) {
        showToast({ type: 'info', title: 'Already added', message: 'Asset is already in style references.' });
      }
      return;
    }

    if (references.length + uniqueIds.length > MAX_STYLE_ANALYSIS_REFERENCES) {
      showToast({
        type: 'error',
        title: 'Reference limit reached',
        message: `Style analysis accepts up to ${MAX_STYLE_ANALYSIS_REFERENCES} images. Remove a reference before adding another.`,
      });
      return;
    }

    const newBindings: ReferenceBinding[] = uniqueIds.map((id) => ({
      asset_id: id,
      role: 'style_reference' as SemanticReferenceRole,
      weight: 1.0,
      notes: 'Visual style reference for rendering medium and palette',
    }));

    const nextRefs = [...references, ...newBindings];
    setReferences(nextRefs);
    setAnalysis(null);
    setAssetModalOpen(false);

    // Auto-persist to active profile immediately so references are preserved across reloads
    if (activeProfile) {
      try {
        const payload: StyleProfile = {
          ...activeProfile,
          name: profileName || activeProfile.name || 'Untitled Style Profile',
          style_prompt_core: stylePromptCore,
          negative_constraints: negativeConstraints,
          references: profileReferences(nextRefs),
          analysis: null,
          style_variables: styleVariables,
        };
        const saved = await apiClient.saveStyleProfile(currentProject, payload);
        setActiveProfile(saved);
        setProfiles((prev) => prev.map((p) => (p.profile_id === saved.profile_id ? saved : p)));
      } catch (err: any) {
        console.warn('Auto-save style profile reference failed:', err);
      }
    }
  };

  const addReferenceAsset = async (assetId: string) => {
    await addReferenceAssets([assetId]);
  };

  const removeReference = async (assetId: string) => {
    const nextRefs = references.filter((r) => r.asset_id !== assetId);
    setReferences(nextRefs);
    setAnalysis(null);
    if (activeProfile) {
      try {
        const payload: StyleProfile = {
          ...activeProfile,
          references: profileReferences(nextRefs),
          analysis: null,
          style_variables: styleVariables,
        };
        const saved = await apiClient.saveStyleProfile(currentProject, payload);
        setActiveProfile(saved);
        setProfiles((prev) => prev.map((p) => (p.profile_id === saved.profile_id ? saved : p)));
      } catch (err: any) {
        console.warn('Auto-save style profile reference removal failed:', err);
      }
    }
  };

  const updateReferenceWeight = (assetId: string, weight: number) => {
    const nextRefs = references.map((r) => (r.asset_id === assetId ? { ...r, weight } : r));
    setReferences(nextRefs);
    if (activeProfile) {
      apiClient.saveStyleProfile(currentProject, { ...activeProfile, references: profileReferences(nextRefs) }).catch(console.warn);
    }
  };

  const hasReferenceOutsideProject = () => assetLibraryLoaded && references.some((reference) => {
    const asset = assetMetadataById[reference.asset_id];
    return !asset || !isStyleReferenceAvailableInProject(asset, currentProject, new Set(quickStylePreviewIds));
  });

  // Quick-style cards show examples only. A creator may explicitly select one
  // for analysis, but it is never persisted as a reusable style reference.
  const profileReferences = (items: ReferenceBinding[]) =>
    items.filter((reference) => !quickStylePreviewIds.includes(reference.asset_id));

  // Unified multi-file processor for both input change and drag & drop
  const processUploadFiles = async (files: FileList | File[]) => {
    const fileList = Array.from(files);
    if (fileList.length === 0) return;
    const remainingSlots = Math.max(0, MAX_STYLE_ANALYSIS_REFERENCES - references.length);
    if (fileList.length > remainingSlots) {
      showToast({
        type: 'error',
        title: remainingSlots === 0 ? 'Reference limit reached' : 'Too many style references',
        message: remainingSlots === 0
          ? `Remove a reference before uploading another. Style analysis supports up to ${MAX_STYLE_ANALYSIS_REFERENCES} references.`
          : `You can add ${remainingSlots} more image${remainingSlots === 1 ? '' : 's'}; style analysis supports up to ${MAX_STYLE_ANALYSIS_REFERENCES} references.`,
      });
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

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
        const updatedAssets = await apiClient.listAssets({ project_id: currentProject }).catch(() => null);
        const assetRows = Array.isArray(updatedAssets) ? updatedAssets : [];
        setAssetLibraryLoaded(Array.isArray(updatedAssets));
        setAssetMetadataById(Object.fromEntries(
          assetRows.filter((asset) => typeof asset?.asset_id === 'string').map((asset) => [asset.asset_id, asset]),
        ));
        setAvailableAssets(assetRows.filter((asset) => isStyleReferenceAvailableInProject(asset, currentProject, new Set(quickStylePreviewIds))));
        showToast({
          type: 'success',
          title: 'Reference(s) Uploaded',
          message: `Successfully bound ${uploadedIds.length} style reference image(s).`,
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

  // Analyze Style
  const handleAnalyzeStyle = async () => {
    if (references.length === 0) {
      showToast({ type: 'error', title: 'No references', message: 'Please attach at least one reference image to analyze.' });
      return;
    }
    if (references.length > MAX_STYLE_ANALYSIS_REFERENCES) {
      showToast({
        type: 'error',
        title: 'Too many style references',
        message: `Remove references until ${MAX_STYLE_ANALYSIS_REFERENCES} or fewer remain, then analyze again.`,
      });
      return;
    }
    if (references.some((reference) => !reference.asset_id?.trim())) {
      showToast({
        type: 'error',
        title: 'Invalid reference',
        message: 'One of these references has no registered asset ID. Remove it and select or upload the image again.',
      });
      return;
    }
    if (hasReferenceOutsideProject()) {
      showToast({
        type: 'error',
        title: 'Reference is outside this project',
        message: 'Remove the unavailable reference, then choose an image from this project or upload it here.',
      });
      return;
    }
    try {
      setAnalyzing(true);
      const cleanInstructions = stylePromptCore.trim();
      const isLegacyMangaBoilerplate =
        cleanInstructions.toLowerCase().includes('authentic manga ink linework') ||
        cleanInstructions.toLowerCase().includes('textured monochrome screentones') ||
        cleanInstructions.toLowerCase().includes('screentones and crisp value separation');
      const instructionsToSend = (!isLegacyMangaBoilerplate && cleanInstructions.length > 0) ? cleanInstructions : undefined;

      const result = await apiClient.analyzeStyleReferences(currentProject, {
        asset_ids: references.map((r) => r.asset_id),
        user_instructions: instructionsToSend,
      });
      setAnalysis(result);
      const nextStyleVariables = mergeStyleAnalysisVariables(result, styleVariables);
      setStyleVariables(nextStyleVariables);
      const nextPromptCore = result.analysis_summary || (isLegacyMangaBoilerplate ? '' : stylePromptCore);
      const nextNeg = result.negative_constraints && result.negative_constraints.length > 0
        ? result.negative_constraints
        : [];

      setStylePromptCore(nextPromptCore);
      setNegativeConstraints(nextNeg);

      // Auto-persist analysis results immediately to active profile
      if (activeProfile) {
        const payload: StyleProfile = {
          ...activeProfile,
          name: profileName || activeProfile.name || 'Untitled Style Profile',
          style_prompt_core: nextPromptCore,
          negative_constraints: nextNeg,
          references: profileReferences(references),
          analysis: result,
          style_variables: nextStyleVariables,
        };
        apiClient.saveStyleProfile(currentProject, payload).then((saved) => {
          setActiveProfile(saved);
          setProfiles((prev) => prev.map((p) => (p.profile_id === saved.profile_id ? saved : p)));
        }).catch((err) => console.warn('Auto-save style analysis failed:', err));
      }

      showToast({ type: 'success', title: 'Analysis Complete', message: `Extracted ${Object.keys(result.traits).length} structured style traits from visual evidence.` });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Analysis failed', message: err.message });
    } finally {
      setAnalyzing(false);
    }
  };

  // Save Style Profile
  const handleSaveProfile = async (approved = false) => {
    if (!activeProfile) return;
    const cleanName = profileName.trim();
    if (!cleanName || cleanName === 'New Style Profile') {
      showToast({ type: 'error', title: 'Name your style', message: 'Enter a short name before saving this style.' });
      return;
    }
    if (!approved && references.length > MAX_STYLE_ANALYSIS_REFERENCES && !analysis) {
      showToast({
        type: 'error',
        title: 'Style analysis needs fewer references',
        message: `Remove references until ${MAX_STYLE_ANALYSIS_REFERENCES} or fewer remain before creating this analyzed style.`,
      });
      return;
    }
    if (!approved && references.length > 0 && !analysis && hasReferenceOutsideProject()) {
      showToast({
        type: 'error',
        title: 'Reference is outside this project',
        message: 'Remove the unavailable reference, then choose an image from this project or upload it here.',
      });
      return;
    }
    const isNewProfile = !profiles.some((profile) => profile.profile_id === activeProfile.profile_id);
    try {
      setLoading(true);
      let analysisForSave = analysis;
      let promptForSave = stylePromptCore;
      let negativesForSave = negativeConstraints;
      let styleVariablesForSave = styleVariables;

      // One simple Create Style action also analyzes attached references when needed.
      if (!approved && references.length > 0 && !analysisForSave) {
        setAnalyzing(true);
        const cleanInstructions = stylePromptCore.trim();
        const result = await apiClient.analyzeStyleReferences(currentProject, {
          asset_ids: references.map((reference) => reference.asset_id),
          user_instructions: cleanInstructions || undefined,
        });
        analysisForSave = result;
        promptForSave = result.analysis_summary || cleanInstructions;
        negativesForSave = result.negative_constraints || [];
        styleVariablesForSave = mergeStyleAnalysisVariables(result, styleVariables);
        setAnalysis(result);
        setStyleVariables(styleVariablesForSave);
        setStylePromptCore(promptForSave);
        setNegativeConstraints(negativesForSave);
      }
      const payload: StyleProfile = {
        ...activeProfile,
        name: cleanName,
        style_prompt_core: promptForSave,
        negative_constraints: negativesForSave,
        references: profileReferences(references),
        analysis: analysisForSave,
        style_variables: styleVariablesForSave,
        status: approved ? 'approved' : (isNewProfile ? 'draft' : 'ready'),
        approved_by_user: approved,
      };

      const saved = await apiClient.saveStyleProfile(currentProject, payload);
      if (approved) {
        const formallyApproved = await apiClient.approveStyleProfile(currentProject, saved.profile_id);
        setActiveProfile(formallyApproved);
      } else {
        setActiveProfile(saved);
      }

      await loadData();
      showToast({
        type: 'success',
        title: approved ? 'Style Approved' : (isNewProfile ? 'Style Created' : 'Style Saved'),
        message: references.length > 0 && analysisForSave
          ? `${cleanName} is saved and ready to use. Its reference images were analyzed.`
          : `${cleanName} is saved and ready to use.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Could not save style', message: err.payload?.message || err.message });
    } finally {
      setAnalyzing(false);
      setLoading(false);
    }
  };

  // Run Test Generation (Combined Style + Character support)
  const handleTestGenerate = async () => {
    if (!activeProfile) return;
    try {
      setGenerating(true);
      setTestResult(null);
      // Auto-save active profile first
      await handleSaveProfile(false);

      const genResult = await apiClient.generateWithCreativeProfiles(currentProject, {
        scene_action: testPrompt,
        shot_type: testShotType,
        style_profile_id: activeProfile.profile_id,
        character_profile_ids: selectedCharacterProfileId ? [selectedCharacterProfileId] : undefined,
        panel_id: 'test_panel_01',
        scene_id: 'test_scene_01',
      });
      setTestResult(genResult);
      const score = genResult.qa_result.overall_score ?? genResult.qa_result.style_score ?? genResult.qa_result.style_fidelity_score;
      showToast({
        type: genResult.is_simulated ? 'info' : 'success',
        title: genResult.is_simulated ? 'Simulated Draft Generated' : 'Test Generation Done',
        message: score == null ? 'Output generated; semantic style and identity remain unverified.' : `Measured QA score: ${Math.round(score)}%.`,
      });
    } catch (err: any) {
      showToast({ type: 'error', title: 'Test generation failed', message: err.message });
    } finally {
      setGenerating(false);
    }
  };

  const addConstraint = () => {
    if (!newConstraint.trim()) return;
    if (!negativeConstraints.includes(newConstraint.trim())) {
      setNegativeConstraints([...negativeConstraints, newConstraint.trim()]);
    }
    setNewConstraint('');
  };

  const removeConstraint = (c: string) => {
    setNegativeConstraints(negativeConstraints.filter((x) => x !== c));
  };

  const activeProfileIsSaved = !!activeProfile && profiles.some((profile) => profile.profile_id === activeProfile.profile_id);

  return (
    <div className="space-y-6">
      {/* Top Header & Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <TabCharacterIcon tab="style-copier" size={38} />
            <h1 className="text-xl font-bold text-white tracking-tight">Styles</h1>
            {activeProfile && (
              <Badge
                variant={activeProfile.approved_by_user ? 'success' : 'neutral'}
                size="sm"
              >
                {activeProfile.approved_by_user ? 'Ready to use' : activeProfileIsSaved ? 'Saved' : 'New style'}
              </Badge>
            )}
          </div>
          <p className="text-xs text-ink-400 mt-1">
            Save a look once, then reuse it across your project.
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
            New Style
          </button>

          <button
            onClick={() => handleSaveProfile(false)}
            disabled={loading || analyzing}
            className="px-3 py-1.5 bg-white text-black hover:bg-ink-200 disabled:opacity-50 rounded-lg text-xs font-semibold transition-colors"
          >
            {analyzing ? 'Looking at images…' : activeProfileIsSaved ? 'Save Changes' : 'Create Style'}
          </button>
          {activeProfileIsSaved && <details className="text-xs">
            <summary className="cursor-pointer text-ink-400 px-2 py-1">More</summary>
            <button
              onClick={() => handleSaveProfile(true)}
              disabled={loading || analyzing}
              title="Marks this reusable style profile as approved."
              className="mt-2 px-3 py-1.5 bg-ink-800 hover:bg-ink-700 text-white rounded-lg border border-white/10"
            >
              Approve style profile
            </button>
          </details>}
        </div>
      </div>

      {/* Honest Capabilities Notice */}
      <div className="p-3 rounded-xl bg-ink-900/80 border border-white/10 text-xs text-ink-300 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-ink-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
              <p className="text-ink-400 leading-relaxed">
            Add up to 3 pictures that show the look you want. InkLoop analyzes these references and suggests editable style details.
          </p>
        </div>
      </div>

      {/* Main Grid: References Left, Traits Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Reference Images Gallery (4 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card
            title={
              <div className="flex items-center justify-between w-full">
                <span>Reference pictures ({references.length})</span>
                
              </div>
            }
            subtitle="Add up to 3 pictures with the look you want."
          >
            <div className="space-y-4">
              {references.length > MAX_STYLE_ANALYSIS_REFERENCES && (
                <p role="alert" className="text-xs text-amber-300">
                  This saved profile has {references.length} references, but analysis accepts {MAX_STYLE_ANALYSIS_REFERENCES}. Remove {references.length - MAX_STYLE_ANALYSIS_REFERENCES} before analyzing.
                </p>
              )}
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
                      Upload 1 to 3 references (PNG, JPEG, WebP) to extract visual style and rendering rules
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

                      {/* Info & Weight */}
                      <div className="flex-1 min-w-0 space-y-1">
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
                            className="w-24 accent-white"
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
                      Click or drop to add style references (up to 3 total; PNG, JPG, WebP)
                    </span>
                  </div>
                </div>
              )}

              <details className="rounded-lg border border-white/10 bg-ink-950/40 p-3">
                <summary className="cursor-pointer text-xs text-ink-300">Optional: preview the picture analysis</summary>
                <button
                  onClick={handleAnalyzeStyle}
                  disabled={analyzing || references.length === 0 || references.length > MAX_STYLE_ANALYSIS_REFERENCES}
                  className="w-full mt-3 py-2.5 px-4 bg-ink-800 text-white hover:bg-ink-700 rounded-xl text-xs font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  {analyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {analyzing ? 'Looking at the images…' : 'Analyze without saving'}
                </button>
              </details>
            </div>
          </Card>
        </div>

        {/* Right Column: Learned Traits & Core Prompt (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card
            title="Describe this look"
            subtitle="The image analysis fills this in when you create the style. You can edit it afterward."
          >
            <div className="space-y-4">
              {/* Profile Name */}
              <div>
                <label className="block text-xs font-medium text-ink-300 mb-1">
                  Style name
                </label>
                <input
                  type="text"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  className="w-full bg-ink-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                  placeholder="e.g. Dark Fantasy Noir Inking"
                />
              </div>

              {/* Core Style Prompt */}
              <div>
                <label className="block text-xs font-medium text-ink-300 mb-1">
                  Style description (optional)
                </label>
                <textarea
                  rows={3}
                  value={stylePromptCore}
                  onChange={(e) => setStylePromptCore(e.target.value)}
                  className="w-full bg-ink-900 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-white/30 font-mono leading-relaxed"
                  placeholder="For example: soft watercolor, warm colors, loose lines, simple backgrounds"
                />
              </div>

              {/* Extracted Structured Traits */}
              {analysis && analysis.traits && Object.keys(analysis.traits).length > 0 && (
                <div className="space-y-2 pt-2 border-t border-white/5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">What we noticed in the images</span>
                    <span className="text-[10px] text-ink-400">Medium: {analysis.medium}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Object.entries(analysis.traits).map(([dimKey, trait]) => (
                      <div
                        key={dimKey}
                        className="p-2.5 rounded-lg bg-ink-900 border border-white/5 space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-bold text-white capitalize">
                            {trait.dimension}
                          </span>
                          <span className="text-[10px] font-mono text-ink-400">
                            {trait.confidence == null ? 'Confidence not provided' : `${Math.round(trait.confidence * 100)}% confidence`}
                          </span>
                        </div>
                        <p className="text-[11px] text-ink-300 leading-tight">{trait.summary}</p>
                        {trait.rules.length > 0 && (
                          <div className="text-[10px] text-ink-400 italic">
                            Rule: {trait.rules[0]}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-white/10 bg-ink-950/40 p-3 space-y-2.5">
                <div>
                  <h3 className="text-xs font-semibold text-white">Keep style details consistent</h3>
                  <p className="text-[10px] text-ink-400 mt-1">Edit a value, then check “Keep fixed” to emphasize it in future image prompts. This guides the model; it cannot guarantee an exact match.</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {STYLE_VARIABLE_FIELDS.map(([key, label]) => {
                    const variable = styleVariables[key] || { value: '', pinned: false, source: 'user_authored' as const };
                    const observed = analysis?.traits?.[key]?.summary;
                    return (
                      <label key={key} className="block rounded-lg border border-white/5 bg-ink-900 p-2">
                        <span className="flex items-center justify-between gap-2 text-[11px] font-medium text-ink-200">
                          {label}
                          <span className="flex items-center gap-1.5 text-[10px] text-ink-400">
                            <input
                              type="checkbox"
                              checked={variable.pinned}
                              onChange={(event) => setStyleVariables((current) => ({
                                ...current,
                                [key]: { ...variable, pinned: event.target.checked, source: 'user_authored' },
                              }))}
                              className="accent-white"
                            />
                            Keep fixed
                          </span>
                        </span>
                        {observed && <span className="block text-[10px] text-ink-500 mt-1">Observed: {observed}</span>}
                        <input
                          type="text"
                          value={variable.value}
                          onChange={(event) => setStyleVariables((current) => ({
                            ...current,
                            [key]: { ...variable, value: event.target.value, source: 'user_authored' },
                          }))}
                          placeholder={observed || `Describe ${label.toLowerCase()}`}
                          className="mt-1 w-full bg-ink-950 border border-white/10 rounded-md px-2 py-1.5 text-[11px] text-white focus:outline-none focus:border-white/30"
                        />
                      </label>
                    );
                  })}
                </div>
              </div>

              <details className="pt-2 border-t border-white/5">
                <summary className="cursor-pointer text-xs text-ink-300">More controls</summary>
              <div className="space-y-2 pt-3">
                <label className="block text-xs font-medium text-ink-300">
                  Things this style should avoid
                </label>

                <div className="flex flex-wrap gap-1.5">
                  {negativeConstraints.map((c) => (
                    <span
                      key={c}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-ink-900 border border-white/10 text-[11px] text-ink-200"
                    >
                      {c}
                      <button
                        onClick={() => removeConstraint(c)}
                        className="text-ink-400 hover:text-white ml-0.5"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>

                <div className="flex items-center gap-2 mt-2">
                  <input
                    type="text"
                    value={newConstraint}
                    onChange={(e) => setNewConstraint(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addConstraint()}
                    placeholder="For example: no 3D shading"
                    className="flex-1 bg-ink-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                  <button
                    onClick={addConstraint}
                    className="px-3 py-1.5 bg-ink-800 hover:bg-ink-700 text-white rounded-lg text-xs font-medium border border-white/10"
                  >
                    Add
                  </button>
                </div>
              </div>
              </details>
            </div>
          </Card>

          <details className="rounded-xl border border-white/10 p-3">
            <summary className="cursor-pointer text-xs text-ink-300">Advanced: make a sample picture</summary>
          <Card
            title="Try a sample image"
            subtitle="Generate a real sample using this saved style"
          >
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-ink-400 mb-1">Scene Action Prompt</label>
                <input
                  type="text"
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  className="w-full bg-ink-900 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-ink-400 mb-1">Shot & Angle</label>
                  <input
                    type="text"
                    value={testShotType}
                    onChange={(e) => setTestShotType(e.target.value)}
                    className="w-full bg-ink-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
                  />
                </div>

                <div>
                  <label className="block text-xs text-ink-400 mb-1">
                    Optional Character Profile (Combined Studio)
                  </label>
                  <select
                    value={selectedCharacterProfileId}
                    onChange={(e) => setSelectedCharacterProfileId(e.target.value)}
                    className="w-full bg-ink-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-white/30"
                  >
                    <option value="">None (Pure Scene/Style Only)</option>
                    {availableCharacters.map((c) => (
                      <option key={c.profile_id} value={c.profile_id}>
                        {c.name} ({c.character_id})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  onClick={handleTestGenerate}
                  disabled={generating || references.length === 0}
                  className="px-5 py-2.5 bg-white text-black hover:bg-ink-200 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {generating ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Generating with Style...
                    </>
                  ) : (
                    <>
                      <Eye className="w-3.5 h-3.5" />
                      Test Generate
                    </>
                  )}
                </button>
              </div>

              {/* Test Result Display */}
              {testResult && (
                <div className="mt-4 p-4 rounded-xl bg-ink-900 border border-white/10 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-white">Generated Test Result</span>
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
                    {/* Image Preview */}
                    <div className="rounded-lg bg-black border border-white/10 overflow-hidden aspect-square flex items-center justify-center relative group">
                      <img
                        src={apiClient.getAssetFileUrl(testResult.output_asset_id || testResult.asset_id || '')}
                        alt="Test Generation Preview"
                        className="max-h-full max-w-full object-contain"
                      />
                    </div>

                    {/* QA Breakdown */}
                    <div className="space-y-2 text-xs">
                      <div className="p-2.5 rounded-lg bg-ink-950 border border-white/5 space-y-1">
                        <div className="flex justify-between">
                          <span className="text-ink-400">Style Fidelity:</span>
                          <span className="font-mono text-white font-bold">
                            {(testResult.qa_result?.style_score ?? testResult.qa_result?.overall_score ?? testResult.qa_result?.style_fidelity_score) == null ? 'Not verified' : `${Math.round(testResult.qa_result?.style_score ?? testResult.qa_result?.overall_score ?? testResult.qa_result?.style_fidelity_score!)}%`}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-ink-400">Dynamic Variation:</span>
                          <span className="font-mono text-white font-bold">
                            {(testResult.qa_result?.variation_score ?? testResult.qa_result?.dynamic_variation_score) == null ? 'Not verified' : `${Math.round(testResult.qa_result?.variation_score ?? testResult.qa_result?.dynamic_variation_score!)}%`}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-ink-400">Refinement Passes:</span>
                          <span className="font-mono text-ink-300">
                            {testResult.attempts_performed ?? 'Unknown'}
                          </span>
                        </div>
                      </div>

                      {/* Score Explanation */}
                      {testResult.qa_result?.score_explanation && (
                        <p className="text-[11px] text-ink-400 italic">
                          {testResult.qa_result.score_explanation}
                        </p>
                      )}

                      {/* Findings */}
                      {testResult.qa_result?.findings && testResult.qa_result.findings.length > 0 && (
                        <div className="space-y-1">
                          <div className="text-[10px] font-semibold text-ink-400 uppercase tracking-wider">
                            QA Inspection Findings
                          </div>
                          {testResult.qa_result.findings.map((f, i) => (
                            <div
                              key={i}
                              className="p-1.5 rounded bg-ink-950 border border-white/5 text-[11px] text-ink-300 flex items-start gap-1.5"
                            >
                              <ShieldCheck className="w-3.5 h-3.5 text-ink-400 shrink-0 mt-0.5" />
                              <div>
                                <span className="font-medium text-white">{f.category || f.affected_dimension || 'Finding'}:</span> {f.message}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Send to Page Editor action */}
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
              Choose an existing image asset to bind as a style reference.
            </p>
          </div>

          {availableAssets.filter((a) =>
            a.asset_type === 'image_reference' ||
            a.asset_type === 'image_generated' ||
            a.mime_type?.startsWith('image/') ||
            /\.(png|jpg|jpeg|webp)$/i.test(a.original_filename || a.logical_filename || a.name || '')
          ).length === 0 ? (
            <div className="p-8 text-center border border-dashed border-white/10 rounded-xl space-y-2">
              <Palette className="w-8 h-8 text-ink-500 mx-auto" />
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
    </div>
  );
};
export default StyleCopierView;

