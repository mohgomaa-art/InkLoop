import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Box, Check, FileImage, ImagePlus, Plus, Save, ShieldCheck, Sparkles, Upload } from 'lucide-react';
import { Card } from '../components/common/Card';
import { useToast } from '../components/common/Toast';
import { apiClient } from '../api/client';
import type { ObjectStudioProfile } from '../types/creative';

interface ObjectStudioViewProps { currentProject: string }
type ImageAsset = { asset_id: string; name?: string; original_filename?: string; mime_type?: string; content_sha256?: string; byte_size?: number; project_id?: string };

const emptyProfile = (): ObjectStudioProfile => ({
  prop_id: `object_${Date.now().toString(36)}`,
  version: 1,
  name: 'New object',
  description: '',
  required_attributes: [],
  reference_assets: [],
  form_and_proportions: '',
  materials: [],
  palette: [],
  components: [],
  distinctive_marks: [],
  stable_invariants: [],
  allowed_states: [],
  uncertain_traits: [],
  identity_features: [],
  trait_provenance: {},
  analysis: {
    analysis_status: 'not_run', analysis_source: 'unknown', observed_summary: '', inferred_purpose: '',
    unknown_or_occluded: [], creator_authored_facts: [],
  },
  creator_notes: '',
  draft_origin: 'creator',
  approval_status: 'draft',
});

const arrayFields: Array<[keyof ObjectStudioProfile, string]> = [
  ['materials', 'Materials'], ['palette', 'Colors'], ['components', 'Parts and connections'],
  ['distinctive_marks', 'Distinctive marks'], ['stable_invariants', 'Always keep the same'],
  ['allowed_states', 'Allowed state changes'], ['uncertain_traits', 'Unknown or unclear'],
];
const fieldClass = 'w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-2 text-sm text-white placeholder:text-ink-500 focus:border-white/30 focus:outline-none';

export const ObjectStudioView: React.FC<ObjectStudioViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();
  const [profiles, setProfiles] = useState<ObjectStudioProfile[]>([]);
  const [active, setActive] = useState<ObjectStudioProfile | null>(null);
  const [assets, setAssets] = useState<ImageAsset[]>([]);
  const [referenceIds, setReferenceIds] = useState<string[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState('');
  const [bibleVersion, setBibleVersion] = useState(1);
  const [busy, setBusy] = useState(false);
  const [pageError, setPageError] = useState('');
  const [pendingProposalId, setPendingProposalId] = useState('');
  const fileInput = useRef<HTMLInputElement>(null);

  const load = async (selectId?: string) => {
    setPageError('');
    try {
      const [nextProfiles, bible, nextAssets] = await Promise.all([
        apiClient.listObjectProfiles(currentProject),
        apiClient.getProjectBible(currentProject),
        apiClient.listAssets({ project_id: currentProject }),
      ]);
      const images = (nextAssets as ImageAsset[]).filter((item) => (item.mime_type || '').startsWith('image/'));
      setProfiles(nextProfiles);
      setAssets(images);
      setBibleVersion(Number(bible.bible_version || 1));
      const nextActive = nextProfiles.find((item) => item.prop_id === (selectId || active?.prop_id)) || nextProfiles[0] || null;
      setActive(nextActive);
      setReferenceIds((nextActive?.reference_assets || []).map((item) => item.asset_id));
      setPendingProposalId('');
    } catch (error: any) {
      setPageError(error?.message || 'Could not load Object Studio.');
    }
  };

  useEffect(() => { void load(); /* project switch reloads project-scoped objects and assets */ }, [currentProject]);

  const isSaved = !!active && profiles.some((item) => item.prop_id === active.prop_id);
  const savedProfile = active ? profiles.find((item) => item.prop_id === active.prop_id) : undefined;
  const isDirty = !!(isSaved && active && savedProfile && (
    JSON.stringify(active) !== JSON.stringify(savedProfile)
    || JSON.stringify(referenceIds) !== JSON.stringify((savedProfile.reference_assets || []).map((item) => item.asset_id))
  ));
  const isCanon = active?.approval_status === 'approved';
  const isProtected = !!active && active.approval_status !== 'draft';
  const analyzedAssetIds = useMemo(() => [...new Set(active?.identity_features.flatMap((feature) => feature.evidence_asset_ids || []) || [])].sort(), [active]);
  const analysisMatchesReferences = !!active && referenceIds.length > 0 && active.analysis.analysis_status === 'completed'
    && JSON.stringify(analyzedAssetIds) === JSON.stringify([...referenceIds].sort());
  const selectedAssets = useMemo(() => referenceIds.map((id) => assets.find((item) => item.asset_id === id)).filter(Boolean) as ImageAsset[], [referenceIds, assets]);
  const canAnalyze = !busy && !!active && referenceIds.length > 0 && referenceIds.length <= 4;

  const update = (patch: Partial<ObjectStudioProfile>) => setActive((prev) => prev ? { ...prev, ...patch } : prev);
  const updateList = (key: keyof ObjectStudioProfile, value: string) => {
    update({ [key]: value.split('\n').map((item) => item.trim()).filter(Boolean), trait_provenance: { ...(active?.trait_provenance || {}), [key]: 'user_authored' } } as Partial<ObjectStudioProfile>);
  };

  const startNew = () => {
    if (isDirty && !window.confirm('Discard unsaved object changes and start a new object?')) return;
    setActive(emptyProfile());
    setReferenceIds([]);
    setPendingProposalId('');
  };

  const copyAsDraft = () => {
    if (!active) return;
    const copy = structuredClone(active);
    copy.prop_id = `object_${Date.now().toString(36)}`;
    copy.name = `${active.name} copy`;
    copy.version = 1;
    copy.approval_status = 'draft';
    copy.draft_origin = 'creator';
    copy.draft_job_id = null;
    copy.analysis = { ...copy.analysis, analysis_status: 'not_run', analysis_source: 'copied_profile', analyzed_at: null };
    setActive(copy);
    setReferenceIds((copy.reference_assets || []).map((item) => item.asset_id));
    setPendingProposalId('');
  };

  const addReference = (assetId: string) => {
    if (!assetId || referenceIds.includes(assetId)) return;
    if (referenceIds.length >= 4) {
      showToast({ type: 'error', title: 'Reference limit reached', message: 'Object analysis accepts up to 4 reference pictures.' });
      return;
    }
    setReferenceIds((current) => current.includes(assetId) || current.length >= 4 ? current : [...current, assetId]);
  };

  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    try {
      const remainingSlots = Math.max(0, 4 - referenceIds.length);
      if (files.length > remainingSlots) throw new Error(`Only ${remainingSlots} reference image slot${remainingSlots === 1 ? '' : 's'} remain. Remove an image before uploading more.`);
      for (const file of Array.from(files)) {
        if (!file.type.startsWith('image/')) throw new Error(`${file.name} is not an image file.`);
        const asset = await apiClient.uploadImageAsset(file, currentProject, 'image_reference');
        if (!asset?.asset_id) throw new Error(`Upload did not return a registered asset ID for ${file.name}.`);
        setAssets((items) => [...items.filter((item) => item.asset_id !== asset.asset_id), asset]);
        setReferenceIds((current) => current.includes(asset.asset_id) || current.length >= 4 ? current : [...current, asset.asset_id]);
      }
      showToast({ type: 'success', title: 'Reference added', message: 'The uploaded image is registered to this project. Analyze it to extract visible object traits.' });
    } catch (error: any) {
      const message = error?.message || 'Image upload failed.';
      setPageError(message);
      showToast({ type: 'error', title: 'Reference upload failed', message });
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = '';
    }
  };

  const analyze = async () => {
    if (!active || !canAnalyze || isProtected) return;
    setBusy(true);
    setPageError('');
    try {
      const analyzed = await apiClient.analyzeObjectReferences(currentProject, {
        prop_id: active.prop_id,
        name: active.name,
        asset_ids: referenceIds,
        creator_notes: active.creator_notes,
      });
      const creatorAuthoredFields = [
        'description', 'form_and_proportions', 'materials', 'palette', 'components',
        'distinctive_marks', 'stable_invariants', 'allowed_states', 'uncertain_traits',
      ] as const;
      for (const key of creatorAuthoredFields) {
        if (active.trait_provenance?.[key] === 'user_authored') {
          (analyzed as any)[key] = active[key];
          analyzed.trait_provenance[key] = 'user_authored';
        }
      }
      analyzed.prop_id = active.prop_id;
      analyzed.name = active.name;
      analyzed.creator_notes = active.creator_notes;
      analyzed.identity_features = [
        ...analyzed.identity_features,
        ...active.identity_features.filter((feature) => feature.provenance === 'user_authored'),
      ];
      analyzed.analysis.creator_authored_facts = active.analysis.creator_authored_facts.length
        ? active.analysis.creator_authored_facts
        : (active.creator_notes.split('\n').map((line) => line.trim()).filter(Boolean));
      analyzed.draft_origin = active.draft_origin || 'object_studio';
      analyzed.draft_job_id = active.draft_job_id || null;
      setActive(analyzed);
      setReferenceIds((analyzed.reference_assets || []).map((item) => item.asset_id));
      showToast({ type: 'success', title: 'Analysis ready to review', message: 'Visible observations, inferences, and unknowns are separated below. Nothing has been saved yet.' });
    } catch (error: any) {
      const message = error?.message || 'Object analysis failed.';
      setPageError(message);
      showToast({ type: 'error', title: 'Analysis failed', message });
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = async () => {
    if (!active || !active.prop_id.trim() || !active.name.trim() || !active.description.trim()) {
      showToast({ type: 'error', title: 'Add the object basics', message: 'Give the object a stable ID, name, and short description before saving.' });
      return;
    }
    if (isProtected) return;
    setBusy(true);
    setPageError('');
    try {
      const payload = { prop: active, expected_bible_version: bibleVersion, reference_asset_ids: referenceIds };
      const result = isSaved
        ? await apiClient.updateObjectDraft(currentProject, active.prop_id, payload)
        : await apiClient.createObjectDraft(currentProject, payload);
      setBibleVersion(result.bible_version);
      setActive(result.prop);
      await load(result.prop.prop_id);
      showToast({ type: 'success', title: 'Object draft saved', message: 'This project-scoped draft can be reused by the Agent. It is not approved Canon.' });
    } catch (error: any) {
      const message = error?.message || 'Object draft could not be saved.';
      setPageError(message);
      showToast({ type: 'error', title: 'Save failed', message });
    } finally {
      setBusy(false);
    }
  };

  const proposeCanon = async () => {
    if (!active || !isSaved || isProtected) return;
    setBusy(true);
    setPageError('');
    try {
      const result = await apiClient.proposeObjectCanon(currentProject, active.prop_id);
      setPendingProposalId(result?.proposal?.proposal_id || '');
      showToast({ type: 'success', title: 'Canon proposal created', message: 'The object remains a draft until you explicitly approve this proposal.' });
    } catch (error: any) {
      const message = error?.message || 'Canon proposal failed.';
      setPageError(message);
      showToast({ type: 'error', title: 'Proposal failed', message });
    } finally {
      setBusy(false);
    }
  };

  const approveCanon = async () => {
    if (!active || !pendingProposalId) return;
    if (!window.confirm(`Approve “${active.name}” as a reusable Canon object?`)) return;
    setBusy(true);
    setPageError('');
    try {
      await apiClient.applyMutation(currentProject, { proposal_id: pendingProposalId });
      await load(active.prop_id);
      showToast({ type: 'success', title: 'Object approved', message: 'The existing Canon approval flow applied the object proposal.' });
    } catch (error: any) {
      const message = error?.message || 'Canon approval failed.';
      setPageError(message);
      showToast({ type: 'error', title: 'Approval failed', message });
    } finally {
      setBusy(false);
    }
  };

  const assetLabel = (asset: ImageAsset) => asset.original_filename || asset.name || asset.asset_id;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-white"><Box size={21} /><h1 className="text-2xl font-bold">Object Studio</h1>
            {active && <span className={`rounded-full px-2 py-1 text-xs ${isCanon ? 'bg-emerald-900/50 text-emerald-200' : isDirty ? 'bg-amber-900/40 text-amber-200' : 'bg-white/10 text-zinc-300'}`}>{isCanon ? 'Approved Canon' : isDirty ? 'Unsaved changes' : isSaved ? 'Saved draft' : 'Unsaved draft'}</span>}
          </div>
          <p className="mt-1 text-sm text-ink-400">Save a recurring object's design once, then reuse its same identity across story panels.</p>
        </div>
        <div className="flex items-center gap-2">
          <select className={fieldClass + ' min-w-48'} value={active?.prop_id || ''} onChange={(event) => {
            if (isDirty && !window.confirm('Discard unsaved changes to this object?')) return;
            const found = profiles.find((item) => item.prop_id === event.target.value);
            if (found) { setActive(found); setReferenceIds(found.reference_assets.map((item) => item.asset_id)); setPendingProposalId(''); }
          }}>
            {!profiles.length && <option value="">No saved objects yet</option>}
            {profiles.map((item) => <option key={item.prop_id} value={item.prop_id}>{item.name} · {item.approval_status}</option>)}
            {active && !profiles.some((item) => item.prop_id === active.prop_id) && <option value={active.prop_id}>{active.name} · unsaved</option>}
          </select>
          <button onClick={startNew} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-ink-800 px-3 py-2 text-sm text-white hover:bg-ink-700"><Plus size={16} />Add object</button>
          {isProtected && <button onClick={copyAsDraft} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-ink-800 px-3 py-2 text-sm text-white hover:bg-ink-700">Copy as draft</button>}
        </div>
      </header>

      {pageError && <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-400/30 bg-red-950/30 p-3 text-sm text-red-100"><AlertTriangle size={17} className="mt-0.5 shrink-0" />{pageError}</div>}
      <div className="rounded-xl border border-white/10 bg-ink-900/60 p-4 text-sm text-ink-300">
        <strong className="text-white">Identity stays the same; object state can change.</strong> “Lit,” “carried,” or “damaged” describes a scene. Shape, construction, parts, materials, and identifying marks describe the object. Reference images guide the model but cannot guarantee an exact match.
      </div>

      {active && <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        <div className="space-y-5 xl:col-span-5">
          <Card title={`Reference pictures (${referenceIds.length}/4)`} subtitle="Upload a picture or choose one already in this project's Library.">
            <div className="flex gap-2">
              <select value={selectedAssetId} onChange={(event) => setSelectedAssetId(event.target.value)} className={fieldClass}>
                <option value="">Choose an image from Library…</option>
                {assets.filter((item) => !referenceIds.includes(item.asset_id)).map((item) => <option key={item.asset_id} value={item.asset_id}>{assetLabel(item)}</option>)}
              </select>
              <button type="button" disabled={busy || !selectedAssetId || referenceIds.length >= 4} onClick={() => { addReference(selectedAssetId); setSelectedAssetId(''); }} className="rounded-lg border border-white/10 px-3 text-white disabled:opacity-40"><ImagePlus size={17} /></button>
              <button type="button" onClick={() => fileInput.current?.click()} disabled={busy || referenceIds.length >= 4} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 text-sm text-white disabled:opacity-40"><Upload size={16} />Upload</button>
              <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp" multiple className="hidden" onChange={(event) => void upload(event.target.files)} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {selectedAssets.map((asset) => <div key={asset.asset_id} className="overflow-hidden rounded-xl border border-white/10 bg-ink-950">
                <img src={apiClient.getAssetFileUrl(asset.asset_id)} alt={assetLabel(asset)} className="aspect-square w-full object-contain bg-black/30" />
                <div className="flex items-start justify-between gap-2 p-2"><span className="truncate text-xs text-zinc-300" title={assetLabel(asset)}>{assetLabel(asset)}</span><button type="button" aria-label={`Remove ${assetLabel(asset)}`} onClick={() => setReferenceIds((ids) => ids.filter((id) => id !== asset.asset_id))} className="text-zinc-500 hover:text-white">×</button></div>
              </div>)}
              {!referenceIds.length && <div className="col-span-full rounded-lg border border-dashed border-white/15 p-6 text-center text-sm text-ink-400"><FileImage className="mx-auto mb-2" size={22} />No reference picture yet. You can still write and save a draft by hand.</div>}
            </div>
            <button type="button" onClick={() => void analyze()} disabled={!canAnalyze || isProtected} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-40"><Sparkles size={16} />{busy ? 'Working...' : 'Analyze reference pictures'}</button>
            <p className="mt-2 text-xs text-ink-500">Analysis uses the registered image bytes. If the vision provider fails or is unavailable, the error is shown and no analysis is saved.</p>
          </Card>

          <Card title="What the picture supports" subtitle="These sections keep visible evidence separate from guesses and creator notes.">
            {analysisMatchesReferences ? <div className="space-y-4 text-sm">
              <div><div className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-300">Observed in reference</div><p className="text-zinc-200">{active.analysis.observed_summary || 'No observation returned.'}</p></div>
              <div><div className="mb-1 text-xs font-semibold uppercase tracking-wide text-sky-300">Model inference</div><p className="text-zinc-300">{active.analysis.inferred_purpose || 'Purpose remains unknown.'}</p></div>
              <div><div className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-300">Unknown or hidden</div><ul className="list-disc space-y-1 pl-5 text-zinc-300">{active.analysis.unknown_or_occluded.length ? active.analysis.unknown_or_occluded.map((item, index) => <li key={index}>{item}</li>) : <li>No additional unknowns were returned.</li>}</ul></div>
              <div className="text-xs text-ink-500">Source: {active.analysis.analysis_source}{active.analysis.model_id ? ` · ${active.analysis.model_id}` : ''}{active.analysis.analyzed_at ? ` · ${new Date(active.analysis.analyzed_at).toLocaleString()}` : ''}</div>
              {!!active.identity_features.length && <div className="space-y-2 border-t border-white/10 pt-3"><div className="text-xs font-semibold uppercase tracking-wide text-zinc-400">Trait evidence</div>{active.identity_features.map((feature) => <div key={feature.feature_id} className="rounded-lg bg-black/20 p-2 text-xs"><div className="flex justify-between gap-2"><strong className="text-white">{feature.label}</strong><span className="text-ink-500">{feature.provenance.replaceAll('_', ' ')} · {feature.stability}</span></div><p className="mt-1 text-zinc-300">{feature.description}</p><p className="mt-1 text-ink-500">Evidence: {feature.evidence_asset_ids.join(', ') || 'none'}</p></div>)}</div>}
            </div> : <div className="flex gap-2 text-sm text-ink-400"><AlertTriangle size={17} className="shrink-0" />{active.analysis.analysis_status === 'completed' ? 'The selected reference set differs from the images used for this analysis. Reanalyze before relying on these visual observations.' : 'No current reference analysis has been run for this draft. Written traits remain unverified until an actual image is analyzed.'}</div>}
          </Card>
        </div>

        <div className="space-y-5 xl:col-span-7">
          <Card title="Object identity" subtitle="Edit the stable design. Keep temporary scene conditions in the state list below.">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-xs text-ink-400">Stable object ID<input disabled={isProtected || isSaved} value={active.prop_id} onChange={(event) => update({ prop_id: event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '_') })} className={fieldClass + ' mt-1'} /></label>
              <label className="text-xs text-ink-400">Object name<input disabled={isProtected} value={active.name} onChange={(event) => update({ name: event.target.value })} className={fieldClass + ' mt-1'} /></label>
              <label className="text-xs text-ink-400 sm:col-span-2">Short description<textarea disabled={isProtected} rows={2} value={active.description} onChange={(event) => { update({ description: event.target.value, trait_provenance: { ...(active.trait_provenance || {}), description: 'user_authored' } }); }} className={fieldClass + ' mt-1'} placeholder="A compact brass-and-glass hand lamp with a hinged top…" />
                <span className="mt-1 block text-[11px] text-ink-500">Source: {(active.trait_provenance?.description || 'unknown').replaceAll('_', ' ')}</span></label>
              <label className="text-xs text-ink-400 sm:col-span-2">Form and proportions<textarea disabled={isProtected} rows={2} value={active.form_and_proportions} onChange={(event) => { update({ form_and_proportions: event.target.value, trait_provenance: { ...(active.trait_provenance || {}), form_and_proportions: 'user_authored' } }); }} className={fieldClass + ' mt-1'} placeholder="Overall silhouette, relative size, and how the parts are arranged" />
                <span className="mt-1 block text-[11px] text-ink-500">Source: {(active.trait_provenance?.form_and_proportions || 'unknown').replaceAll('_', ' ')}</span></label>
              {arrayFields.map(([key, label]) => <label key={key} className="text-xs text-ink-400">{label}<textarea disabled={isProtected} rows={3} value={(active[key] as string[]).join('\n')} onChange={(event) => updateList(key, event.target.value)} className={fieldClass + ' mt-1'} placeholder="One detail per line" /><span className="mt-1 block text-[11px] text-ink-500">Source: {(active.trait_provenance?.[key as string] || 'unknown').replaceAll('_', ' ')}</span></label>)}
              <label className="text-xs text-ink-400 sm:col-span-2">Creator-authored notes<textarea disabled={isProtected} rows={3} value={active.creator_notes} onChange={(event) => update({ creator_notes: event.target.value })} className={fieldClass + ' mt-1'} placeholder="Facts you know that the image cannot prove. These are kept separate from observations." /></label>
            </div>
          </Card>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-ink-900/60 p-4">
            <div className="text-xs text-ink-400">{isCanon ? 'Approved Canon object. Copy it to create a separate editable draft.' : isProtected ? 'Deprecated object. Copy it to create a separate editable draft.' : isDirty ? 'Unsaved changes · save the draft to update what the Agent will use.' : isSaved ? `Saved in project · object v${active.version} · Bible v${bibleVersion}` : 'Unsaved changes · not available to the Agent until saved.'}</div>
            <div className="flex flex-wrap gap-2">
              {!isProtected && <button onClick={() => void saveDraft()} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-black disabled:opacity-50"><Save size={16} />{busy ? 'Saving...' : 'Save draft'}</button>}
              {!isProtected && isSaved && !pendingProposalId && <button onClick={() => void proposeCanon()} disabled={busy} className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm text-white disabled:opacity-50"><ShieldCheck size={16} />Propose to Canon</button>}
              {pendingProposalId && <button onClick={() => void approveCanon()} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-emerald-100 px-4 py-2 text-sm font-semibold text-black disabled:opacity-50"><Check size={16} />Approve Canon</button>}
              {isCanon && <span className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/20 px-3 py-2 text-sm text-emerald-200"><ShieldCheck size={16} />Canon is protected</span>}
            </div>
          </div>
        </div>
      </div>}
    </div>
  );
};
