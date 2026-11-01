import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowDownToLine,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Grid2X2,
  Hand,
  Image as ImageIcon,
  ImagePlus,
  Layers3,
  Minus,
  PenLine,
  Plus,
  Redo2,
  RotateCcw,
  RotateCw,
  Save,
  Trash2,
  Type,
  Undo2,
  Upload,
  X,
  Check,
  Move,
  Maximize2,
  MessageSquare,
  Cloud,
  Zap,
  Bookmark,
  Copy,
  ClipboardPaste,
  Crop,
  FlipHorizontal,
  FlipVertical,
  Keyboard,
  HelpCircle,
  AlignCenter,
  Layers,
  Clock,
  Search,
  Sparkles,
  Radio,
  Flame,
  Scroll,
  Download,
  Eye,
  FileText,
} from 'lucide-react';
import { apiClient, BubblePresetDto, EditablePageDto, EditorLayerDto, PanelLayoutPresetDto } from '../api/client';
import { StyleProfile } from '../types/creative';
import { TabCharacterIcon } from '../components/agent/character';
import { SpeechBubbleSvg, BubbleShape, TailType, BubbleAccent } from '../components/editor/SpeechBubbleSvg';
import { TransformGizmo } from '../components/editor/TransformGizmo';

type Point = { x: number; y: number };
type ImageDimensions = { width: number; height: number };
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

const imageEditBounds = (
  rect: { x: number; y: number; width: number; height: number },
  fitMode: 'cover' | 'contain',
  dimensions: ImageDimensions,
  transform?: EditorLayerDto['transform'],
) => {
  const fitScale = fitMode === 'cover'
    ? Math.max(rect.width / dimensions.width, rect.height / dimensions.height)
    : Math.min(rect.width / dimensions.width, rect.height / dimensions.height);
  const scale = Math.abs(transform?.scale_x || 1);
  const width = dimensions.width * fitScale * scale;
  const height = dimensions.height * fitScale * scale;
  const centerX = rect.x + rect.width / 2 + (transform?.translate_x || 0);
  const centerY = rect.y + rect.height / 2 + (transform?.translate_y || 0);
  return { x: centerX - width / 2, y: centerY - height / 2, width, height, centerX, centerY };
};

export const TEMPLATE_OPTIONS = [
  { id: 'dynamic_shonen', name: 'Dynamic Action (4 Panels – Wide + 2 Diagonal + Slanted Hero)' },
  { id: 'three_tier_action_slant', name: 'Three-Tier Action Slant (4 Panels – Wide Top + 2 Wedges + Chevron Bot)' },
  { id: 'diagonal_slash_battle', name: 'Diagonal Slash Battle (6 Panels – Cross-Page 15° Clash)' },
  { id: 'shonen_climax_spread', name: 'Shonen Climax Spread (4 Panels – 62% Hero Splash + 3 Cuts)' },
  { id: 'four_panel_cinematic', name: 'Four-Panel Cinematic (16:9 Wide Header + 3 Rhythm Panels)' },
  { id: 'three_panel_hero', name: 'Three-Panel Hero (2 Tilted Top + Wide Hero Bottom)' },
  { id: 'three_panel_slanted', name: 'Three-Panel Slanted (Perspective Tilted Horizontal Gutters)' },
  { id: 'five_panel_action', name: 'Five-Panel Action (Diagonal Top Slash + Wide Mid + 2 Bot)' },
  { id: 'seven_panel_action_burst', name: 'Seven-Panel Action Burst (1 Banner + 3 Rapid Cuts + 3 Aftermath)' },
  { id: 'nine_panel_grid', name: 'Nine-Panel Grid (Classic 3x3 Psychological Pacing)' },
  { id: 'two_panel_dramatic_spread', name: 'Two-Panel Dramatic Spread (Two Panoramic 50/50 Vistas)' },
  { id: 'eight_panel_manhwa', name: 'Eight-Panel Manhwa (4 Tiers x 2 Panels Episodic Rhythm)' },
  { id: 'manga_grid', name: 'Manga Grid (4 Asymmetric Panels)' },
  { id: 'six_panel_classic', name: 'Six-Panel Classic (2x3 Balanced Comic Grid)' },
  { id: 'four_koma', name: '4-Koma (Vertical Yonkoma Strip)' },
  { id: 'webtoon_vertical', name: 'Webtoon Vertical (Continuous Mobile Scroll Cadence)' },
];

export const ManualEditorView: React.FC<{ projectId: string }> = ({ projectId }) => {
  const [page, setPage] = useState<EditablePageDto | null>(null);
  const [pageId, setPageId] = useState('');
  const [chosenTemplate, setChosenTemplate] = useState<string>('dynamic_shonen');
  const [panelLayoutPresets, setPanelLayoutPresets] = useState<PanelLayoutPresetDto[]>([]);
  const [bubblePresets, setBubblePresets] = useState<BubblePresetDto[]>([]);
  const [showBubblePicker, setShowBubblePicker] = useState(false);
  const [bubblePickerQuery, setBubblePickerQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [imageEditLayerId, setImageEditLayerId] = useState<string | null>(null);
  const [selectedVertex, setSelectedVertex] = useState<number | null>(null);
  const [assets, setAssets] = useState<any[]>([]);
  const [projectCharacters, setProjectCharacters] = useState<Array<{ id: string; name: string }>>([]);
  const [projectStyles, setProjectStyles] = useState<StyleProfile[]>([]);
  const [savedPages, setSavedPages] = useState<any[]>([]);
  const [pageSearchQuery, setPageSearchQuery] = useState('');
  const [deletedPages, setDeletedPages] = useState<any[]>([]);
  const [revisions, setRevisions] = useState<any[]>([]);
  const [restoreRevision, setRestoreRevision] = useState<number | ''>('');
  const [savedRevision, setSavedRevision] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [showGuides, setShowGuides] = useState(true);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [diagnostics, setDiagnostics] = useState<any[]>([]);
  const [imagePreviews, setImagePreviews] = useState<Record<string, string>>({});
  const [imageSourceDimensions, setImageSourceDimensions] = useState<Record<string, ImageDimensions>>({});
  const [imageBoundsErrorFor, setImageBoundsErrorFor] = useState<string | null>(null);
  const imageDimensionAttemptsRef = useRef(new Set<string>());
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [conflictPage, setConflictPage] = useState<EditablePageDto | null>(null);
  const [undoStack, setUndoStack] = useState<EditablePageDto[]>([]);
  const [redoStack, setRedoStack] = useState<EditablePageDto[]>([]);
  const [draftSavedAt, setDraftSavedAt] = useState<Date | null>(null);
  const [availableDraft, setAvailableDraft] = useState<any | null>(null);
  const [showShortcutsModal, setShowShortcutsModal] = useState<boolean>(false);

  // In-Panel Direct Generation State
  const [inPanelGenOpen, setInPanelGenOpen] = useState(false);
  const [panelGenPrompt, setPanelGenPrompt] = useState('');
  const [panelGenCharacters, setPanelGenCharacters] = useState<string[]>([]);
  const [panelGenStyleId, setPanelGenStyleId] = useState('');
  const [panelGenCamera, setPanelGenCamera] = useState('medium shot, dynamic angle');
  const [panelGenLoading, setPanelGenLoading] = useState(false);
  const [panelGenStage, setPanelGenStage] = useState('');

  // Image & Asset Placement State
  const [imagePickerOpen, setImagePickerOpen] = useState(false);
  const [imagePickerQuery, setImagePickerQuery] = useState('');
  const [imagePickerFilter, setImagePickerFilter] = useState<'all' | 'panel' | 'character'>('all');
  const [uploadingImage, setUploadingImage] = useState(false);
  const imageUploadInputRef = useRef<HTMLInputElement>(null);

  const [exporting, setExporting] = useState(false);
  const [compositing, setCompositing] = useState(false);
  const [compositeModalUrl, setCompositeModalUrl] = useState<string | null>(null);
  const [exportedPdfUrl, setExportedPdfUrl] = useState<string | null>(null);

  const clipboardRef = useRef<EditorLayerDto | null>(null);
  const gizmoDragRef = useRef<{
    before: EditablePageDto;
    initialTransform?: any;
    initialMetadata?: any;
  } | null>(null);

  const fontInputRef = useRef<HTMLInputElement>(null);
  const loadedFontIds = useRef(new Set<string>());
  const saveInFlightRef = useRef(false);
  const editSequenceRef = useRef(0);
  const svgRef = useRef<SVGSVGElement>(null);
  const canvasScrollRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    id: string;
    start: Point;
    before: EditablePageDto;
    vertex?: number;
    kind: 'image' | 'panel' | 'vertex' | 'text' | 'line' | 'tail_tip';
  } | null>(null);

  const dirty = !!page && hasChanges;
  const activePanelLayoutPreset = panelLayoutPresets.find((preset) => preset.id === chosenTemplate);

  useEffect(() => {
    Promise.all([apiClient.listPanelLayoutPresets(), apiClient.listBubblePresets()])
      .then(([layouts, bubbles]) => {
        setPanelLayoutPresets(layouts.presets);
        setBubblePresets(bubbles.presets);
        setChosenTemplate((current) => current === 'dynamic_shonen'
          ? (layouts.presets.find((preset) => preset.id === 'panel_layout_dynamic_shonen_action')?.id || current)
          : current);
      })
      .catch(() => {
        setPanelLayoutPresets([]);
        setBubblePresets([]);
      });
  }, []);

  // --- Load Assets & Registered Fonts ---
  const loadAssets = useCallback(async () => {
    try {
      setAssets(await apiClient.listAssets({ project_id: projectId }));
    } catch {
      setAssets([]);
    }
  }, [projectId]);

  useEffect(() => {
    void loadAssets();
  }, [loadAssets]);

  useEffect(() => {
    let cancelled = false;
    void apiClient.getProjectBible(projectId).then((bible) => {
      if (cancelled) return;
      const entries = Object.entries(bible?.characters || {}).map(([id, character]: [string, any]) => ({
        id,
        name: String(character?.name || id),
      }));
      setProjectCharacters(entries);
    }).catch(() => setProjectCharacters([]));
    return () => { cancelled = true; };
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    void apiClient.listStyleProfiles(projectId).then((styles) => {
      if (!cancelled) setProjectStyles(styles);
    }).catch(() => {
      if (!cancelled) setProjectStyles([]);
    });
    return () => { cancelled = true; };
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    const fontAssets = assets.filter((asset) => asset.asset_type === 'font_file');
    void Promise.all(
      fontAssets.map(async (asset) => {
        if (loadedFontIds.current.has(asset.asset_id) || !('FontFace' in window)) return;
        const family = String(asset.name || asset.original_filename || asset.asset_id);
        try {
          const face = new FontFace(family, `url(${JSON.stringify(apiClient.getAssetFileUrl(asset.asset_id))})`);
          await face.load();
          if (!cancelled) {
            document.fonts.add(face);
            loadedFontIds.current.add(asset.asset_id);
          }
        } catch {
          /* Fallback font family will be used */
        }
      })
    );
    return () => {
      cancelled = true;
    };
  }, [assets]);

  // --- Load Saved Pages ---
  const loadSavedPages = useCallback(async () => {
    try {
      const [list, deleted] = await Promise.all([apiClient.listEditablePages(projectId), apiClient.listDeletedEditablePages(projectId)]);
      setSavedPages([...(list || [])].sort((a, b) => String(b.updated_at || b.created_at || '').localeCompare(String(a.updated_at || a.created_at || ''))));
      setDeletedPages(deleted || []);
    } catch {
      setSavedPages([]);
      setDeletedPages([]);
    }
  }, [projectId]);

  const deleteSavedPage = async (event: React.MouseEvent, item: any) => {
    event.stopPropagation();
    if (!window.confirm(`Remove “${item.page_id}” from this project’s page list? Its saved revisions and source artwork will be retained.`)) return;
    setBusy(true);
    setError('');
    try {
      await apiClient.deleteEditablePage(item.page_id);
      await loadSavedPages();
      if (page?.page_id === item.page_id) {
        setPage(null);
        setPageId('');
      }
      setSuccessMsg(`Removed ${item.page_id} from the active page list. Revisions remain recoverable.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not remove page');
    } finally {
      setBusy(false);
    }
  };

  const restoreDeletedPage = async (item: any) => {
    setBusy(true);
    setError('');
    try {
      await apiClient.restoreDeletedEditablePage(item.page_id);
      await loadSavedPages();
      setSuccessMsg(`Restored ${item.page_id} to the page list.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not restore page');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void loadSavedPages();
  }, [loadSavedPages]);

  // --- Check Available Drafts in Local Storage ---
  const checkStoredDraft = useCallback(() => {
    try {
      const stored = localStorage.getItem(`inkloop_editor_draft_${projectId}`);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed?.document && parsed?.pageId) {
          setAvailableDraft(parsed);
          return parsed;
        }
      }
    } catch {
      /* ignore */
    }
    setAvailableDraft(null);
    return null;
  }, [projectId]);

  useEffect(() => {
    checkStoredDraft();
  }, [checkStoredDraft]);

  // --- Open Page with Local Persistence ---
  const openPage = useCallback(async (id: string, forceServerReload = false) => {
    if (!id) return;
    setBusy(true);
    setError('');
    setSuccessMsg('');
    try {
      // Check if we have an unsaved working draft for this page
      if (!forceServerReload) {
        try {
          const stored = localStorage.getItem(`inkloop_editor_draft_${projectId}`);
          if (stored) {
            const parsed = JSON.parse(stored);
            if (parsed?.pageId === id && parsed?.document && parsed?.hasChanges) {
              setPage(parsed.document);
              setPageId(id);
              setSavedRevision(parsed.savedRevision ?? parsed.document.revision ?? 0);
              setHasChanges(true);
              setConflictPage(null);
              setSelectedId(null);
              setSelectedVertex(null);
              setUndoStack([]);
              setRedoStack([]);
              localStorage.setItem(`inkloop_active_page_${projectId}`, id);
              localStorage.setItem(`inkloop_last_active_page_${projectId}`, id);
              try {
                setRevisions(await apiClient.getEditablePageRevisions(id));
              } catch {
                setRevisions([]);
              }
              setRestoreRevision('');
              setSuccessMsg(`Restored working draft with unsaved edits (${new Date(parsed.timestamp).toLocaleTimeString()}). Save (Ctrl+S) to persist revision.`);
              setBusy(false);
              return;
            }
          }
        } catch {}
      }

      const result = await apiClient.getEditablePage(id);
      setPage(result);
      setPageId(id);
      setSavedRevision(result.revision);
      setHasChanges(false);
      setConflictPage(null);
      setSelectedId(null);
      setSelectedVertex(null);
      setUndoStack([]);
      setRedoStack([]);
      try {
        setRevisions(await apiClient.getEditablePageRevisions(id));
      } catch {
        setRevisions([]);
      }
      setRestoreRevision('');
      localStorage.setItem(`inkloop_active_page_${projectId}`, id);
      localStorage.setItem(`inkloop_last_active_page_${projectId}`, id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not open page');
    } finally {
      setBusy(false);
    }
  }, [projectId]);

  // Deep-link page open on mount or hash change (only opens if ?page=... is explicitly in URL)
  useEffect(() => {
    const checkHashAndOpen = () => {
      const hashMatch = window.location.hash.match(/[?&]page=([^&]+)/);
      if (hashMatch) {
        const targetPageId = decodeURIComponent(hashMatch[1]);
        if (targetPageId && (!page || page.page_id !== targetPageId)) {
          void openPage(targetPageId);
        }
      }
    };

    checkHashAndOpen();
    window.addEventListener('hashchange', checkHashAndOpen);
    return () => window.removeEventListener('hashchange', checkHashAndOpen);
  }, [openPage, page]);

  // Reset active page selection when switching projects so we start clean at the hub
  useEffect(() => {
    setPage(null);
    setPageId('');
    setSelectedId(null);
    setSelectedVertex(null);
    checkStoredDraft();
  }, [projectId, checkStoredDraft]);

  // Track draft locally so unexpected navigation never loses work
  useEffect(() => {
    if (!page) return;
    const timer = setTimeout(() => {
      try {
        const draftData = {
          document: page,
          timestamp: Date.now(),
          pageId: page.page_id,
          hasChanges,
          savedRevision,
        };
        localStorage.setItem(`inkloop_editor_draft_${projectId}`, JSON.stringify(draftData));
        localStorage.setItem(`inkloop_draft_${page.page_id}`, JSON.stringify(page));
        setDraftSavedAt(new Date());
        setAvailableDraft(draftData);
      } catch {
        /* storage quota */
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [page, hasChanges, savedRevision, projectId]);

  const resumeDraft = useCallback((draftToLoad?: any) => {
    const target = draftToLoad || availableDraft;
    if (!target?.document) return;
    setPage(target.document);
    setPageId(target.pageId || target.document.page_id);
    setSavedRevision(target.savedRevision ?? target.document.revision ?? 0);
    setHasChanges(target.hasChanges ?? true);
    setSelectedId(null);
    setSelectedVertex(null);
    setUndoStack([]);
    setRedoStack([]);
    localStorage.setItem(`inkloop_active_page_${projectId}`, target.document.page_id);
    localStorage.setItem(`inkloop_last_active_page_${projectId}`, target.document.page_id);
    void apiClient.getEditablePageRevisions(target.document.page_id).then(setRevisions).catch(() => setRevisions([]));
    setSuccessMsg(`Restored draft from ${new Date(target.timestamp).toLocaleTimeString()} with ${target.document.layers.length} layers.`);
  }, [availableDraft, projectId]);

  const discardDraft = useCallback(async () => {
    if (!window.confirm('Discard all unsaved local edits and revert to the server revision?')) {
      return;
    }
    localStorage.removeItem(`inkloop_editor_draft_${projectId}`);
    if (page?.page_id) {
      localStorage.removeItem(`inkloop_draft_${page.page_id}`);
      await openPage(page.page_id, true);
    } else {
      setPage(null);
      setPageId('');
    }
    setAvailableDraft(null);
    setHasChanges(false);
    setSuccessMsg('Draft discarded. Showing server version.');
  }, [page, projectId, openPage]);

  // --- Commit state transition with Undo history ---
  const commit = (next: EditablePageDto, recordUndo = true) => {
    editSequenceRef.current += 1;
    if (recordUndo && page) {
      setUndoStack((items) => [...items.slice(-49), clone(page)]);
      setRedoStack([]);
    }
    setPage(next);
    if (recordUndo) {
      setHasChanges(true);
      setSuccessMsg('');
    }
  };

  const undo = () => {
    if (!page || !undoStack.length) return;
    setRedoStack((items) => [...items, clone(page)]);
    setPage(undoStack[undoStack.length - 1]);
    setUndoStack((items) => items.slice(0, -1));
    setHasChanges(true); // Undoing marks document modified again
    setSuccessMsg('');
  };

  const redo = () => {
    if (!page || !redoStack.length) return;
    setUndoStack((items) => [...items, clone(page)]);
    setPage(redoStack[redoStack.length - 1]);
    setRedoStack((items) => items.slice(0, -1));
    setHasChanges(true);
    setSuccessMsg('');
  };

  // --- Create New Page Layout ---
  const newPage = async (templateOverride?: string) => {
    setBusy(true);
    setError('');
    setSuccessMsg('');
    const tpl = templateOverride || chosenTemplate;
    try {
      const layout = await apiClient.generateEditableLayout({
        page_format: 'custom',
        width_px: 900,
        height_px: 1200,
        dpi: 96,
        margins_px: { top: 45, bottom: 45, left: 45, right: 45 },
        gutters_px: { horizontal: 18, vertical: 18 },
        bleed_px: 0,
        layout_template: tpl,
        panel_preset_id: tpl.startsWith('panel_layout_') ? tpl : undefined,
        reading_direction: 'ltr',
      });
      const result = await apiClient.createEditablePage({ project_id: projectId, layout });
      setPage(result);
      setPageId(result.page_id);
      setSavedRevision(result.revision);
      setHasChanges(false);
      setSelectedId(null);
      setSelectedVertex(null);
      setUndoStack([]);
      setRedoStack([]);
      localStorage.setItem(`inkloop_active_page_${projectId}`, result.page_id);
      localStorage.setItem(`inkloop_last_active_page_${projectId}`, result.page_id);
      setRevisions(await apiClient.getEditablePageRevisions(result.page_id));
      void loadSavedPages();
      setSuccessMsg(`Created new editable page (${result.page_id})`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create an E2 page');
    } finally {
      setBusy(false);
    }
  };

  // --- Versioned Save ---
  const save = useCallback(async (): Promise<boolean> => {
    if (!page || !dirty || saveInFlightRef.current) return false;
    const submittedEditSequence = editSequenceRef.current;
    saveInFlightRef.current = true;
    setBusy(true);
    setError('');
    setSuccessMsg('');
    try {
      const validation = await apiClient.validateEditablePage(page);
      setDiagnostics(validation.diagnostics || []);
      if (!validation.valid) {
        setShowDiagnostics(true);
        setError('Fix the page errors before saving a new version.');
        return false;
      }
      const result = await apiClient.saveEditablePage(page.page_id, savedRevision, page);
      setSavedRevision(result.revision);
      setConflictPage(null);
      const newerEditsExist = editSequenceRef.current !== submittedEditSequence;
      if (newerEditsExist) {
        // A save response must never replace a newer local edit (for example a
        // scale/rotate click made while autosave was in flight).
        setPage((current) => current ? { ...current, revision: result.revision } : current);
        setHasChanges(true);
        setSuccessMsg(`Saved revision ${result.revision}; newer edits are still saving.`);
      } else {
        setPage(result);
        setHasChanges(false);
        localStorage.removeItem(`inkloop_draft_${page.page_id}`);
        localStorage.removeItem(`inkloop_editor_draft_${projectId}`);
        setAvailableDraft(null);
        setSuccessMsg(`Saved revision ${result.revision} successfully.`);
      }
      setRevisions(await apiClient.getEditablePageRevisions(page.page_id));
      void loadSavedPages();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed; local edits are preserved.');
      if (e instanceof Error && /409|changed since revision|conflict/i.test(e.message)) {
        try {
          setConflictPage(await apiClient.getEditablePage(page.page_id));
        } catch {
          /* Preserve local edits */
        }
      }
      return false;
    } finally {
      saveInFlightRef.current = false;
      setBusy(false);
    }
  }, [page, dirty, savedRevision, loadSavedPages, projectId]);

  // Commit a new immutable server revision after a short pause. The browser draft
  // remains a recovery fallback; successful persistence clears it in save().
  useEffect(() => {
    if (!dirty || busy || !page) return;
    const timer = window.setTimeout(() => { void save(); }, 900);
    return () => window.clearTimeout(timer);
  }, [dirty, busy, page, save]);

  // --- Restore Previous Version ---
  const restoreVersion = async () => {
    if (!page || !restoreRevision || dirty) return;
    setBusy(true);
    setError('');
    setSuccessMsg('');
    try {
      const restored = await apiClient.restoreEditablePage(page.page_id, savedRevision, restoreRevision);
      setPage(restored);
      setSavedRevision(restored.revision);
      setHasChanges(false);
      setRevisions(await apiClient.getEditablePageRevisions(page.page_id));
      setRestoreRevision('');
      void loadSavedPages();
      setSuccessMsg(`Restored revision ${restoreRevision} as new revision ${restored.revision}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not restore this version.');
    } finally {
      setBusy(false);
    }
  };

  // --- Export & Composite Handlers ---
  const handleExportComic = async () => {
    if (!page) return;
    setExporting(true);
    setError('');
    try {
      if (dirty) {
        await save();
      }
      const exportReadingDirection = page.layout?.reading_direction || 'ltr';
      const res = await apiClient.exportEditablePage(page.page_id, { target_format: 'pdf', reading_direction: exportReadingDirection });
      setExportedPdfUrl(res.download_url);
      window.open(res.download_url, '_blank');
      setSuccessMsg('Comic exported successfully as print-ready PDF!');
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const handleCompositePreview = async () => {
    if (!page) return;
    setCompositing(true);
    setError('');
    try {
      if (dirty) {
        await save();
      }
      const res = await apiClient.compositeEditablePage(page.page_id);
      setCompositeModalUrl(res.image_url);
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'Composite rendering failed');
    } finally {
      setCompositing(false);
    }
  };

  // --- Validate Page ---
  const validate = async () => {
    if (!page) return;
    setBusy(true);
    try {
      const result = await apiClient.validateEditablePage(page);
      setDiagnostics(result.diagnostics || []);
      setShowDiagnostics(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation failed');
    } finally {
      setBusy(false);
    }
  };

  // Selected entities
  const selectedLayer = page?.layers.find((layer) => layer.layer_id === selectedId) || null;
  useEffect(() => {
    if (imageEditLayerId && selectedId !== imageEditLayerId) setImageEditLayerId(null);
  }, [imageEditLayerId, selectedId]);
  const selectedPanel = selectedLayer?.panel_id
    ? page?.layout.panel_slots.find((panel: any) => panel.panel_id === selectedLayer.panel_id)
    : selectedLayer?.kind === 'panel'
    ? page?.layout.panel_slots.find((panel: any) => panel.panel_id === selectedLayer.panel_id)
    : null;
  useEffect(() => {
    if (!page) return;
    localStorage.setItem(`inkloop_active_page_${projectId}`, page.page_id);
    localStorage.setItem(`inkloop_last_active_page_${projectId}`, page.page_id);
    if (selectedPanel?.panel_id) {
      localStorage.setItem(`inkloop_active_panel_${projectId}`, selectedPanel.panel_id);
    } else {
      localStorage.removeItem(`inkloop_active_panel_${projectId}`);
    }
  }, [page?.page_id, projectId, selectedPanel?.panel_id]);
  const selectedImage = selectedLayer?.kind === 'image' ? selectedLayer : null;
  const selectedPanelImage = selectedPanel
    ? (page?.layers || []).find((layer) => layer.kind === 'image' && layer.panel_id === selectedPanel.panel_id)
    : null;
  const imageEditing = !!selectedImage && imageEditLayerId === selectedImage.layer_id;
  const selectedText = selectedLayer?.kind === 'text' ? selectedLayer : null;
  const selectedLine = selectedLayer?.kind === 'line' ? selectedLayer : null;
  const imageSourceAssetIds = [...new Set((page?.layers || [])
    .filter((layer) => layer.kind === 'image' && layer.visible && layer.source_asset_id)
    .map((layer) => String(layer.source_asset_id)))].join('|');
  const imageSourceDimensionKey = (page?.layers || [])
    .filter((layer) => layer.kind === 'image' && layer.visible)
    .map((layer) => `${layer.source_asset_id || ''}:${layer.metadata?.width || ''}x${layer.metadata?.height || ''}`)
    .join('|');

  useEffect(() => {
    const assetIds = imageSourceAssetIds ? imageSourceAssetIds.split('|') : [];
    assetIds.forEach((assetId) => {
      const layer = page?.layers.find((item) => item.kind === 'image' && item.source_asset_id === assetId);
      const asset = assets.find((item) => item.asset_id === assetId);
      const width = Number(layer?.metadata?.width || asset?.width || asset?.dimensions?.width || asset?.metadata?.width);
      const height = Number(layer?.metadata?.height || asset?.height || asset?.dimensions?.height || asset?.metadata?.height);
      if (Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0) {
        setImageBoundsErrorFor((current) => current === assetId ? null : current);
        setImageSourceDimensions((current) => current[assetId] ? current : { ...current, [assetId]: { width, height } });
        return;
      }
      if (imageDimensionAttemptsRef.current.has(assetId)) return;
      imageDimensionAttemptsRef.current.add(assetId);
      const probe = new Image();
      probe.onload = () => {
        if (probe.naturalWidth > 0 && probe.naturalHeight > 0) {
          setImageBoundsErrorFor((current) => current === assetId ? null : current);
          setImageSourceDimensions((current) => ({
            ...current,
            [assetId]: { width: probe.naturalWidth, height: probe.naturalHeight },
          }));
        }
      };
      probe.onerror = () => {
        setImageBoundsErrorFor(assetId);
      };
      probe.src = apiClient.getAssetFileUrl(assetId);
    });
  }, [imageSourceAssetIds, imageSourceDimensionKey, assets]);

  const selectedImageDimensions = selectedImage
    ? imageSourceDimensions[selectedImage.source_asset_id || ''] || (() => {
        const asset = assets.find((item) => item.asset_id === selectedImage.source_asset_id);
        const width = Number(selectedImage.metadata?.width || asset?.width || asset?.dimensions?.width || asset?.metadata?.width);
        const height = Number(selectedImage.metadata?.height || asset?.height || asset?.dimensions?.height || asset?.metadata?.height);
        return Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0 ? { width, height } : null;
      })()
    : null;
  const imageEditReady = imageEditing && !!selectedImageDimensions;
  const dimensionsForImageLayer = (image: EditorLayerDto): ImageDimensions | null => {
    const cached = imageSourceDimensions[image.source_asset_id || ''];
    if (cached) return cached;
    const asset = assets.find((item) => item.asset_id === image.source_asset_id);
    const width = Number(image.metadata?.width || asset?.width || asset?.dimensions?.width || asset?.metadata?.width);
    const height = Number(image.metadata?.height || asset?.height || asset?.dimensions?.height || asset?.metadata?.height);
    return Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0 ? { width, height } : null;
  };

  const points = selectedPanel?.polygon || (selectedPanel
    ? [
        { x: selectedPanel.rect.x, y: selectedPanel.rect.y },
        { x: selectedPanel.rect.x + selectedPanel.rect.width, y: selectedPanel.rect.y },
        { x: selectedPanel.rect.x + selectedPanel.rect.width, y: selectedPanel.rect.y + selectedPanel.rect.height },
        { x: selectedPanel.rect.x, y: selectedPanel.rect.y + selectedPanel.rect.height },
      ]
    : []);

  const canvasWidth = page?.layout.canvas_spec.width_px || 900;
  const canvasHeight = page?.layout.canvas_spec.height_px || 1200;

  // E3 preview render debounce
  useEffect(() => {
    if (!page || !selectedImage?.transform || imageEditing) return;
    let cancelled = false;
    // While E3 produces the next masked preview, render the fitted source image
    // directly so controls stay responsive and the previous crop is not stale.
    setImagePreviews((current) => {
      const prior = current[selectedImage.layer_id];
      if (!prior) return current;
      URL.revokeObjectURL(prior);
      const next = { ...current };
      delete next[selectedImage.layer_id];
      return next;
    });
    const timer = window.setTimeout(() => {
      void apiClient
        .renderEditableImageLayer(page.page_id, selectedImage.layer_id, selectedImage.transform!, page.layout)
        .then((url) => {
          if (cancelled) URL.revokeObjectURL(url);
          else
            setImagePreviews((current) => {
              const prior = current[selectedImage.layer_id];
              if (prior) URL.revokeObjectURL(prior);
              return { ...current, [selectedImage.layer_id]: url };
            });
        })
        .catch((reason) => {
          if (!cancelled) setError(reason instanceof Error ? reason.message : 'E3 preview failed');
        });
    }, 180);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [page?.page_id, page?.layout, selectedImage?.layer_id, selectedImage?.transform, imageEditing]);

  // Window to SVG document coordinate transform
  const toDoc = (event: React.PointerEvent): Point => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const matrix = svg.getScreenCTM();
    if (!matrix) return { x: 0, y: 0 };
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const world = pt.matrixTransform(matrix.inverse());
    return { x: world.x, y: world.y };
  };

  const updateLayer = (layerId: string, update: (layer: EditorLayerDto) => EditorLayerDto) => {
    if (!page) return;
    const next = clone(page);
    next.layers = next.layers.map((layer) => (layer.layer_id === layerId ? update(layer) : layer));
    commit(next);
  };

  const updatePanelRect = (key: 'x' | 'y' | 'width' | 'height', value: number) => {
    if (!page || !selectedPanel) return;
    const next = clone(page);
    const panel = next.layout.panel_slots.find((item: any) => item.panel_id === selectedPanel.panel_id);
    const old = { ...panel.rect };
    const updated = { ...old, [key]: value };
    if (panel.polygon) {
      panel.polygon = panel.polygon.map((point: Point) => ({
        x: updated.x + (point.x - old.x) * (updated.width / old.width),
        y: updated.y + (point.y - old.y) * (updated.height / old.height),
      }));
    }
    panel.rect = updated;
    commit(next);
  };

  // --- Pointer Drag Events (Batched into single Undo step) ---
  const onPointerDownLayer = (event: React.PointerEvent, layerId: string, kind: 'image' | 'panel' | 'text' | 'line') => {
    event.stopPropagation();
    setSelectedId(layerId);
    setSelectedVertex(null);
    // Artwork stays locked to the panel until the creator double-clicks it to
    // enter crop/edit mode. A normal click only selects the image layer.
    if (kind === 'image' && imageEditLayerId !== layerId) return;
    if (!page) return;
    dragRef.current = {
      id: layerId,
      start: toDoc(event),
      before: clone(page),
      kind,
    };
    (event.currentTarget as SVGElement).setPointerCapture(event.pointerId);
  };

  const onPointerDownVertex = (event: React.PointerEvent, layerId: string, vertexIndex: number) => {
    event.stopPropagation();
    setSelectedId(layerId);
    setSelectedVertex(vertexIndex);
    if (!page) return;
    dragRef.current = {
      id: layerId,
      start: toDoc(event),
      before: clone(page),
      vertex: vertexIndex,
      kind: 'vertex',
    };
    (event.currentTarget as SVGElement).setPointerCapture(event.pointerId);
  };

  const onPointerDownTailHandle = (event: React.PointerEvent, layerId: string) => {
    event.stopPropagation();
    setSelectedId(layerId);
    setSelectedVertex(null);
    if (!page) return;
    dragRef.current = {
      id: layerId,
      start: toDoc(event),
      before: clone(page),
      kind: 'tail_tip',
    };
    (event.currentTarget as SVGElement).setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent) => {
    if (!dragRef.current || !page) return;
    const drag = dragRef.current;
    const here = toDoc(event);
    const dx = here.x - drag.start.x;
    const dy = here.y - drag.start.y;
    const next = clone(page);

    if (drag.kind === 'vertex' && drag.vertex !== undefined && selectedPanel?.polygon) {
      const panel = next.layout.panel_slots.find((item: any) => item.panel_id === selectedPanel.panel_id);
      if (panel?.polygon?.[drag.vertex]) {
        panel.polygon[drag.vertex] = { x: Math.round(here.x), y: Math.round(here.y) };
        const xs = panel.polygon.map((p: Point) => p.x);
        const ys = panel.polygon.map((p: Point) => p.y);
        panel.rect = {
          x: Math.min(...xs),
          y: Math.min(...ys),
          width: Math.max(...xs) - Math.min(...xs),
          height: Math.max(...ys) - Math.min(...ys),
        };
      }
    } else if (drag.kind === 'image') {
      // Moves image ONLY within mask - panel is untouched
      const layer = next.layers.find((item: EditorLayerDto) => item.layer_id === drag.id);
      if (layer) {
        const beforeLayer = drag.before.layers.find((item) => item.layer_id === drag.id);
        const curTransform = beforeLayer?.transform || {
          scale_x: 1,
          scale_y: 1,
          translate_x: 0,
          translate_y: 0,
          rotation_deg: 0,
          anchor_x: 0.5,
          anchor_y: 0.5,
        };
        layer.transform = {
          ...curTransform,
          translate_x: Math.round(curTransform.translate_x + dx),
          translate_y: Math.round(curTransform.translate_y + dy),
        };
      }
    } else if (drag.kind === 'text') {
      const layer = next.layers.find((item: EditorLayerDto) => item.layer_id === drag.id);
      const before = drag.before.layers.find((item) => item.layer_id === drag.id);
      if (layer && before) {
        layer.metadata.x = Math.round(Number(before.metadata.x || 0) + dx);
        layer.metadata.y = Math.round(Number(before.metadata.y || 0) + dy);
        if (before.metadata.tail_tip_x !== undefined) {
          layer.metadata.tail_tip_x = Math.round(Number(before.metadata.tail_tip_x) + dx);
        }
        if (before.metadata.tail_tip_y !== undefined) {
          layer.metadata.tail_tip_y = Math.round(Number(before.metadata.tail_tip_y) + dy);
        }
        delete layer.metadata.svg_path;
        delete layer.metadata.tail_path;
        delete layer.metadata.unified_path;
        delete layer.metadata.secondary_tail_path;
        delete layer.metadata.double_stroke_path;
        delete layer.metadata.ribbon_fold_paths;
        delete layer.metadata.accent_paths;
      }
    } else if (drag.kind === 'tail_tip') {
      const layer = next.layers.find((item: EditorLayerDto) => item.layer_id === drag.id);
      if (layer) {
        const anchor = { x: Math.round(here.x), y: Math.round(here.y) };
        layer.metadata.tail_tip_x = anchor.x;
        layer.metadata.tail_tip_y = anchor.y;
        layer.metadata.tail_target = anchor;
        layer.metadata.tail_anchor_character_id = layer.metadata.speaker_character_id || null;
        layer.metadata.tail_anchor_source = layer.metadata.speaker_character_id ? 'creator_confirmed' : 'unassigned';
        const panelImage = next.layers.find((item: EditorLayerDto) => item.panel_id === layer.panel_id && item.kind === 'image');
        layer.metadata.tail_anchor_asset_id = panelImage?.source_asset_id || null;
        layer.metadata.bubble_geometry_version = 1;
        delete layer.metadata.svg_path;
        delete layer.metadata.tail_path;
        delete layer.metadata.unified_path;
        delete layer.metadata.secondary_tail_path;
      }
    } else if (drag.kind === 'line') {
      const layer = next.layers.find((item: EditorLayerDto) => item.layer_id === drag.id);
      const before = drag.before.layers.find((item) => item.layer_id === drag.id);
      if (layer && before) {
        layer.metadata.x1 = Math.round(Number(before.metadata.x1 || 0) + dx);
        layer.metadata.y1 = Math.round(Number(before.metadata.y1 || 0) + dy);
        layer.metadata.x2 = Math.round(Number(before.metadata.x2 || 0) + dx);
        layer.metadata.y2 = Math.round(Number(before.metadata.y2 || 0) + dy);
      }
    } else if (drag.kind === 'panel') {
      // Moves panel geometry as a whole
      const panel = next.layout.panel_slots.find((item: any) => item.panel_id === selectedPanel?.panel_id);
      const beforePanel = drag.before.layout.panel_slots.find((item: any) => item.panel_id === selectedPanel?.panel_id);
      if (panel && beforePanel) {
        panel.rect.x = Math.round(beforePanel.rect.x + dx);
        panel.rect.y = Math.round(beforePanel.rect.y + dy);
        if (panel.polygon && beforePanel.polygon) {
          panel.polygon = beforePanel.polygon.map((p: Point) => ({
            x: Math.round(p.x + dx),
            y: Math.round(p.y + dy),
          }));
        }
      }
    }
    // Update live without polluting undo stack on every mousemove
    commit(next, false);
  };

  const onPointerUp = () => {
    const completedDrag = dragRef.current;
    dragRef.current = null;
    if (!completedDrag || !page) return;
    // Push prior state to undo stack once pointer releases
    setUndoStack((items) => [...items.slice(-49), completedDrag.before]);
    setRedoStack([]);
    setHasChanges(true);
  };

  // Place or Replace Image in target panel
  const placeOrReplaceImage = (asset: any, targetPanelId?: string) => {
    if (!page) return;
    const panelId = targetPanelId || selectedPanel?.panel_id;
    if (!panelId) return;

    const next = clone(page);
    const existingImage = next.layers.find(
      (layer: any) => layer.kind === 'image' && layer.panel_id === panelId
    );

    const imageLayerId = existingImage?.layer_id || `image_${asset.asset_id}_${panelId}`;
    const newImage: EditorLayerDto = {
      layer_id: imageLayerId,
      kind: 'image',
      label: asset.name || asset.original_filename || 'Placed image',
      parent_id: `layer_${panelId}`,
      visible: true,
      locked: false,
      z_index: 10,
      source_asset_id: asset.asset_id,
      source_sha256: asset.content_sha256,
      panel_id: panelId,
      transform: existingImage?.transform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 },
      fit_mode: existingImage?.fit_mode || 'cover',
      metadata: {
        width: asset.width || asset.dimensions?.width,
        height: asset.height || asset.dimensions?.height,
      },
    };

    next.layers = [
      ...next.layers.filter((layer: any) => !(layer.kind === 'image' && layer.panel_id === panelId)),
      newImage,
    ];
    commit(next);
    setSelectedId(newImage.layer_id);
    setImagePickerOpen(false);
    setSuccessMsg(`Artwork placed in Panel ${panelId}`);
  };

  const addImage = (asset: any) => {
    placeOrReplaceImage(asset);
  };

  const handleUploadAndPlaceImage = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !selectedPanel) return;
    setUploadingImage(true);
    setError('');
    try {
      const asset = await apiClient.uploadImageAsset(file, projectId, 'panel_image', file.name);
      setAssets((prev) => [asset, ...prev.filter((a) => a.asset_id !== asset.asset_id)]);
      placeOrReplaceImage(asset, selectedPanel.panel_id);
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'Could not upload image.');
    } finally {
      setUploadingImage(false);
      if (imageUploadInputRef.current) imageUploadInputRef.current.value = '';
    }
  };

  const filteredAssets = assets
    .filter((asset) => String(asset.asset_type).includes('image') || asset.mime_type?.startsWith('image/'))
    .filter((asset) => {
      if (imagePickerFilter === 'panel') {
        return asset.asset_type === 'panel_image' || asset.name?.toLowerCase().includes('panel');
      }
      if (imagePickerFilter === 'character') {
        return asset.asset_type === 'character_reference' || asset.name?.toLowerCase().includes('char');
      }
      return true;
    })
    .filter((asset) => {
      if (!imagePickerQuery.trim()) return true;
      const q = imagePickerQuery.toLowerCase();
      return (
        asset.name?.toLowerCase().includes(q) ||
        asset.original_filename?.toLowerCase().includes(q) ||
        asset.asset_id?.toLowerCase().includes(q)
      );
    });

  const handleInPanelGenerate = async () => {
    if (!page || !selectedPanel) return;
    if (!panelGenPrompt.trim()) {
      setError('Please describe the action or scene for this panel.');
      return;
    }
    setPanelGenLoading(true);
    setPanelGenStage('Sending selected cast and style references to the image provider…');
    setError('');

    try {
      const res = await apiClient.generateInPanelArt(page.page_id, selectedPanel.panel_id, {
        prompt: panelGenPrompt.trim(),
        character_ids: panelGenCharacters,
        camera_angle: panelGenCamera,
        style_profile_id: panelGenStyleId || undefined,
        style_profile_version: projectStyles.find((style) => style.profile_id === panelGenStyleId)?.version,
        fit_mode: 'cover',
      });

      if (res.success && res.updated_page) {
        commit(res.updated_page);
        setSuccessMsg(`Artwork generated and inked onto ${selectedPanel.panel_id}!`);
        setInPanelGenOpen(false);
        setPanelGenPrompt('');
      }
    } catch (err: any) {
      setError(err.message || 'Panel generation failed.');
    } finally {
      setPanelGenLoading(false);
      setPanelGenStage('');
    }
  };

  const addBubblePreset = (
    shape: BubbleShape,
    tailType: TailType,
    defaultText: string,
    options?: {
      halftone?: boolean; accent?: BubbleAccent; inverted?: boolean; presetId?: string;
      fillColor?: string; strokeColor?: string; textColor?: string; strokeWidth?: number;
      strokeDash?: string; useCase?: string; pinterestSearchUrl?: string;
    }
  ) => {
    if (!page || !selectedPanel) return;
    const id = `bbl_${crypto.randomUUID()}`;
    const width = Math.max(150, Math.min(250, selectedPanel.rect.width - 48));
    const height = 72;
    const x = selectedPanel.rect.x + Math.max(18, (selectedPanel.rect.width - width) / 2);
    const y = selectedPanel.rect.y + 24;
    const isInverted = Boolean(options?.inverted) || shape === 'dark_aura_ghost';
    const metadata = {
      text: defaultText,
      bubble_id: id,
      bubble_preset_id: options?.presetId,
      bubble_preset_version: options?.presetId ? 1 : undefined,
      bubble_use_case: options?.useCase,
      bubble_pinterest_search_url: options?.pinterestSearchUrl,
      x,
      y,
      width,
      height,
      font_family: shape === 'shout_burst' || shape === 'explosive_blast' || shape === 'spiky_ring_scream' ? 'Bangers' : 'Comic Neue',
      font_size: shape === 'shout_burst' || shape === 'spiky_ring_scream' ? 30 : 20,
      font_weight: shape === 'shout_burst' || shape === 'spiky_ring_scream' || shape === 'heavy_weight_emphasis' ? 'bold' : 'normal',
      color: options?.textColor || (isInverted ? '#FFFFFF' : '#111111'),
      align: 'center',
      direction: 'auto',
      line_height: 1.25,
      bubble_shape: shape,
      tail_type: tailType,
      tail_tip_x: Math.round(x + width * 0.62),
      tail_tip_y: Math.round(y + height + 40),
      tail_target: { x: Math.round(x + width * 0.62), y: Math.round(y + height + 40) },
      inverted_dark_mode: isInverted,
      bubble_fill: options?.fillColor || (isInverted ? '#111111' : '#FFFFFF'),
      bubble_stroke: options?.strokeColor || (isInverted ? '#FFFFFF' : '#111111'),
      stroke_width: options?.strokeWidth || (shape === 'shout_burst' || shape === 'spiky_ring_scream' || shape === 'heavy_weight_emphasis' ? 3.5 : 2.5),
      stroke_dash: options?.strokeDash ?? (shape === 'whisper_cloud_soft' || tailType === 'whisper_dashed' ? '5 4' : ''),
      halftone_shadow: Boolean(options?.halftone),
      accents: options?.accent || 'none',
      accent: options?.accent || 'none',
      padding_x: 24,
      padding_y: 18,
    };
    commit({
      ...clone(page),
      layers: [
        ...page.layers,
        {
          layer_id: id,
          kind: 'text',
          label: `${shape.replace('_', ' ')} bubble`,
          panel_id: selectedPanel.panel_id,
          visible: true,
          locked: false,
          z_index: Math.max(0, ...page.layers.map((l) => l.z_index)) + 1,
          fit_mode: 'cover',
          metadata,
        },
      ],
    });
    setSelectedId(id);
  };

  const addTextLayer = () => {
    if (!page || !selectedPanel) return;
    const id = `text_${crypto.randomUUID()}`;
    const width = Math.max(150, Math.min(250, selectedPanel.rect.width - 48));
    const height = 72;
    const x = selectedPanel.rect.x + Math.max(18, (selectedPanel.rect.width - width) / 2);
    const y = selectedPanel.rect.y + 24;
    const metadata = {
      text: 'Type dialogue...',
      x,
      y,
      width,
      height,
      font_family: 'Comic Neue',
      font_size: 20,
      font_weight: 'normal',
      color: '#111111',
      align: 'center',
      direction: 'auto',
      line_height: 1.25,
      bubble_shape: 'oval',
      tail_type: 'smooth_pointer',
      tail_tip_x: Math.round(x + width * 0.4),
      tail_tip_y: Math.round(y + height + 40),
      tail_target: { x: Math.round(x + width * 0.62), y: Math.round(y + height + 40) },
      bubble_fill: '#FFFFFF',
      bubble_stroke: '#111111',
      stroke_width: 2.5,
      stroke_dash: '',
      halftone_shadow: false,
      accents: 'none',
      padding_x: 24,
      padding_y: 18,
    };
    commit({
      ...clone(page),
      layers: [
        ...page.layers,
        {
          layer_id: id,
          kind: 'text',
          label: 'Dialogue Bubble',
          panel_id: selectedPanel.panel_id,
          visible: true,
          locked: false,
          z_index: Math.max(0, ...page.layers.map((l) => l.z_index)) + 1,
          fit_mode: 'cover',
          metadata,
        },
      ],
    });
    setSelectedId(id);
  };

  const addLineLayer = () => {
    if (!page || !selectedPanel) return;
    const id = `line_${crypto.randomUUID()}`;
    const metadata = {
      x1: selectedPanel.rect.x + 18,
      y1: selectedPanel.rect.y + selectedPanel.rect.height / 2,
      x2: selectedPanel.rect.x + selectedPanel.rect.width - 18,
      y2: selectedPanel.rect.y + selectedPanel.rect.height / 2,
      color: '#111111',
      stroke_width: 3,
      dash: '',
    };
    commit({
      ...clone(page),
      layers: [
        ...page.layers,
        {
          layer_id: id,
          kind: 'line',
          label: 'Line',
          panel_id: selectedPanel.panel_id,
          visible: true,
          locked: false,
          z_index: Math.max(0, ...page.layers.map((l) => l.z_index)) + 1,
          fit_mode: 'cover',
          metadata,
        },
      ],
    });
    setSelectedId(id);
  };

  const updateMetadata = (layerId: string, key: string, value: unknown) =>
    updateLayer(layerId, (item) => ({
      ...item,
      label: key === 'text' ? String(value).slice(0, 48) || 'Text' : item.label,
      metadata: { ...item.metadata, [key]: value },
    }));

  const removeLayer = (layerId: string) => {
    if (!page) return;
    const next = clone(page);
    next.layers = next.layers.filter((layer) => layer.layer_id !== layerId);
    commit(next);
    setSelectedId(null);
    setSelectedVertex(null);
  };

  const uploadFont = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      const font = await apiClient.uploadFont(projectId, file);
      setAssets((current) => [font, ...current.filter((asset) => asset.asset_id !== font.asset_id)]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not add this font file.');
    } finally {
      setBusy(false);
      if (fontInputRef.current) fontInputRef.current.value = '';
    }
  };

  const cornersOf = (rect: any): Point[] => [
    { x: rect.x, y: rect.y },
    { x: rect.x + rect.width, y: rect.y },
    { x: rect.x + rect.width, y: rect.y + rect.height },
    { x: rect.x, y: rect.y + rect.height },
  ];

  const addPolygonVertex = async () => {
    if (!page || !selectedPanel) return;
    const pointsNow: Point[] = selectedPanel.polygon?.length ? selectedPanel.polygon : cornersOf(selectedPanel.rect);
    let edgeIndex = 0;
    let longest = -1;
    pointsNow.forEach((point, index) => {
      const following = pointsNow[(index + 1) % pointsNow.length];
      const length = Math.hypot(following.x - point.x, following.y - point.y);
      if (length > longest) {
        longest = length;
        edgeIndex = index;
      }
    });
    const a = pointsNow[edgeIndex];
    const b = pointsNow[(edgeIndex + 1) % pointsNow.length];
    const nextPoints = [...pointsNow];
    nextPoints.splice(edgeIndex + 1, 0, { x: Math.round((a.x + b.x) / 2), y: Math.round((a.y + b.y) / 2) });
    const next = clone(page);
    const panel = next.layout.panel_slots.find((item: any) => item.panel_id === selectedPanel.panel_id);
    panel.polygon = nextPoints;
    const xs = nextPoints.map((point) => point.x);
    const ys = nextPoints.map((point) => point.y);
    panel.rect = {
      x: Math.min(...xs),
      y: Math.min(...ys),
      width: Math.max(...xs) - Math.min(...xs),
      height: Math.max(...ys) - Math.min(...ys),
    };
    const check = await apiClient.validateEditablePage(next);
    setDiagnostics(check.diagnostics || []);
    if (!check.valid) {
      setShowDiagnostics(true);
      setError('This vertex would make the panel geometry invalid.');
      return;
    }
    commit(next);
    setSelectedVertex(edgeIndex + 1);
  };

  const deletePolygonVertex = async () => {
    if (!page || !selectedPanel?.polygon || selectedVertex === null || selectedPanel.polygon.length <= 3) return;
    const nextPoints = selectedPanel.polygon.filter((_point: Point, index: number) => index !== selectedVertex);
    const next = clone(page);
    const panel = next.layout.panel_slots.find((item: any) => item.panel_id === selectedPanel.panel_id);
    panel.polygon = nextPoints;
    const xs = nextPoints.map((point: Point) => point.x);
    const ys = nextPoints.map((point: Point) => point.y);
    panel.rect = {
      x: Math.min(...xs),
      y: Math.min(...ys),
      width: Math.max(...xs) - Math.min(...xs),
      height: Math.max(...ys) - Math.min(...ys),
    };
    const check = await apiClient.validateEditablePage(next);
    setDiagnostics(check.diagnostics || []);
    if (!check.valid) {
      setShowDiagnostics(true);
      setError('Removing this vertex would make the panel geometry invalid.');
      return;
    }
    commit(next);
    setSelectedVertex(null);
  };

  const editVertex = (index: number, coordinate: 'x' | 'y', value: number) => {
    if (!page || !selectedPanel) return;
    const next = clone(page);
    const panel = next.layout.panel_slots.find((item: any) => item.panel_id === selectedPanel.panel_id);
    const currentPoints = panel.polygon ? [...panel.polygon] : cornersOf(panel.rect);
    currentPoints[index] = { ...currentPoints[index], [coordinate]: value };
    panel.polygon = currentPoints;
    const xs = currentPoints.map((point: Point) => point.x);
    const ys = currentPoints.map((point: Point) => point.y);
    panel.rect = {
      x: Math.min(...xs),
      y: Math.min(...ys),
      width: Math.max(...xs) - Math.min(...xs),
      height: Math.max(...ys) - Math.min(...ys),
    };
    commit(next);
  };

  // --- Clipboard & Layer Actions ---
  const copySelected = useCallback(() => {
    if (!selectedLayer) return;
    clipboardRef.current = clone(selectedLayer);
    try {
      localStorage.setItem('inkloop_editor_clipboard', JSON.stringify(clipboardRef.current));
    } catch {}
    setSuccessMsg(`Copied "${selectedLayer.label}" to clipboard (Ctrl+V to paste).`);
  }, [selectedLayer]);

  const pasteClipboard = useCallback(() => {
    if (!page) return;
    let item = clipboardRef.current;
    if (!item) {
      try {
        const stored = localStorage.getItem('inkloop_editor_clipboard');
        if (stored) item = JSON.parse(stored);
      } catch {}
    }
    if (!item) {
      setError('Clipboard is empty. Select an element and press Ctrl+C first.');
      return;
    }
    const next = clone(page);
    const newId = `${item.kind}_${crypto.randomUUID().slice(0, 8)}`;
    const highestZ = Math.max(0, ...next.layers.map((l: EditorLayerDto) => l.z_index || 0));
    const targetPanelId = selectedPanel?.panel_id || item.panel_id || next.layout.panel_slots[0]?.panel_id;

    const pastedLayer: EditorLayerDto = {
      ...clone(item),
      layer_id: newId,
      label: `${item.label} (Copy)`,
      panel_id: targetPanelId,
      z_index: highestZ + 1,
    };

    if (pastedLayer.kind === 'image') {
      const curT = pastedLayer.transform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 };
      pastedLayer.transform = {
        ...curT,
        translate_x: (curT.translate_x || 0) + 20,
        translate_y: (curT.translate_y || 0) + 20,
      };
    } else if (pastedLayer.kind === 'text') {
      pastedLayer.metadata = {
        ...pastedLayer.metadata,
        x: Number(pastedLayer.metadata.x || 0) + 24,
        y: Number(pastedLayer.metadata.y || 0) + 24,
      };
      if (pastedLayer.metadata.tail_tip_x !== undefined) {
        pastedLayer.metadata.tail_tip_x = Number(pastedLayer.metadata.tail_tip_x) + 24;
      }
      if (pastedLayer.metadata.tail_tip_y !== undefined) {
        pastedLayer.metadata.tail_tip_y = Number(pastedLayer.metadata.tail_tip_y) + 24;
      }
    } else if (pastedLayer.kind === 'line') {
      pastedLayer.metadata = {
        ...pastedLayer.metadata,
        x1: Number(pastedLayer.metadata.x1 || 0) + 20,
        y1: Number(pastedLayer.metadata.y1 || 0) + 20,
        x2: Number(pastedLayer.metadata.x2 || 0) + 20,
        y2: Number(pastedLayer.metadata.y2 || 0) + 20,
      };
    }

    next.layers.push(pastedLayer);
    commit(next);
    setSelectedId(newId);
    setSuccessMsg(`Pasted "${pastedLayer.label}".`);
  }, [page, selectedPanel]);

  const duplicateSelected = useCallback(() => {
    if (!selectedLayer) return;
    copySelected();
    pasteClipboard();
  }, [selectedLayer, copySelected, pasteClipboard]);

  const deleteSelected = useCallback(() => {
    if (!selectedLayer) return;
    removeLayer(selectedLayer.layer_id);
    setSuccessMsg('Element deleted.');
  }, [selectedLayer, removeLayer]);

  // --- Transformation Functions (Scale, Rotate, Mirror, Center) ---
  const setScale = useCallback((newScale: number) => {
    if (!selectedLayer || !page) return;
    if (selectedLayer.kind === 'image' && imageEditLayerId !== selectedLayer.layer_id) return;
    const clamped = Math.max(0.05, Math.min(10, Math.round(newScale * 100) / 100));
    if (selectedLayer.kind === 'image') {
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        transform: {
          ...(l.transform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 }),
          scale_x: clamped,
          scale_y: clamped,
        },
      }));
    } else if (selectedLayer.kind === 'text') {
      updateLayer(selectedLayer.layer_id, (l) => {
        const baseW = Number(l.metadata.base_width || l.metadata.width || 240);
        const baseH = Number(l.metadata.base_height || l.metadata.height || 140);
        const baseFont = Number(l.metadata.base_font_size || l.metadata.font_size || 24);
        const nextMeta: Record<string, any> = {
          ...l.metadata,
          base_width: baseW,
          base_height: baseH,
          base_font_size: baseFont,
          width: Math.max(40, Math.round(baseW * clamped)),
          height: Math.max(30, Math.round(baseH * clamped)),
          font_size: Math.max(10, Math.round(baseFont * clamped)),
          scale_factor: clamped,
        };
        delete nextMeta.svg_path;
        delete nextMeta.tail_path;
        delete nextMeta.unified_path;
        delete nextMeta.secondary_tail_path;
        delete nextMeta.double_stroke_path;
        delete nextMeta.ribbon_fold_paths;
        delete nextMeta.accent_paths;
        return {
          ...l,
          metadata: nextMeta,
        };
      });
    }
  }, [selectedLayer, page, imageEditLayerId]);

  const stepScale = useCallback((delta: number) => {
    if (!selectedLayer) return;
    const curScale = selectedLayer.kind === 'image'
      ? (selectedLayer.transform?.scale_x ?? 1)
      : Number(selectedLayer.metadata.scale_factor || 1);
    setScale(Math.round((curScale + delta) * 10) / 10);
  }, [selectedLayer, setScale]);

  const setRotation = useCallback((deg: number) => {
    if (!selectedLayer || !page) return;
    if (selectedLayer.kind === 'image' && imageEditLayerId !== selectedLayer.layer_id) return;
    let norm = Math.round(deg) % 360;
    if (norm < 0) norm += 360;
    if (selectedLayer.kind === 'image') {
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        transform: {
          ...(l.transform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 }),
          rotation_deg: norm,
        },
      }));
    } else if (selectedLayer.kind === 'text') {
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        metadata: {
          ...l.metadata,
          rotation_deg: norm,
        },
      }));
    }
  }, [selectedLayer, page, imageEditLayerId]);

  const stepRotate = useCallback((delta: number) => {
    if (!selectedLayer) return;
    const cur = selectedLayer.kind === 'image'
      ? (selectedLayer.transform?.rotation_deg ?? 0)
      : Number(selectedLayer.metadata.rotation_deg ?? 0);
    setRotation(cur + delta);
  }, [selectedLayer, setRotation]);

  const toggleFlipH = useCallback(() => {
    if (!selectedLayer || !page) return;
    if (selectedLayer.kind === 'image' && imageEditLayerId !== selectedLayer.layer_id) return;
    if (selectedLayer.kind === 'image') {
      const cur = Boolean(selectedLayer.metadata?.flip_h);
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        metadata: {
          ...l.metadata,
          flip_h: !cur,
        },
      }));
    } else if (selectedLayer.kind === 'text') {
      const cur = Boolean(selectedLayer.metadata?.flip_h);
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        metadata: {
          ...l.metadata,
          flip_h: !cur,
        },
      }));
    }
  }, [selectedLayer, page, imageEditLayerId]);

  const toggleFlipV = useCallback(() => {
    if (!selectedLayer || !page) return;
    if (selectedLayer.kind === 'image' && imageEditLayerId !== selectedLayer.layer_id) return;
    if (selectedLayer.kind === 'image') {
      const cur = Boolean(selectedLayer.metadata?.flip_v);
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        metadata: {
          ...l.metadata,
          flip_v: !cur,
        },
      }));
    } else if (selectedLayer.kind === 'text') {
      const cur = Boolean(selectedLayer.metadata?.flip_v);
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        metadata: {
          ...l.metadata,
          flip_v: !cur,
        },
      }));
    }
  }, [selectedLayer, page, imageEditLayerId]);

  const centerInPanel = useCallback(() => {
    if (!selectedLayer || !page) return;
    if (selectedLayer.kind === 'image' && imageEditLayerId !== selectedLayer.layer_id) return;
    if (selectedLayer.kind === 'image') {
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        transform: {
          ...(l.transform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 }),
          translate_x: 0,
          translate_y: 0,
        },
      }));
    } else if (selectedLayer.kind === 'text' && selectedPanel) {
      const w = Number(selectedLayer.metadata.width || 240);
      const h = Number(selectedLayer.metadata.height || 140);
      const newX = Math.round(selectedPanel.rect.x + (selectedPanel.rect.width - w) / 2);
      const newY = Math.round(selectedPanel.rect.y + (selectedPanel.rect.height - h) / 2);
      const dx = newX - Number(selectedLayer.metadata.x || 0);
      const dy = newY - Number(selectedLayer.metadata.y || 0);
      updateLayer(selectedLayer.layer_id, (l) => ({
        ...l,
        metadata: {
          ...l.metadata,
          x: newX,
          y: newY,
          tail_tip_x: l.metadata.tail_tip_x !== undefined ? Number(l.metadata.tail_tip_x) + dx : undefined,
          tail_tip_y: l.metadata.tail_tip_y !== undefined ? Number(l.metadata.tail_tip_y) + dy : undefined,
        },
      }));
    }
  }, [selectedLayer, page, selectedPanel, imageEditLayerId]);

  const toggleFitMode = useCallback(() => {
    if (!selectedImage) return;
    if (!imageEditing) return;
    const nextMode = selectedImage.fit_mode === 'cover' ? 'contain' : 'cover';
    updateLayer(selectedImage.layer_id, (l) => ({
      ...l,
      fit_mode: nextMode,
    }));
  }, [selectedImage, imageEditing]);

  const sendBackward = useCallback(() => {
    if (!selectedLayer || !page) return;
    const sorted = [...page.layers].sort((a, b) => a.z_index - b.z_index);
    const idx = sorted.findIndex((l) => l.layer_id === selectedLayer.layer_id);
    if (idx > 0) {
      const prev = sorted[idx - 1];
      const next = clone(page);
      const currentInNext = next.layers.find((l: EditorLayerDto) => l.layer_id === selectedLayer.layer_id)!;
      const prevInNext = next.layers.find((l: EditorLayerDto) => l.layer_id === prev.layer_id)!;
      const temp = currentInNext.z_index;
      currentInNext.z_index = prevInNext.z_index;
      prevInNext.z_index = temp;
      commit(next);
    }
  }, [selectedLayer, page]);

  const bringForward = useCallback(() => {
    if (!selectedLayer || !page) return;
    const sorted = [...page.layers].sort((a, b) => a.z_index - b.z_index);
    const idx = sorted.findIndex((l) => l.layer_id === selectedLayer.layer_id);
    if (idx >= 0 && idx < sorted.length - 1) {
      const following = sorted[idx + 1];
      const next = clone(page);
      const currentInNext = next.layers.find((l: EditorLayerDto) => l.layer_id === selectedLayer.layer_id)!;
      const follInNext = next.layers.find((l: EditorLayerDto) => l.layer_id === following.layer_id)!;
      const temp = currentInNext.z_index;
      currentInNext.z_index = follInNext.z_index;
      follInNext.z_index = temp;
      commit(next);
    }
  }, [selectedLayer, page]);

  // --- Transform Gizmo Interactive Callbacks ---
  const handleGizmoTranslate = (dx: number, dy: number, isFinal: boolean) => {
    if (!selectedLayer || !page) return;
    if (!gizmoDragRef.current) {
      gizmoDragRef.current = {
        before: clone(page),
        initialTransform: clone(selectedLayer.transform || {}),
        initialMetadata: clone(selectedLayer.metadata || {}),
      };
    }
    const { before, initialTransform, initialMetadata } = gizmoDragRef.current;
    const next = clone(before);
    const targetLayer = next.layers.find((l: EditorLayerDto) => l.layer_id === selectedLayer.layer_id);
    if (!targetLayer) return;

    if (targetLayer.kind === 'image') {
      targetLayer.transform = {
        ...(initialTransform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 }),
        translate_x: Math.round((initialTransform?.translate_x || 0) + dx),
        translate_y: Math.round((initialTransform?.translate_y || 0) + dy),
      };
    } else if (targetLayer.kind === 'text') {
      targetLayer.metadata = {
        ...initialMetadata,
        x: Math.round(Number(initialMetadata.x || 0) + dx),
        y: Math.round(Number(initialMetadata.y || 0) + dy),
      };
      if (initialMetadata.tail_tip_x !== undefined) {
        targetLayer.metadata.tail_tip_x = Math.round(Number(initialMetadata.tail_tip_x) + dx);
      }
      if (initialMetadata.tail_tip_y !== undefined) {
        targetLayer.metadata.tail_tip_y = Math.round(Number(initialMetadata.tail_tip_y) + dy);
      }
      delete targetLayer.metadata.svg_path;
      delete targetLayer.metadata.tail_path;
      delete targetLayer.metadata.unified_path;
      delete targetLayer.metadata.secondary_tail_path;
      delete targetLayer.metadata.double_stroke_path;
      delete targetLayer.metadata.ribbon_fold_paths;
      delete targetLayer.metadata.accent_paths;
    }

    if (isFinal) {
      gizmoDragRef.current = null;
      setUndoStack((items) => [...items.slice(-49), before]);
      setRedoStack([]);
      setHasChanges(true);
      setPage(next);
    } else {
      setPage(next);
    }
  };

  const handleGizmoScale = (scaleMultiplier: number, isFinal: boolean) => {
    if (!selectedLayer || !page) return;
    if (!gizmoDragRef.current) {
      gizmoDragRef.current = {
        before: clone(page),
        initialTransform: clone(selectedLayer.transform || {}),
        initialMetadata: clone(selectedLayer.metadata || {}),
      };
    }
    const { before, initialTransform, initialMetadata } = gizmoDragRef.current;
    const next = clone(before);
    const targetLayer = next.layers.find((l: EditorLayerDto) => l.layer_id === selectedLayer.layer_id);
    if (!targetLayer) return;

    const clamped = Math.max(0.05, Math.min(10, scaleMultiplier));

    if (targetLayer.kind === 'image') {
      targetLayer.transform = {
        ...(initialTransform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 }),
        scale_x: clamped,
        scale_y: clamped,
      };
    } else if (targetLayer.kind === 'text') {
      const baseW = Number(initialMetadata.base_width || initialMetadata.width || 240);
      const baseH = Number(initialMetadata.base_height || initialMetadata.height || 140);
      const baseFont = Number(initialMetadata.base_font_size || initialMetadata.font_size || 24);
      targetLayer.metadata = {
        ...initialMetadata,
        base_width: baseW,
        base_height: baseH,
        base_font_size: baseFont,
        width: Math.max(40, Math.round(baseW * clamped)),
        height: Math.max(30, Math.round(baseH * clamped)),
        font_size: Math.max(10, Math.round(baseFont * clamped)),
        scale_factor: clamped,
      };
      delete targetLayer.metadata.svg_path;
      delete targetLayer.metadata.tail_path;
      delete targetLayer.metadata.unified_path;
      delete targetLayer.metadata.secondary_tail_path;
      delete targetLayer.metadata.double_stroke_path;
      delete targetLayer.metadata.ribbon_fold_paths;
      delete targetLayer.metadata.accent_paths;
    }

    if (isFinal) {
      gizmoDragRef.current = null;
      setUndoStack((items) => [...items.slice(-49), before]);
      setRedoStack([]);
      setHasChanges(true);
      setPage(next);
    } else {
      setPage(next);
    }
  };

  const handleGizmoRotate = (newRotationDeg: number, isFinal: boolean) => {
    if (!selectedLayer || !page) return;
    if (!gizmoDragRef.current) {
      gizmoDragRef.current = {
        before: clone(page),
        initialTransform: clone(selectedLayer.transform || {}),
        initialMetadata: clone(selectedLayer.metadata || {}),
      };
    }
    const { before, initialTransform, initialMetadata } = gizmoDragRef.current;
    const next = clone(before);
    const targetLayer = next.layers.find((l: EditorLayerDto) => l.layer_id === selectedLayer.layer_id);
    if (!targetLayer) return;

    let norm = Math.round(newRotationDeg) % 360;
    if (norm < 0) norm += 360;

    if (targetLayer.kind === 'image') {
      targetLayer.transform = {
        ...(initialTransform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 }),
        rotation_deg: norm,
      };
    } else if (targetLayer.kind === 'text') {
      targetLayer.metadata = {
        ...initialMetadata,
        rotation_deg: norm,
      };
    }

    if (isFinal) {
      gizmoDragRef.current = null;
      setUndoStack((items) => [...items.slice(-49), before]);
      setRedoStack([]);
      setHasChanges(true);
      setPage(next);
    } else {
      setPage(next);
    }
  };

  // Values for HUD & Inspector
  const currentScale = selectedImage
    ? (selectedImage.transform?.scale_x ?? 1)
    : selectedText
    ? (Number(selectedText.metadata.scale_factor || 1))
    : 1;

  const currentRotation = selectedImage
    ? (selectedImage.transform?.rotation_deg ?? 0)
    : selectedText
    ? (Number(selectedText.metadata.rotation_deg || 0))
    : 0;

  const currentFlipH = selectedImage
    ? Boolean(selectedImage.metadata?.flip_h)
    : selectedText
    ? Boolean(selectedText.metadata?.flip_h)
    : false;

  const currentFlipV = selectedImage
    ? Boolean(selectedImage.metadata?.flip_v)
    : selectedText
    ? Boolean(selectedText.metadata?.flip_v)
    : false;

  // Keyboard navigation & shortcuts
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))) return;
      const command = event.ctrlKey || event.metaKey;

      if (event.key === '?' || (event.shiftKey && event.key === '/')) {
        event.preventDefault();
        setShowShortcutsModal((v) => !v);
        return;
      }
      if (event.key === 'Escape') {
        if (showShortcutsModal) {
          setShowShortcutsModal(false);
          return;
        }
        setSelectedId(null);
        setSelectedVertex(null);
        setImageEditLayerId(null);
        return;
      }
      if (command && event.key.toLowerCase() === 's') {
        event.preventDefault();
        void save();
        return;
      }
      if (command && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        event.shiftKey ? redo() : undo();
        return;
      }
      if (command && event.key.toLowerCase() === 'y') {
        event.preventDefault();
        redo();
        return;
      }
      if (command && event.key.toLowerCase() === 'c') {
        if (selectedLayer) {
          event.preventDefault();
          copySelected();
        }
        return;
      }
      if (command && event.key.toLowerCase() === 'v') {
        event.preventDefault();
        pasteClipboard();
        return;
      }
      if (command && (event.key === '=' || event.key === '+')) {
        event.preventDefault();
        setZoom((v) => Math.min(4.0, Math.round((v + 0.1) * 100) / 100));
        return;
      }
      if (command && (event.key === '-' || event.key === '_')) {
        event.preventDefault();
        setZoom((v) => Math.max(0.15, Math.round((v - 0.1) * 100) / 100));
        return;
      }
      if (command && event.key === '0') {
        event.preventDefault();
        setZoom(1);
        return;
      }
      if (command && event.key.toLowerCase() === 'd') {
        if (selectedLayer) {
          event.preventDefault();
          duplicateSelected();
        }
        return;
      }
      if (event.key === 'Delete' || event.key === 'Backspace') {
        if (selectedLayer) {
          event.preventDefault();
          deleteSelected();
        }
        return;
      }
      if (!command && event.key.toLowerCase() === 'h') {
        if (selectedLayer) {
          event.preventDefault();
          toggleFlipH();
        }
        return;
      }
      if (!command && event.key.toLowerCase() === 'v') {
        if (selectedLayer) {
          event.preventDefault();
          toggleFlipV();
        }
        return;
      }
      if (!command && event.key.toLowerCase() === 'c') {
        if (selectedImage) {
          event.preventDefault();
          toggleFitMode();
        }
        return;
      }
      if (event.key === '[') {
        if (selectedLayer) {
          event.preventDefault();
          sendBackward();
        }
        return;
      }
      if (event.key === ']') {
        if (selectedLayer) {
          event.preventDefault();
          bringForward();
        }
        return;
      }

      if (!page || !selectedLayer || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const amount = event.shiftKey ? 10 : 1;
      const dx = event.key === 'ArrowLeft' ? -amount : event.key === 'ArrowRight' ? amount : 0;
      const dy = event.key === 'ArrowUp' ? -amount : event.key === 'ArrowDown' ? amount : 0;
      const next = clone(page);

      if (selectedLayer.kind === 'image') {
        const layer = next.layers.find((item: EditorLayerDto) => item.layer_id === selectedLayer.layer_id)!;
        layer.transform ||= { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 };
        layer.transform.translate_x += dx;
        layer.transform.translate_y += dy;
      } else if (selectedLayer.kind === 'text') {
        const layer = next.layers.find((item: EditorLayerDto) => item.layer_id === selectedLayer.layer_id)!;
        layer.metadata.x = Number(layer.metadata.x || 0) + dx;
        layer.metadata.y = Number(layer.metadata.y || 0) + dy;
      } else if (selectedLayer.kind === 'line') {
        const layer = next.layers.find((item: EditorLayerDto) => item.layer_id === selectedLayer.layer_id)!;
        layer.metadata.x1 = Number(layer.metadata.x1 || 0) + dx;
        layer.metadata.y1 = Number(layer.metadata.y1 || 0) + dy;
        layer.metadata.x2 = Number(layer.metadata.x2 || 0) + dx;
        layer.metadata.y2 = Number(layer.metadata.y2 || 0) + dy;
      } else {
        const panel = next.layout.panel_slots.find((item: any) => item.panel_id === selectedLayer.panel_id);
        if (panel) {
          panel.rect.x += dx;
          panel.rect.y += dy;
          if (panel.polygon) {
            panel.polygon = panel.polygon.map((point: Point) => ({ x: point.x + dx, y: point.y + dy }));
          }
        }
      }
      commit(next);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [page, selectedLayer, selectedImage, undoStack, redoStack, showShortcutsModal, save, copySelected, pasteClipboard, duplicateSelected, deleteSelected, toggleFlipH, toggleFlipV, toggleFitMode, sendBackward, bringForward]);

  // Canvas Mouse Wheel Zoom Listener
  useEffect(() => {
    const el = canvasScrollRef.current;
    if (!el) return;

    const onNativeWheel = (e: WheelEvent) => {
      // Prevent whole page / outer container from scrolling while zooming over canvas
      e.preventDefault();
      e.stopPropagation();

      const delta = e.deltaY;
      if (delta === 0) return;

      // Smooth geometric scaling: scroll down = zoom out, scroll up = zoom in
      const factor = delta < 0 ? 1.1 : 0.9;
      setZoom((prev) => {
        const next = Math.round(prev * factor * 100) / 100;
        return Math.min(4.0, Math.max(0.15, next));
      });
    };

    el.addEventListener('wheel', onNativeWheel, { passive: false });
    return () => el.removeEventListener('wheel', onNativeWheel);
  }, [page]);

  // Handle explicit exit/close (draft is safely kept in localStorage for resumption)
  const handleCloseEditor = () => {
    if (page && hasChanges) {
      try {
        const draftData = {
          document: page,
          timestamp: Date.now(),
          pageId: page.page_id,
          hasChanges,
          savedRevision,
        };
        localStorage.setItem(`inkloop_editor_draft_${projectId}`, JSON.stringify(draftData));
        localStorage.setItem(`inkloop_draft_${page.page_id}`, JSON.stringify(page));
        setAvailableDraft(draftData);
      } catch {
        /* storage quota */
      }
    }
    localStorage.removeItem(`inkloop_active_page_${projectId}`);
    setPage(null);
    setPageId('');
    setSelectedId(null);
    setSelectedVertex(null);
    checkStoredDraft();
    void loadSavedPages();
  };

  if (!page) {
    const filteredPages = savedPages.filter((item) => {
      const q = pageSearchQuery.trim().toLowerCase();
      if (!q) return true;
      return (
        item.page_id.toLowerCase().includes(q) ||
        (item.template_id && item.template_id.toLowerCase().includes(q))
      );
    });

    return (
      <div className="editor-start w-full h-full overflow-y-auto bg-ink-950 p-6 md:p-10">
        <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-200">
          {/* Studio Header Banner */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 rounded-2xl bg-zinc-900/80 border border-white/10 shadow-lg">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-zinc-800 border border-white/10 flex items-center justify-center shrink-0 shadow-inner">
                <Layers size={28} className="text-white" />
              </div>
              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="text-2xl font-bold text-white tracking-tight">Canvas Page Studio</h1>
                  <TabCharacterIcon tab="editor" size={36} />
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-white/10 text-white border border-white/15">
                    {savedPages.length} Saved {savedPages.length === 1 ? 'Page' : 'Pages'}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-1 leading-relaxed max-w-2xl">
                  Compose manga & comic panel geometries, speech bubbles, and lettering. All artwork and revision history remain immutable.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <button
                type="button"
                onClick={() => void newPage()}
                disabled={busy}
                className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-white text-black hover:bg-zinc-200 font-bold text-xs shadow-md transition"
              >
                <Plus size={16} /> New Page Layout
              </button>
            </div>
          </div>

          {/* Working Draft Restoration Banner */}
          {availableDraft?.document && (
            <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm animate-in slide-in-from-top-2">
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
                  <Clock size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-2 text-xs font-bold text-amber-400">
                    <span>Unsaved Local Draft Available</span>
                    <span className="text-[10px] font-normal text-amber-300/80">• Auto-saved</span>
                  </div>
                  <div className="text-xs text-zinc-300 mt-0.5">
                    Page <strong className="font-mono text-white">{availableDraft.pageId}</strong> with <strong>{availableDraft.document.layers.length}</strong> layers • Last modified {new Date(availableDraft.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                <button
                  type="button"
                  onClick={() => resumeDraft(availableDraft)}
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs shadow-sm transition"
                >
                  Resume Draft
                </button>
                <button
                  type="button"
                  onClick={() => void discardDraft()}
                  className="px-3.5 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs transition"
                >
                  Discard
                </button>
              </div>
            </div>
          )}

          {/* Last Active Canvas Shortcut (when no unsaved draft exists) */}
          {!availableDraft?.document && localStorage.getItem(`inkloop_last_active_page_${projectId}`) && (
            <div className="p-4 rounded-2xl bg-zinc-900/60 border border-white/10 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Layers size={18} className="text-zinc-400 shrink-0" />
                <div className="text-xs text-zinc-300">
                  Continue editing last viewed canvas: <strong className="font-mono text-white">{localStorage.getItem(`inkloop_last_active_page_${projectId}`)}</strong>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  const lastId = localStorage.getItem(`inkloop_last_active_page_${projectId}`);
                  if (lastId) void openPage(lastId);
                }}
                disabled={busy}
                className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-white text-white hover:text-black font-semibold text-xs transition shadow-sm"
              >
                Open Canvas
              </button>
            </div>
          )}

          {/* Creation Station & Quick Jump */}
          <div className="rounded-2xl bg-zinc-900/80 border border-white/10 p-6 shadow-lg">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
              {/* Recipe Selector (Spans 2 columns) */}
              <div className="lg:col-span-2 space-y-3">
                <div className="flex items-center gap-2">
                  <Sparkles size={16} className="text-zinc-300" />
                  <h2 className="text-xs font-bold text-white uppercase tracking-wider">
                    Panel Layout Recipe
                  </h2>
                </div>
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <select
                      value={chosenTemplate}
                      onChange={(e) => setChosenTemplate(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-950 border border-white/10 text-xs text-white focus:outline-none focus:border-white/30"
                    >
                      {panelLayoutPresets.length > 0
                        ? Array.from(new Set(panelLayoutPresets.map((preset) => preset.category))).map((category) => (
                            <optgroup key={category} label={category}>
                              {panelLayoutPresets.filter((preset) => preset.category === category).map((preset) => (
                                <option key={preset.id} value={preset.id} title={preset.use_case}>
                                  {preset.name}
                                </option>
                              ))}
                            </optgroup>
                          ))
                        : TEMPLATE_OPTIONS.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => void newPage()}
                    disabled={busy}
                    className="px-5 py-2.5 rounded-xl bg-white text-black hover:bg-zinc-200 font-bold text-xs shadow-sm flex items-center justify-center gap-2 transition shrink-0"
                  >
                    <Plus size={15} /> Create Page
                  </button>
                </div>
                {activePanelLayoutPreset && (
                  <div className="text-[11px] text-zinc-400 pt-1">
                    <p className="truncate">{activePanelLayoutPreset.use_case}</p>
                  </div>
                )}
              </div>

              {/* Direct Open by ID */}
              <div className="space-y-3 lg:border-l lg:border-white/10 lg:pl-6">
                <h2 className="text-xs font-bold text-white uppercase tracking-wider">
                  Open by Page ID
                </h2>
                <div className="flex items-center gap-2">
                  <input
                    value={pageId}
                    onChange={(e) => setPageId(e.target.value)}
                    placeholder="e.g. page_story_..."
                    aria-label="Saved page ID"
                    className="flex-1 px-3.5 py-2.5 rounded-xl bg-zinc-950 border border-white/10 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white/30 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => void openPage(pageId)}
                    disabled={!pageId.trim() || busy}
                    className="px-4 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-white font-semibold text-xs transition disabled:opacity-40 shrink-0"
                  >
                    Open
                  </button>
                </div>
                <p className="text-[10px] text-zinc-500">Jump directly to any persisted canvas page revision.</p>
              </div>
            </div>
          </div>

          {/* Saved Pages Gallery */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <h2 className="text-lg font-bold text-white tracking-tight">Saved Pages</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-800 text-zinc-300 border border-white/10">
                  {savedPages.length}
                </span>
              </div>

              {savedPages.length > 3 && (
                <div className="relative w-full sm:w-64">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
                  <input
                    type="text"
                    value={pageSearchQuery}
                    onChange={(e) => setPageSearchQuery(e.target.value)}
                    placeholder="Search pages by ID..."
                    className="w-full pl-9 pr-3 py-1.5 bg-zinc-900 border border-white/10 rounded-xl text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white/30"
                  />
                </div>
              )}
            </div>

            {savedPages.length === 0 ? (
              <div className="p-12 rounded-2xl bg-zinc-900/40 border border-dashed border-white/10 text-center space-y-3">
                <Layers size={36} className="mx-auto text-zinc-600" />
                <h3 className="text-sm font-semibold text-white">No saved pages in this project</h3>
                <p className="text-xs text-zinc-400 max-w-sm mx-auto">
                  Pick a panel layout recipe above and click "Create Page" to start designing your first page.
                </p>
              </div>
            ) : filteredPages.length === 0 ? (
              <div className="p-8 rounded-2xl bg-zinc-900/40 border border-white/10 text-center text-xs text-zinc-400">
                No saved pages match "{pageSearchQuery}".
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {filteredPages.map((item) => {
                  const cWidth = item.canvas_width || 900;
                  const cHeight = item.canvas_height || 1200;

                  return (
                    <div
                      key={item.page_id}
                      className="group relative flex flex-col rounded-2xl bg-zinc-900/90 hover:bg-zinc-850 border border-white/10 hover:border-white/25 hover:shadow-2xl transition-all duration-200 overflow-hidden"
                    >
                      {/* Comic Page Thumbnail Container (aspect-[3/4]) */}
                      <div
                        className="relative aspect-[3/4] w-full bg-zinc-950 overflow-hidden cursor-pointer select-none border-b border-white/5"
                        onClick={() => void openPage(item.page_id)}
                      >
                        {/* Real Panel Layout & Artwork Preview */}
                        {item.panel_slots && item.panel_slots.length > 0 ? (
                          <div className="absolute inset-0 p-3">
                            <div className="relative w-full h-full bg-zinc-900/80 rounded-lg overflow-hidden border border-white/5 shadow-inner">
                              {item.panel_slots.map((slot: any, sIdx: number) => {
                                const rect = slot.rect || { x: 0, y: 0, width: cWidth, height: cHeight };
                                const left = `${(rect.x / cWidth) * 100}%`;
                                const top = `${(rect.y / cHeight) * 100}%`;
                                const width = `${(rect.width / cWidth) * 100}%`;
                                const height = `${(rect.height / cHeight) * 100}%`;

                                return (
                                  <div
                                    key={slot.panel_id || sIdx}
                                    className="absolute overflow-hidden bg-zinc-800 border border-black/40 shadow-sm"
                                    style={{ left, top, width, height }}
                                  >
                                    {slot.asset_id ? (
                                      <img
                                        src={apiClient.getAssetFileUrl(slot.asset_id)}
                                        alt={slot.panel_id}
                                        className="w-full h-full object-cover"
                                        decoding="async"
                                      />
                                    ) : (
                                      <div className="w-full h-full flex items-center justify-center text-[10px] font-mono font-medium text-zinc-500 bg-zinc-800/80">
                                        P{sIdx + 1}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ) : item.preview_asset_id ? (
                          <img
                            src={apiClient.getAssetFileUrl(item.preview_asset_id)}
                            alt={item.page_id}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            decoding="async"
                          />
                        ) : (
                          <div className="w-full h-full flex flex-col items-center justify-center gap-2 text-zinc-600 bg-zinc-950 p-4 text-center">
                            <Layers size={32} className="opacity-40" />
                            <span className="text-[10px] font-mono opacity-60">Layout Canvas</span>
                          </div>
                        )}

                        {/* Floating Badges */}
                        <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 z-10">
                          <span className="px-2 py-0.5 rounded-md bg-black/80 backdrop-blur-md text-[10px] font-mono text-white font-medium border border-white/10 shadow-sm">
                            Rev {item.revision}
                          </span>
                          {item.panel_count > 0 && (
                            <span className="px-2 py-0.5 rounded-md bg-zinc-800/80 backdrop-blur-md text-[10px] font-medium text-zinc-300 border border-white/10 shadow-sm">
                              {item.panel_count} Panels
                            </span>
                          )}
                        </div>

                        {/* Hover Overlay */}
                        <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-2 p-4 z-20">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              void openPage(item.page_id);
                            }}
                            disabled={busy}
                            className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 font-bold text-xs shadow-lg flex items-center gap-1.5 transition transform group-hover:scale-105"
                          >
                            <Layers size={14} /> Open Canvas
                          </button>
                        </div>
                      </div>

                      {/* Card Details & Actions Footer */}
                      <div className="p-4 flex flex-col justify-between flex-1 gap-3">
                        <div>
                          <h3
                            className="text-xs font-bold text-white truncate font-mono tracking-tight cursor-pointer hover:text-zinc-300 transition"
                            title={item.page_id}
                            onClick={() => void openPage(item.page_id)}
                          >
                            {item.page_id}
                          </h3>
                          <div className="flex items-center gap-2 mt-1.5 text-[11px] text-zinc-400">
                            <span>{item.image_count || 0} Artworks</span>
                            <span>•</span>
                            <span>{item.layer_count || 0} Layers</span>
                          </div>
                          <div className="text-[10px] text-zinc-500 mt-1">
                            Updated {new Date(item.updated_at || item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                          <button
                            type="button"
                            onClick={() => void openPage(item.page_id)}
                            disabled={busy}
                            className="flex-1 py-1.5 px-3 rounded-lg bg-white/10 hover:bg-white text-white hover:text-black font-semibold text-xs flex items-center justify-center gap-1.5 transition shadow-sm"
                          >
                            <span>Open</span>
                          </button>
                          <button
                            type="button"
                            onClick={(event) => void deleteSavedPage(event, item)}
                            disabled={busy}
                            aria-label={`Delete ${item.page_id}`}
                            title="Remove page; revisions are retained"
                            className="w-8 h-8 rounded-lg text-zinc-400 hover:text-red-400 hover:bg-red-500/10 flex items-center justify-center transition shrink-0"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recently Removed Pages Drawer */}
          {deletedPages.length > 0 && (
            <div className="p-5 rounded-2xl bg-zinc-900/60 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                  Recently Removed Pages ({deletedPages.length}) • Revisions Retained
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {deletedPages.map((item) => (
                  <div key={item.page_id} className="flex items-center justify-between p-3 rounded-xl bg-zinc-950 border border-white/5 text-xs">
                    <span className="font-mono text-zinc-400 truncate max-w-[200px]">{item.page_id}</span>
                    <button
                      type="button"
                      onClick={() => void restoreDeletedPage(item)}
                      disabled={busy}
                      className="px-2.5 py-1 rounded-md bg-white/10 hover:bg-white text-white hover:text-black text-[11px] font-semibold transition"
                    >
                      Restore
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="editor-error p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-200 text-xs">
              {error}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <section className="manual-editor" aria-label="Manual page editor" data-testid="manual-editor" data-selected-layer={selectedId || ''}>
      {showBubblePicker && (
        <div className="bubble-preset-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowBubblePicker(false); }}>
          <section className="bubble-preset-dialog" role="dialog" aria-modal="true" aria-labelledby="bubble-preset-title">
            <header>
              <div>
                <h2 id="bubble-preset-title">Bubble Library · {bubblePresets.length || 50}</h2>
                <p>Choose by story use. Every bubble gets a stable instance ID and preset ID.</p>
              </div>
              <button type="button" aria-label="Close bubble library" onClick={() => setShowBubblePicker(false)}>×</button>
            </header>
            <input
              autoFocus
              type="search"
              value={bubblePickerQuery}
              onChange={(event) => setBubblePickerQuery(event.target.value)}
              placeholder="Search whisper, shout, radio, thought…"
              aria-label="Search bubble presets"
            />
            <div className="bubble-preset-grid">
              {bubblePresets.filter((preset) => `${preset.name} ${preset.category} ${preset.use_case}`.toLowerCase().includes(bubblePickerQuery.toLowerCase())).map((preset) => (
                <div className="bubble-preset-card hover:border-zinc-500 hover:bg-[#282828] transition" key={preset.id}>
                  <button
                    type="button"
                    className="w-full text-left cursor-pointer disabled:cursor-not-allowed"
                    disabled={!selectedPanel}
                    title={`${preset.id} · ${preset.use_case}`}
                    onClick={() => {
                      addBubblePreset(preset.shape as BubbleShape, preset.tail_type as TailType, 'Type dialogue…', {
                        presetId: preset.id,
                        halftone: preset.halftone_shadow,
                        accent: preset.accent as BubbleAccent,
                        inverted: preset.inverted_dark_mode,
                        fillColor: preset.fill_color,
                        strokeColor: preset.stroke_color,
                        textColor: preset.text_color,
                        strokeWidth: preset.stroke_width,
                        strokeDash: preset.stroke_dash,
                        useCase: preset.use_case,
                        pinterestSearchUrl: preset.pinterest_search_url,
                      });
                      setShowBubblePicker(false);
                      setBubblePickerQuery('');
                    }}
                  >
                    <strong>{preset.name}</strong>
                    <span>{preset.use_case}</span>
                    <code>{preset.id}</code>
                  </button>
                </div>
              ))}
              {bubblePresets.length === 0 && <p className="bubble-preset-hint">Bubble presets could not load. Check the Canvas API connection and reopen this library.</p>}
            </div>
            {!selectedPanel && <p className="bubble-preset-hint">Select a panel before adding a bubble.</p>}
          </section>
        </div>
      )}
      <header className="editor-topbar">
        <div className="editor-crumb flex items-center gap-2">
          <button
            type="button"
            onClick={handleCloseEditor}
            className="px-2.5 py-1 mr-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white text-xs flex items-center gap-1.5 border border-white/10 transition cursor-pointer"
            title="Return to Page Hub (draft is safely preserved)"
          >
            <ArrowLeft size={13} />
            <span>Page Hub</span>
          </button>
          <TabCharacterIcon tab="editor" size={22} />
          <span>{projectId}</span>
          <b>/</b>
          <strong>{page.page_id}</strong>
          <div className="editor-draft-pill" title={dirty ? 'A local recovery copy exists; server revision save is pending.' : 'All changes are saved to a server revision.'}>
            <span className={`draft-dot ${dirty ? 'dirty' : 'saved'}`} />
            <span>{dirty ? 'Unsaved · saving' : `Saved (rev ${savedRevision})`}</span>
            {draftSavedAt && (
              <span className="text-zinc-500 text-[9px]">
                · {draftSavedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            )}
          </div>
          {dirty && (
            <button
              type="button"
              className="text-[10px] text-zinc-400 hover:text-red-400 transition px-2 py-1 rounded bg-transparent border-0 cursor-pointer"
              onClick={() => void discardDraft()}
              title="Discard local draft edits and revert to the server version"
            >
              Discard draft
            </button>
          )}
        </div>

        <div className="editor-actions">
          <button title="Undo (Ctrl+Z)" aria-label="Undo" onClick={undo} disabled={!undoStack.length}>
            <Undo2 />
          </button>
          <button title="Redo (Ctrl+Y)" aria-label="Redo" onClick={redo} disabled={!redoStack.length}>
            <Redo2 />
          </button>
          <i />
          <button title="Zoom out (Mouse Wheel Down)" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.15, Math.round((value - 0.1) * 100) / 100))}>
            <Minus />
          </button>
          <span
            className="cursor-pointer select-none hover:text-white px-1.5 py-0.5 rounded hover:bg-white/10 transition-colors"
            title="Wheel to zoom • Click to reset to 100%"
            onClick={() => setZoom(1)}
          >
            {Math.round(zoom * 100)}%
          </span>
          <button title="Zoom in (Mouse Wheel Up)" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(4.0, Math.round((value + 0.1) * 100) / 100))}>
            <Plus />
          </button>
          <button
            title="Toggle layout guides"
            aria-label="Toggle layout guides"
            className={showGuides ? 'selected' : ''}
            onClick={() => setShowGuides((value) => !value)}
          >
            <Grid2X2 />
          </button>

          <select
            className="editor-version-select text-xs"
            value={chosenTemplate}
            onChange={(e) => {
              const val = e.target.value;
              setChosenTemplate(val);
              void newPage(val);
            }}
            aria-label="Switch layout template"
            title="Switch page layout template"
          >
            {panelLayoutPresets.length > 0
              ? Array.from(new Set(panelLayoutPresets.map((preset) => preset.category))).map((category) => (
                  <optgroup key={category} label={category}>
                    {panelLayoutPresets.filter((preset) => preset.category === category).map((preset) => (
                      <option key={preset.id} value={preset.id} title={preset.use_case}>{preset.name}</option>
                    ))}
                  </optgroup>
                ))
              : TEMPLATE_OPTIONS.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>

          <select
            className="editor-version-select"
            value={restoreRevision}
            onChange={(e) => setRestoreRevision(e.target.value ? Number(e.target.value) : '')}
            aria-label="Choose a version to restore"
          >
            <option value="">Version History</option>
            {revisions.map((item) => (
              <option key={item.revision} value={item.revision}>
                Revision {item.revision}
                {item.revision === savedRevision ? ' · current' : ''}
              </option>
            ))}
          </select>

          <button
            className="editor-restore"
            onClick={() => void restoreVersion()}
            disabled={!restoreRevision || dirty || busy || restoreRevision === savedRevision}
          >
            <RotateCcw size={14} /> Restore
          </button>

          <button
            type="button"
            title="Keyboard Shortcuts (?)"
            aria-label="Keyboard Shortcuts"
            onClick={() => setShowShortcutsModal(true)}
          >
            <Keyboard size={15} />
          </button>

          <button className="editor-save motion-interactive" onClick={() => void save()} disabled={!dirty || busy}>
            <Save size={15} />
            {busy ? 'Saving...' : 'Save version'}
          </button>

          <button
            type="button"
            className="editor-composite-btn bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium px-2.5 py-1.5 rounded flex items-center gap-1.5 text-xs border border-white/10 transition-colors motion-interactive"
            onClick={() => void handleCompositePreview()}
            disabled={busy || compositing}
            title="Render high-DPI full-page composite preview"
          >
            <Eye size={14} />
            {compositing ? 'Rendering...' : 'Composite'}
          </button>

          <button
            type="button"
            className="editor-export bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3 py-1.5 rounded flex items-center gap-1.5 text-xs transition-colors motion-interactive shadow-sm"
            onClick={() => void handleExportComic()}
            disabled={busy || exporting}
            title="Export high-resolution print-ready PDF comic book"
          >
            <Download size={14} />
            {exporting ? 'Exporting...' : 'Export PDF'}
          </button>

          <button title="Close editor" aria-label="Close editor" onClick={handleCloseEditor}>
            <X />
          </button>
        </div>
      </header>

      <div className="editor-workspace">
        <aside className="editor-tools">
          <button
            className={!selectedLayer ? 'active' : ''}
            title="Select tool"
            aria-label="Select tool"
            onClick={() => {
              setSelectedId(null);
              setSelectedVertex(null);
            }}
          >
            <Hand />
          </button>
          <button
            title="Add Speech Bubble (Classic Oval)"
            aria-label="Add Speech Bubble"
            onClick={() => addBubblePreset('oval', 'smooth_pointer', 'Spoken dialogue...')}
            disabled={!selectedPanel}
          >
            <MessageSquare />
          </button>
          <button
            title="Add Thought Cloud"
            aria-label="Add Thought Cloud"
            onClick={() => addBubblePreset('thought_cloud', 'bubble_chain', 'Inner monologue...')}
            disabled={!selectedPanel}
          >
            <Cloud />
          </button>
          <button
            title="Add Action Shout (Starburst + Halftone Shadow)"
            aria-label="Add Action Shout"
            onClick={() => addBubblePreset('shout_burst', 'lightning_bolt', 'SHOUT!', { halftone: true })}
            disabled={!selectedPanel}
          >
            <Zap />
          </button>
          <button
            title="Add Narration Banner"
            aria-label="Add Narration Banner"
            onClick={() => addBubblePreset('tilted_banner', 'none', 'Meanwhile...', { halftone: true })}
            disabled={!selectedPanel}
          >
            <Bookmark />
          </button>
          <button
            title="Add 3D Parchment Ribbon Banner"
            aria-label="Add 3D Parchment Ribbon Banner"
            onClick={() => addBubblePreset('folded_ribbon_3d', 'none', 'ACT I: RECKONING', { halftone: true })}
            disabled={!selectedPanel}
          >
            <Scroll />
          </button>
          <button
            title="Add Radio Broadcast Comms"
            aria-label="Add Radio Broadcast Comms"
            onClick={() => addBubblePreset('radio_broadcast_zigzag', 'zigzag_antenna', 'DISPATCH: STATUS REPORT!', { halftone: true, accent: 'electric_sparks' })}
            disabled={!selectedPanel}
          >
            <Radio />
          </button>
          <button
            title="Add Dark Aura (Villain / Inverted Speech)"
            aria-label="Add Dark Aura (Villain / Inverted Speech)"
            onClick={() => addBubblePreset('dark_aura_ghost', 'smooth_pointer', 'Your time is over...', { halftone: true, inverted: true })}
            disabled={!selectedPanel}
          >
            <Flame />
          </button>
          <button
            title="Browse 50 speech bubble presets"
            aria-label="Browse bubble presets"
            onClick={() => setShowBubblePicker(true)}
            disabled={!selectedPanel}
          >
            <Sparkles />
          </button>
          <hr />
          <button
            title="Add custom text"
            aria-label="Add custom text"
            onClick={addTextLayer}
            disabled={!selectedPanel}
          >
            <Type />
          </button>
          <button
            title="Add line"
            aria-label="Add line"
            onClick={addLineLayer}
            disabled={!selectedPanel}
          >
            <PenLine />
          </button>
          <button title="Validate geometry" aria-label="Validate geometry" onClick={() => void validate()}>
            <CircleAlert />
          </button>
          <button title="Return to page list" aria-label="Return to page list" onClick={handleCloseEditor}>
            <ArrowDownToLine />
          </button>
          <input
            ref={fontInputRef}
            type="file"
            accept=".ttf,.otf,.woff,.woff2"
            hidden
            onChange={(event) => void uploadFont(event.target.files?.[0])}
          />
        </aside>

        <div className="editor-canvas-wrap" style={{ position: 'relative' }}>
          {/* Floating Transform HUD Toolbar (Figma/Canva Pro Style) */}
          {selectedLayer && (
            <div className="editor-hud-toolbar">
              {/* Direct In-Panel Action HUD */}
              {selectedPanel && (
                <div className="hud-group">
                  <button
                    type="button"
                    onClick={() => {
                      setInPanelGenOpen(true);
                      setPanelGenPrompt('');
                    }}
                    className="hud-btn-primary"
                    title="Draw artwork for this panel using AI Agent"
                  >
                    <Sparkles size={13} className="shrink-0" />
                    <span>Draw with Agent</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setImagePickerOpen(true)}
                    className="hud-btn-secondary"
                    title={selectedPanelImage ? 'Change or replace the image in this panel' : 'Select an image from library to place into this panel'}
                  >
                    <ImagePlus size={13} className="shrink-0" />
                    <span>{selectedPanelImage ? 'Change Image' : '+ Place Image'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => addBubblePreset('oval', 'none', 'New dialogue...')}
                    className="hud-btn-secondary"
                    title="Add speech bubble to panel"
                  >
                    <MessageSquare size={13} className="shrink-0" />
                    <span>+ Bubble</span>
                  </button>
                </div>
              )}

              {selectedImage && (
                imageEditLayerId === selectedImage.layer_id ? (
                  <div className="hud-group image-edit-mode-indicator">
                    <span>{imageEditReady ? 'Editing full image bounds' : imageBoundsErrorFor === selectedImage.source_asset_id ? 'Image bounds unavailable' : 'Loading image bounds…'}</span>
                    <button type="button" onClick={() => setImageEditLayerId(null)} title="Finish image editing">
                      Done
                    </button>
                  </div>
                ) : (
                  <div className="hud-group">
                    <button
                      type="button"
                      onClick={() => setImagePickerOpen(true)}
                      className="hud-btn-secondary"
                      title="Choose a different image from library or upload"
                    >
                      <ImagePlus size={13} className="shrink-0" />
                      <span>Change Image</span>
                    </button>
                    <span className="image-edit-mode-hint" title="Double-click the image to reveal and adjust its full source bounds">
                      Double-click to edit bounds
                    </span>
                  </div>
                )
              )}

              {/* Scale Controls */}
              <div className="hud-group">
                <span className="hud-label">Scale</span>
                <button type="button" onClick={() => stepScale(-0.1)} disabled={!!selectedImage && !imageEditReady} title="Scale Down (-10%)">
                  <Minus size={13} />
                </button>
                <span className="hud-value">{Math.round(currentScale * 100)}%</span>
                {selectedImage && (
                  <input
                    className="hud-scale-slider"
                    type="range"
                    min="0.05"
                    max="10"
                    step="0.05"
                    value={currentScale}
                    aria-label="Scale full image"
                    title="Scale the full source image; the panel mask stays fixed"
                    disabled={!imageEditReady}
                    onChange={(event) => setScale(Number(event.currentTarget.value))}
                  />
                )}
                <button type="button" onClick={() => stepScale(0.1)} disabled={!!selectedImage && !imageEditReady} title="Scale Up (+10%)">
                  <Plus size={13} />
                </button>
                <button type="button" onClick={() => setScale(1)} disabled={!!selectedImage && !imageEditReady} title="Reset Scale (100%)" className="hud-reset">
                  1:1
                </button>
              </div>

              {/* Rotation Controls */}
              <div className="hud-group">
                <span className="hud-label">Rotate</span>
                <button type="button" onClick={() => stepRotate(-15)} disabled={!!selectedImage && !imageEditReady} title="Rotate -15°">
                  <RotateCcw size={13} />
                </button>
                <span className="hud-value">{Math.round(currentRotation)}°</span>
                <button type="button" onClick={() => stepRotate(15)} disabled={!!selectedImage && !imageEditReady} title="Rotate +15°">
                  <RotateCw size={13} />
                </button>
                <button type="button" onClick={() => stepRotate(90)} disabled={!!selectedImage && !imageEditReady} title="Rotate +90°">
                  90°
                </button>
                <button type="button" onClick={() => setRotation(0)} disabled={!!selectedImage && !imageEditReady} title="Reset Rotation (0°)" className="hud-reset">
                  0°
                </button>
              </div>

              {/* Mirror Controls */}
              <div className="hud-group">
                <span className="hud-label">Mirror</span>
                <button
                  type="button"
                  onClick={toggleFlipH}
                  disabled={!!selectedImage && !imageEditReady}
                  className={currentFlipH ? 'active' : ''}
                  title="Flip Horizontal (H)"
                >
                  <FlipHorizontal size={14} />
                </button>
                <button
                  type="button"
                  onClick={toggleFlipV}
                  disabled={!!selectedImage && !imageEditReady}
                  className={currentFlipV ? 'active' : ''}
                  title="Flip Vertical (V)"
                >
                  <FlipVertical size={14} />
                </button>
              </div>

              {/* Fit / Crop (for images) */}
              {selectedImage && (
                <div className="hud-group">
                  <button
                    type="button"
                    onClick={toggleFitMode}
                    disabled={!imageEditReady}
                    className={selectedImage.fit_mode === 'contain' ? 'active' : ''}
                    title={`Crop / Fit mode: ${selectedImage.fit_mode} (Hotkey: C)`}
                  >
                    <Crop size={14} />
                    <span style={{ fontSize: '10px', textTransform: 'capitalize' }}>{selectedImage.fit_mode}</span>
                  </button>
                </div>
              )}

              {/* Center in Panel */}
              {selectedPanel && (
                <div className="hud-group">
                  <button type="button" onClick={centerInPanel} disabled={!!selectedImage && !imageEditReady} title="Center in Panel">
                    <AlignCenter size={14} />
                    <span>Center</span>
                  </button>
                </div>
              )}

              {/* Clipboard & Duplication */}
              <div className="hud-group">
                <button type="button" onClick={copySelected} title="Copy Element (Ctrl+C)">
                  <Copy size={13} />
                </button>
                <button
                  type="button"
                  onClick={pasteClipboard}
                  title="Paste Element (Ctrl+V)"
                  disabled={!clipboardRef.current && !localStorage.getItem('inkloop_editor_clipboard')}
                >
                  <ClipboardPaste size={13} />
                </button>
                <button type="button" onClick={duplicateSelected} title="Duplicate In-Place (Ctrl+D)">
                  <Layers size={13} />
                </button>
                <button type="button" onClick={deleteSelected} title="Delete Element (Del)" className="hud-danger">
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          )}

          {/* In-Panel Direct Generation Modal */}
          {inPanelGenOpen && selectedPanel && (
            <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
              <div className="w-full max-w-lg bg-[#181818] border border-white/15 rounded-2xl p-6 shadow-2xl space-y-4 text-left">
                <div className="flex items-center justify-between pb-3 border-b border-white/10">
                  <div className="flex items-center gap-2.5">
                    <TabCharacterIcon tab="editor" size={32} />
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        Draw Panel Artwork
                        <span className="px-2 py-0.5 rounded-full bg-white/10 text-[11px] font-mono text-zinc-300">
                          {selectedPanel.panel_id}
                        </span>
                      </h3>
                      <p className="text-[11px] text-zinc-400">
                        Choose the cast and style for this panel. Matching uses the selected reference images.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => !panelGenLoading && setInPanelGenOpen(false)}
                    className="text-zinc-400 hover:text-white transition p-1"
                    disabled={panelGenLoading}
                  >
                    <X size={18} />
                  </button>
                </div>

                {panelGenLoading ? (
                  <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
                    <TabCharacterIcon tab="editor" active size={64} />
                    <div className="space-y-1">
                      <div className="text-sm font-semibold text-white animate-pulse">
                        {panelGenStage || 'InkLoop Agent Generating Panel Artwork...'}
                      </div>
                      <p className="text-xs text-zinc-400 font-mono">
                        Waiting for the configured image provider. Verification is only shown if it actually runs.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-white flex items-center justify-between">
                        <span>Scene & Action Description:</span>
                        <span className="text-[10px] text-zinc-400">No text or bubbles in prompt (D6)</span>
                      </label>
                      <textarea
                        rows={3}
                        value={panelGenPrompt}
                        onChange={(e) => setPanelGenPrompt(e.target.value)}
                        placeholder="e.g. Sara draws her blade against the moonlight, rain dripping from her bangs, dramatic low angle..."
                        className="w-full p-3 rounded-xl bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/30 resize-none font-sans"
                      />
                      {/* Quick Prompt Starters */}
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {[
                          'Heroic standoff with drawn weapon',
                          'Quiet introspective rain scene',
                          'Kinetic action slash with motion lines',
                          'Shocked facial expression close-up',
                        ].map((starter) => (
                          <button
                            key={starter}
                            type="button"
                            onClick={() => setPanelGenPrompt(starter)}
                            className="px-2 py-0.5 rounded-md bg-white/5 hover:bg-white/10 text-[10px] text-zinc-300 transition"
                          >
                            + {starter}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-1">
                      <div className="space-y-1">
                        <label className="text-[11px] font-medium text-zinc-300">Cast in Panel:</label>
                        <div className="flex items-center gap-1.5">
                          {projectCharacters.map(({ id: cid, name }) => {
                            const active = panelGenCharacters.includes(cid);
                            return (
                              <button
                                key={cid}
                                type="button"
                                onClick={() =>
                                  setPanelGenCharacters((prev) =>
                                    active ? prev.filter((c) => c !== cid) : [...prev, cid]
                                  )
                                }
                                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                                  active
                                    ? 'bg-white text-black font-semibold'
                                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                                }`}
                              >
                                {active ? `✓ ${name}` : `+ ${name}`}
                              </button>
                            );
                          })}
                        </div>
                        {panelGenCharacters.length === 0 && (
                          <p className="text-[10px] text-zinc-500">
                            No cast selected. Exact canon names in the prompt may be resolved; other characters stay unlinked.
                          </p>
                        )}
                      </div>

                      <div className="space-y-1">
                        <label className="text-[11px] font-medium text-zinc-300">Camera Framing:</label>
                        <select
                          value={panelGenCamera}
                          onChange={(e) => setPanelGenCamera(e.target.value)}
                          className="w-full p-1.5 rounded-lg bg-zinc-900 border border-white/10 text-xs text-white focus:outline-none focus:border-white/30"
                        >
                          <option value="medium shot, dynamic angle">Medium Shot (Dynamic)</option>
                          <option value="close-up dramatic portrait">Close-up Dramatic</option>
                          <option value="wide panoramic establishing">Wide Establishing</option>
                          <option value="low angle heroic shot">Low Angle Heroic</option>
                          <option value="high angle bird's eye view">Bird's Eye Overlook</option>
                        </select>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-medium text-zinc-300" htmlFor="panel-generation-style">
                        Art style:
                      </label>
                      <select
                        id="panel-generation-style"
                        value={panelGenStyleId}
                        onChange={(e) => setPanelGenStyleId(e.target.value)}
                        className="w-full p-2 rounded-lg bg-zinc-900 border border-white/10 text-xs text-white focus:outline-none focus:border-white/30"
                      >
                        <option value="">Use this project’s Story Bible style</option>
                        {projectStyles.map((style) => (
                          <option key={style.profile_id} value={style.profile_id}>
                            {style.name} · v{style.version}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="pt-3 border-t border-white/10 flex items-center justify-between">
                      <div className="text-[11px] text-zinc-400">
                        Character and style matching are best effort; verification only runs when enabled.
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setInPanelGenOpen(false)}
                          className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-white transition"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleInPanelGenerate()}
                          disabled={!panelGenPrompt.trim()}
                          className="px-4 py-1.5 rounded-lg bg-white hover:bg-zinc-200 text-black font-semibold text-xs transition shadow-md flex items-center gap-1.5 disabled:opacity-40"
                        >
                          <Sparkles size={14} />
                          <span>Generate panel art</span>
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Asset / Image Picker Modal */}
          {imagePickerOpen && selectedPanel && (
            <div
              className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in"
              role="dialog"
              aria-modal="true"
              aria-labelledby="image-picker-title"
              onClick={(e) => {
                if (e.target === e.currentTarget) setImagePickerOpen(false);
              }}
            >
              <div className="w-full max-w-3xl max-h-[85vh] bg-[#161616] border border-white/15 rounded-2xl shadow-2xl flex flex-col text-left overflow-hidden">
                {/* Modal Header */}
                <div className="p-5 border-b border-white/10 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-white/10 border border-white/10 flex items-center justify-center text-white">
                      <ImagePlus size={18} />
                    </div>
                    <div>
                      <h3 id="image-picker-title" className="text-sm font-bold text-white flex items-center gap-2">
                        <span>{selectedPanelImage ? 'Change Image' : 'Select Image'}</span>
                        <span className="text-zinc-500 font-mono text-xs">· Panel {selectedPanel.panel_id}</span>
                      </h3>
                      <p className="text-xs text-zinc-400 mt-0.5">
                        Choose artwork from your project library or upload directly into this panel.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setImagePickerOpen(false)}
                    className="text-zinc-400 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>

                {/* Filter and Upload Bar */}
                <div className="px-5 py-3 border-b border-white/5 bg-zinc-900/60 flex flex-wrap items-center justify-between gap-3 shrink-0">
                  <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                    <div className="relative flex-1">
                      <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
                      <input
                        type="text"
                        value={imagePickerQuery}
                        onChange={(e) => setImagePickerQuery(e.target.value)}
                        placeholder="Search images by name or ID…"
                        className="w-full pl-9 pr-8 py-1.5 rounded-lg bg-zinc-950 border border-white/10 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white/30"
                      />
                      {imagePickerQuery && (
                        <button
                          type="button"
                          onClick={() => setImagePickerQuery('')}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white cursor-pointer"
                        >
                          <X size={12} />
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-1 bg-zinc-950 p-0.5 rounded-lg border border-white/10 text-xs">
                      {(['all', 'panel', 'character'] as const).map((filter) => (
                        <button
                          key={filter}
                          type="button"
                          onClick={() => setImagePickerFilter(filter)}
                          className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition capitalize cursor-pointer ${
                            imagePickerFilter === filter
                              ? 'bg-white/15 text-white'
                              : 'text-zinc-400 hover:text-white'
                          }`}
                        >
                          {filter === 'all' ? 'All Images' : filter === 'panel' ? 'Panels' : 'Characters'}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Upload Input & Button */}
                  <input
                    type="file"
                    ref={imageUploadInputRef}
                    accept="image/*"
                    className="hidden"
                    onChange={handleUploadAndPlaceImage}
                  />
                  <button
                    type="button"
                    disabled={uploadingImage}
                    onClick={() => imageUploadInputRef.current?.click()}
                    className="px-3.5 py-1.5 rounded-lg bg-white text-black hover:bg-zinc-200 text-xs font-semibold flex items-center gap-1.5 transition shadow-sm cursor-pointer disabled:opacity-50"
                  >
                    <Upload size={13} />
                    <span>{uploadingImage ? 'Uploading…' : 'Upload New Image'}</span>
                  </button>
                </div>

                {/* Asset Grid */}
                <div className="flex-1 overflow-y-auto p-5">
                  {filteredAssets.length === 0 ? (
                    <div className="py-12 text-center space-y-3">
                      <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mx-auto text-zinc-400">
                        <ImageIcon size={22} />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">No matching images found</p>
                        <p className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
                          {imagePickerQuery
                            ? 'Try adjusting your search query or filter.'
                            : 'No image assets are registered in this project yet. Click Upload New Image to add one.'}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => imageUploadInputRef.current?.click()}
                        className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-medium inline-flex items-center gap-2 transition cursor-pointer"
                      >
                        <Upload size={13} /> Upload Image from Disk
                      </button>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3.5">
                      {filteredAssets.map((asset) => {
                        const isCurrent = selectedPanelImage?.source_asset_id === asset.asset_id;
                        return (
                          <div
                            key={asset.asset_id}
                            onClick={() => placeOrReplaceImage(asset, selectedPanel.panel_id)}
                            className={`group relative rounded-xl border p-2 bg-zinc-900/80 hover:bg-zinc-800 transition cursor-pointer flex flex-col justify-between ${
                              isCurrent
                                ? 'border-blue-500 ring-2 ring-blue-500/20'
                                : 'border-white/10 hover:border-white/30'
                            }`}
                          >
                            <div className="aspect-[4/3] rounded-lg bg-black/60 overflow-hidden relative mb-2 flex items-center justify-center border border-white/5">
                              <img
                                src={apiClient.getAssetFileUrl(asset.asset_id)}
                                alt={asset.name || asset.original_filename}
                                loading="lazy"
                                className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                              />
                              {isCurrent && (
                                <span className="absolute top-1.5 right-1.5 px-1.5 py-0.5 rounded bg-blue-600 text-white text-[9px] font-bold shadow">
                                  Current
                                </span>
                              )}
                              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                <span className="px-2.5 py-1 rounded-lg bg-white text-black text-xs font-bold shadow-lg flex items-center gap-1">
                                  <Check size={12} /> {isCurrent ? 'Current' : 'Select'}
                                </span>
                              </div>
                            </div>

                            <div className="space-y-0.5">
                              <p className="text-xs font-medium text-white truncate" title={asset.name || asset.original_filename}>
                                {asset.name || asset.original_filename}
                              </p>
                              <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono">
                                <span>{asset.width && asset.height ? `${asset.width}×${asset.height}` : 'Asset'}</span>
                                <span className="truncate max-w-[80px]">{asset.asset_id.slice(0, 10)}…</span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Modal Footer */}
                <div className="p-4 border-t border-white/10 bg-zinc-900/40 flex items-center justify-between shrink-0 text-xs">
                  <span className="text-zinc-400 text-[11px]">
                    Showing {filteredAssets.length} image{filteredAssets.length === 1 ? '' : 's'} in project
                  </span>
                  <button
                    type="button"
                    onClick={() => setImagePickerOpen(false)}
                    className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white transition font-medium cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}

          <div
            className="editor-canvas-scroll"
            ref={canvasScrollRef}
            onPointerDown={(event) => {
              if (event.target === event.currentTarget) {
                setSelectedId(null);
                setSelectedVertex(null);
                setImageEditLayerId(null);
              }
            }}
          >
            <svg
              ref={svgRef}
              className="editor-svg canvas-raw-manipulation"
              viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
              style={{ width: `${82 * zoom}%` }}
              onPointerDown={(event) => {
                const target = event.target as SVGElement;
                if (event.target === event.currentTarget || target.dataset.canvasBackground === 'true') {
                  setSelectedId(null);
                  setSelectedVertex(null);
                  setImageEditLayerId(null);
                }
              }}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerUp}
            >
              <defs>
                <pattern
                  id="manga-halftone-pattern"
                  width="8"
                  height="8"
                  patternUnits="userSpaceOnUse"
                  patternTransform="rotate(45)"
                >
                  <circle cx="2" cy="2" r="1.8" fill="#111111" opacity="0.4" />
                  <circle cx="6" cy="6" r="1.8" fill="#111111" opacity="0.4" />
                </pattern>
                {page.layout.panel_slots.map((panel: any) => (
                  <clipPath id={`clip-${panel.panel_id}`} key={panel.panel_id}>
                    {panel.polygon?.length ? (
                      <polygon points={panel.polygon.map((p: Point) => `${p.x},${p.y}`).join(' ')} />
                    ) : (
                      <rect x={panel.rect.x} y={panel.rect.y} width={panel.rect.width} height={panel.rect.height} />
                    )}
                  </clipPath>
                ))}
              </defs>

              <rect data-canvas-background="true" data-testid="canvas-background" width={canvasWidth} height={canvasHeight} fill="#fff" />

              {showGuides && (
                <rect
                  x={page.layout.safe_area_box.x}
                  y={page.layout.safe_area_box.y}
                  width={page.layout.safe_area_box.width}
                  height={page.layout.safe_area_box.height}
                  fill="none"
                  stroke="#aaa"
                  strokeDasharray="8 8"
                  vectorEffect="non-scaling-stroke"
                />
              )}

              {/* Panels and Placed Artwork */}
              {(imageEditing && selectedPanel
                ? [...page.layout.panel_slots.filter((item: any) => item.panel_id !== selectedPanel.panel_id), ...page.layout.panel_slots.filter((item: any) => item.panel_id === selectedPanel.panel_id)]
                : page.layout.panel_slots).map((panel: any) => {
                const panelLayer = page.layers.find((l) => l.kind === 'panel' && l.panel_id === panel.panel_id);
                const image = page.layers.find((l) => l.kind === 'image' && l.panel_id === panel.panel_id && l.visible);
                const transform = image?.transform || {
                  scale_x: 1,
                  scale_y: 1,
                  translate_x: 0,
                  translate_y: 0,
                  rotation_deg: 0,
                  anchor_x: 0.5,
                  anchor_y: 0.5,
                };
                const shape = panel.polygon?.length ? (
                  <polygon points={panel.polygon.map((p: Point) => `${p.x},${p.y}`).join(' ')} />
                ) : (
                  <rect x={panel.rect.x} y={panel.rect.y} width={panel.rect.width} height={panel.rect.height} />
                );

                const isPanelSelected = selectedId === panelLayer?.layer_id;
                const isImageSelected = selectedId === image?.layer_id;
                const isPanelOrArtworkSelected = isPanelSelected || isImageSelected;
                const previewUrl = image ? imagePreviews[image.layer_id] : undefined;
                const editingThisImage = !!image && imageEditLayerId === image.layer_id;
                const sourceUrl = image?.source_asset_id ? apiClient.getAssetFileUrl(image.source_asset_id) : '';
                const sourceDimensions = image ? dimensionsForImageLayer(image) : null;
                const bounds = image && sourceDimensions
                  ? imageEditBounds(panel.rect, image.fit_mode, sourceDimensions, transform)
                  : null;
                const showMaskedPreview = !!previewUrl && !editingThisImage;
                const panelCenterX = panel.rect.x + panel.rect.width / 2;
                const panelCenterY = panel.rect.y + panel.rect.height / 2;
                const fallbackWidth = panel.rect.width * Math.abs(transform.scale_x || 1);
                const fallbackHeight = panel.rect.height * Math.abs(transform.scale_y || 1);
                const imageWidth = showMaskedPreview ? panel.rect.width : bounds?.width || fallbackWidth;
                const imageHeight = showMaskedPreview ? panel.rect.height : bounds?.height || fallbackHeight;
                const imageCenterX = showMaskedPreview ? panelCenterX : bounds?.centerX ?? panelCenterX + (transform.translate_x || 0);
                const imageCenterY = showMaskedPreview ? panelCenterY : bounds?.centerY ?? panelCenterY + (transform.translate_y || 0);
                const imageX = showMaskedPreview ? panel.rect.x : bounds?.x ?? imageCenterX - imageWidth / 2;
                const imageY = showMaskedPreview ? panel.rect.y : bounds?.y ?? imageCenterY - imageHeight / 2;
                const imageRotation = showMaskedPreview ? 0 : (transform.rotation_deg || 0);
                const flipH = Boolean(image?.metadata?.flip_h);
                const flipV = Boolean(image?.metadata?.flip_v);
                const imageTransform = imageRotation !== 0 || flipH || flipV
                  ? `translate(${imageCenterX}, ${imageCenterY}) rotate(${imageRotation}) scale(${flipH ? -1 : 1}, ${flipV ? -1 : 1}) translate(${-imageCenterX}, ${-imageCenterY})`
                  : undefined;
                const imageHref = showMaskedPreview ? previewUrl! : sourceUrl;
                const imageNode = (
                  <image
                    href={imageHref}
                    x={imageX}
                    y={imageY}
                    width={imageWidth}
                    height={imageHeight}
                    transform={imageTransform}
                    preserveAspectRatio={showMaskedPreview ? 'none' : 'none'}
                  />
                );

                return (
                  <g key={panel.panel_id}>
                    {/* Source bounds stay editable; only the final artwork copy is panel-clipped. */}
                    {image && (
                      <g
                        data-testid={`panel-artwork-${panel.panel_id}`}
                        data-image-edit-mode={imageEditLayerId === image.layer_id ? 'enabled' : 'disabled'}
                        data-image-bounds-ready={sourceDimensions ? 'true' : 'false'}
                        data-image-source-width={sourceDimensions?.width || ''}
                        data-image-source-height={sourceDimensions?.height || ''}
                        data-image-scale={transform.scale_x ?? 1}
                        data-image-rotation={transform.rotation_deg ?? 0}
                        data-image-translate-x={transform.translate_x ?? 0}
                        data-image-translate-y={transform.translate_y ?? 0}
                        onPointerDown={(event) => onPointerDownLayer(event, image.layer_id, 'image')}
                        onDoubleClick={(event) => {
                          event.stopPropagation();
                          setSelectedId(image.layer_id);
                          setImageEditLayerId(image.layer_id);
                          setSuccessMsg('Image editing enabled. Drag the artwork or use the scale and rotate controls; the panel mask stays fixed.');
                        }}
                        style={{ cursor: imageEditLayerId === image.layer_id ? 'move' : 'pointer' }}
                      >
                        {editingThisImage && bounds && (
                          <g data-testid={`image-overscan-ghost-${panel.panel_id}`} opacity="0.28">
                            {imageNode}
                          </g>
                        )}
                        <g clipPath={`url(#clip-${panel.panel_id})`} data-testid={`panel-artwork-mask-${panel.panel_id}`}>
                          {imageNode}
                        </g>
                      </g>
                    )}

                    {/* Panel Border Outline */}
                    <g
                      className={`editor-panel ${isPanelSelected ? 'selected' : ''}`}
                      onPointerDown={(event) => panelLayer && onPointerDownLayer(event, panelLayer.layer_id, 'panel')}
                      onClick={() => panelLayer && setSelectedId(panelLayer.layer_id)}
                    >
                      {React.cloneElement(shape, {
                        'data-testid': `panel-outline-${panel.panel_id}`,
                        className: 'editor-panel-hit-shape',
                        // The panel overlay is drawn above its artwork. With a
                        // painted transparent fill, it captures the whole panel
                        // and blocks image selection/double-click. Hit-test only
                        // the frame when artwork fills the panel.
                        pointerEvents: image ? 'stroke' : 'visiblePainted',
                        fill: image ? 'transparent' : '#f7f7f7',
                        stroke: '#171717',
                        strokeWidth: isPanelSelected ? 2.5 : 1.4,
                        vectorEffect: 'non-scaling-stroke',
                      } as any)}
                      <text x={panel.rect.x + 10} y={panel.rect.y + 20} className="editor-panel-label">
                        {panel.panel_id} · {panel.reading_order}
                      </text>
                    </g>

                    {/* Non-interactive selection ring: artwork selection follows its fixed panel mask. */}
                    {isPanelOrArtworkSelected && (
                      <g
                        data-testid={`editor-selection-highlight-${panel.panel_id}`}
                        data-selection-kind={isImageSelected ? 'image' : 'panel'}
                        pointerEvents="none"
                        aria-hidden="true"
                      >
                        {React.cloneElement(shape, {
                          fill: 'none',
                          stroke: '#ffffff',
                          strokeWidth: 7,
                          vectorEffect: 'non-scaling-stroke',
                          pointerEvents: 'none',
                        } as any)}
                        {React.cloneElement(shape, {
                          fill: 'none',
                          stroke: '#2563eb',
                          strokeWidth: 3,
                          vectorEffect: 'non-scaling-stroke',
                          pointerEvents: 'none',
                        } as any)}
                      </g>
                    )}

                    {/* Vertex Draggable Handles */}
                    {selectedPanel?.panel_id === panel.panel_id &&
                      selectedLayer?.kind === 'panel' &&
                      (panel.polygon || points).map((point: Point, index: number) => (
                        <circle
                          key={index}
                          className={`editor-vertex ${selectedVertex === index ? 'active' : ''}`}
                          cx={point.x}
                          cy={point.y}
                          r={6 / zoom}
                          onPointerDown={(event) => onPointerDownVertex(event, selectedLayer.layer_id, index)}
                        />
                      ))}
                  </g>
                );
              })}

              {/* Text and Line Vector Layers */}
              {page.layers
                .filter((layer) => layer.visible && (layer.kind === 'text' || layer.kind === 'line'))
                .sort((a, b) => a.z_index - b.z_index)
                .map((layer) => {
                  const m = layer.metadata as Record<string, any>;
                  const isText = layer.kind === 'text';
                  const isSelected = selectedId === layer.layer_id;

                  if (isText) {
                    return (
                      <g
                        key={layer.layer_id}
                        data-testid={`editor-layer-${layer.layer_id}`}
                        className={`editor-vector-layer ${isSelected ? 'selected' : ''}`}
                        onPointerDown={(event) => onPointerDownLayer(event, layer.layer_id, 'text')}
                      >
                        <SpeechBubbleSvg
                          layer={layer}
                          isSelected={isSelected}
                          zoom={zoom}
                          onPointerDownTailHandle={onPointerDownTailHandle}
                        />
                      </g>
                    );
                  }

                  return (
                    <g
                      key={layer.layer_id}
                      className={`editor-vector-layer ${isSelected ? 'selected' : ''}`}
                      onPointerDown={(event) => onPointerDownLayer(event, layer.layer_id, 'line')}
                    >
                      <line
                        x1={Number(m.x1 || 0)}
                        y1={Number(m.y1 || 0)}
                        x2={Number(m.x2 || 0)}
                        y2={Number(m.y2 || 0)}
                        stroke={String(m.color || '#111')}
                        strokeWidth={Number(m.stroke_width || 3)}
                        strokeDasharray={String(m.dash || '') || undefined}
                        strokeLinecap="round"
                      />
                    </g>
                  );
                })}

              {/* Interactive Transform Gizmo (Corner Scales, Top Rotation Stem, Move) */}
              {selectedImage && selectedPanel && imageEditReady && selectedImageDimensions && (() => {
                const imgTransform = selectedImage.transform || { scale_x: 1, scale_y: 1, translate_x: 0, translate_y: 0, rotation_deg: 0, anchor_x: 0.5, anchor_y: 0.5 };
                const bounds = imageEditBounds(selectedPanel.rect, selectedImage.fit_mode, selectedImageDimensions, imgTransform);
                return (
                  <TransformGizmo
                    x={bounds.x}
                    y={bounds.y}
                    width={bounds.width}
                    height={bounds.height}
                    rotationDeg={imgTransform.rotation_deg || 0}
                    scaleX={Math.abs(imgTransform.scale_x || 1)}
                    scaleY={Math.abs(imgTransform.scale_y || 1)}
                    zoom={zoom}
                    flipH={Boolean(selectedImage.metadata?.flip_h)}
                    flipV={Boolean(selectedImage.metadata?.flip_v)}
                    disableBodyDrag
                    toDocPoint={toDoc}
                    onTranslate={handleGizmoTranslate}
                    onScale={handleGizmoScale}
                    onRotate={handleGizmoRotate}
                  />
                );
              })()}

              {selectedText && (() => {
                const textX = Number(selectedText.metadata.x || 0);
                const textY = Number(selectedText.metadata.y || 0);
                const textW = Math.max(40, Number(selectedText.metadata.width || 240));
                const textH = Math.max(30, Number(selectedText.metadata.height || 140));
                return (
                  <TransformGizmo
                    x={textX}
                    y={textY}
                    width={textW}
                    height={textH}
                    rotationDeg={Number(selectedText.metadata.rotation_deg || 0)}
                    scaleX={Number(selectedText.metadata.scale_factor || 1)}
                    scaleY={Number(selectedText.metadata.scale_factor || 1)}
                    zoom={zoom}
                    flipH={Boolean(selectedText.metadata.flip_h)}
                    flipV={Boolean(selectedText.metadata.flip_v)}
                    toDocPoint={toDoc}
                    onTranslate={handleGizmoTranslate}
                    onScale={handleGizmoScale}
                    onRotate={handleGizmoRotate}
                  />
                );
              })()}
            </svg>
          </div>

          <div className="editor-canvas-footer">
            <span>Document coordinates · px</span>
            <span>Reading {page.layout.reading_direction?.toUpperCase()}</span>
            <button onClick={() => void validate()}>Check geometry</button>
          </div>
        </div>

        {/* Properties & Layer Inspector */}
        <aside className="editor-inspector">
          <section>
            <div className="editor-section-title">
              <strong>Layers</strong>
              <span>{page.layers.length}</span>
            </div>
            <div className="editor-layer-list">
              {page.layers
                .slice()
                .sort((a, b) => b.z_index - a.z_index)
                .map((layer) => (
                  <button
                    key={layer.layer_id}
                    className={`editor-layer ${selectedId === layer.layer_id ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedId(layer.layer_id);
                      setSelectedVertex(null);
                    }}
                  >
                    <span className="layer-kind">
                      {layer.kind === 'image' ? (
                        <ImagePlus />
                      ) : layer.kind === 'text' ? (
                        <Type />
                      ) : layer.kind === 'line' ? (
                        <PenLine />
                      ) : (
                        <Layers3 />
                      )}
                    </span>
                    <span>
                      <b>{layer.label}</b>
                      <small>
                        {layer.kind === 'image'
                          ? `Image · ${layer.source_asset_id?.slice(0, 10)}...`
                          : layer.panel_id
                          ? `Panel ${layer.panel_id}`
                          : layer.kind}
                      </small>
                    </span>
                    <input
                      type="checkbox"
                      aria-label={`Show ${layer.label}`}
                      checked={layer.visible}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) =>
                        updateLayer(layer.layer_id, (item) => ({ ...item, visible: e.target.checked }))
                      }
                    />
                  </button>
                ))}
            </div>
          </section>

          <section>
            <div className="editor-section-title">
              <strong>Properties</strong>
            </div>

            {!selectedLayer ? (
              <p className="editor-muted">Select a panel or image layer on the canvas.</p>
            ) : selectedImage ? (
              <>
                <div className="editor-field" style={{ marginBottom: '12px' }}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-semibold text-zinc-300">Source Artwork</span>
                    <button
                      type="button"
                      onClick={() => setImagePickerOpen(true)}
                      className="px-2.5 py-1 rounded bg-white text-black hover:bg-zinc-200 text-xs font-semibold transition flex items-center gap-1.5 shadow-sm cursor-pointer"
                      title="Change or replace the image in this panel"
                    >
                      <ImagePlus size={12} /> Change Image
                    </button>
                  </div>
                  <div className="flex items-center gap-2.5 p-2 rounded-lg bg-zinc-900 border border-white/10">
                    <img
                      src={apiClient.getAssetFileUrl(selectedImage.source_asset_id || '')}
                      alt=""
                      className="w-12 h-12 object-cover rounded bg-black/50 shrink-0 border border-white/10"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-white font-medium truncate">{selectedImage.label}</p>
                      <code className="text-[10px] text-zinc-400 block truncate">{selectedImage.source_asset_id}</code>
                    </div>
                  </div>
                </div>

                <div className="editor-field-grid">
                  {(['translate_x', 'translate_y', 'rotation_deg'] as const).map((key) => (
                    <label className="editor-field" key={key}>
                      <span>{key.replace('_', ' ')}</span>
                      <input
                        type="number"
                        step="1"
                        value={selectedImage.transform?.[key] ?? 0}
                        onChange={(e) =>
                          updateLayer(selectedImage.layer_id, (item) => {
                            const cur = item.transform || {
                              scale_x: 1,
                              scale_y: 1,
                              translate_x: 0,
                              translate_y: 0,
                              rotation_deg: 0,
                              anchor_x: 0.5,
                              anchor_y: 0.5,
                            };
                            return {
                              ...item,
                              transform: {
                                ...cur,
                                [key]: Number(e.target.value),
                              },
                            };
                          })
                        }
                      />
                    </label>
                  ))}
                  <label className="editor-field">
                    <span>Uniform scale</span>
                    <input
                      type="number"
                      step="0.05"
                      min="0.05"
                      value={selectedImage.transform?.scale_x ?? 1}
                      onChange={(e) => {
                        const scale = Number(e.target.value);
                        updateLayer(selectedImage.layer_id, (item) => {
                          const cur = item.transform || {
                            scale_x: 1,
                            scale_y: 1,
                            translate_x: 0,
                            translate_y: 0,
                            rotation_deg: 0,
                            anchor_x: 0.5,
                            anchor_y: 0.5,
                          };
                          return {
                            ...item,
                            transform: {
                              ...cur,
                              scale_x: scale,
                              scale_y: scale,
                            },
                          };
                        });
                      }}
                    />
                  </label>
                </div>

                <label className="editor-field">
                  <span>Fit mode</span>
                  <select
                    value={selectedImage.fit_mode}
                    onChange={(e) =>
                      updateLayer(selectedImage.layer_id, (item) => ({
                        ...item,
                        fit_mode: e.target.value as 'cover' | 'contain',
                      }))
                    }
                  >
                    <option value="cover">Cover (Masked without stretch)</option>
                    <option value="contain">Contain (Full view inside frame)</option>
                  </select>
                </label>

                <div className="editor-field-grid" style={{ marginTop: '8px' }}>
                  <button
                    type="button"
                    className={`editor-vertex-tools button ${Boolean(selectedImage.metadata?.flip_h) ? 'border-blue-500 text-blue-400' : ''}`}
                    style={{ minHeight: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', background: '#252525' }}
                    onClick={toggleFlipH}
                  >
                    <FlipHorizontal size={13} /> {Boolean(selectedImage.metadata?.flip_h) ? 'Flipped H' : 'Flip H'}
                  </button>
                  <button
                    type="button"
                    className={`editor-vertex-tools button ${Boolean(selectedImage.metadata?.flip_v) ? 'border-blue-500 text-blue-400' : ''}`}
                    style={{ minHeight: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', background: '#252525' }}
                    onClick={toggleFlipV}
                  >
                    <FlipVertical size={13} /> {Boolean(selectedImage.metadata?.flip_v) ? 'Flipped V' : 'Flip V'}
                  </button>
                </div>

                <button
                  type="button"
                  style={{ width: '100%', minHeight: '30px', marginTop: '6px', marginBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', background: '#252525', border: '1px solid #3b3b3b', borderRadius: '5px', color: '#d0d0d0', fontSize: '10px' }}
                  onClick={centerInPanel}
                >
                  <AlignCenter size={13} /> Center in Panel
                </button>

                <button className="editor-danger" onClick={() => removeLayer(selectedImage.layer_id)}>
                  <Trash2 size={14} /> Remove image from panel
                </button>
              </>
            ) : selectedText ? (
              <>
                <label className="editor-field">
                  <span>Text Content</span>
                  <textarea
                    rows={4}
                    value={String(selectedText.metadata.text || '')}
                    onChange={(e) => updateMetadata(selectedText.layer_id, 'text', e.target.value)}
                  />
                </label>
                <label className="editor-field">
                  <span>Font asset</span>
                  <select
                    value={String(selectedText.metadata.font_asset_id || '')}
                    onChange={(e) => {
                      const font = assets.find((item) => item.asset_id === e.target.value);
                      updateLayer(selectedText.layer_id, (item) => ({
                        ...item,
                        metadata: {
                          ...item.metadata,
                          font_asset_id: font?.asset_id || '',
                          font_family: font?.name || item.metadata.font_family || 'sans-serif',
                        },
                      }));
                    }}
                  >
                    <option value="">Browser / System font</option>
                    {assets
                      .filter((asset) => asset.asset_type === 'font_file')
                      .map((font) => (
                        <option key={font.asset_id} value={font.asset_id}>
                          {font.name || font.original_filename}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="editor-field">
                  <span>Font family</span>
                    <select
                      value={String(selectedText.metadata.font_family || 'Comic Neue')}
                      onChange={(e) => updateMetadata(selectedText.layer_id, 'font_family', e.target.value)}
                    >
                      <option value="Comic Neue">Comic Neue · Dialogue</option>
                      <option value="Bangers">Bangers · Impact / SFX</option>
                      <option value="Noto Sans Arabic">Noto Sans Arabic</option>
                      <option value="Cairo">Cairo</option>
                      <option value="sans-serif">System sans-serif</option>
                    </select>
                </label>
                <div className="editor-field-grid">
                  {(['x', 'y', 'width', 'font_size'] as const).map((key) => (
                    <label className="editor-field" key={key}>
                      <span>{key.replace('_', ' ')}</span>
                      <input
                        type="number"
                        min={key === 'width' || key === 'font_size' ? 1 : undefined}
                        value={Number(selectedText.metadata[key] || 0)}
                        onChange={(e) => updateMetadata(selectedText.layer_id, key, Number(e.target.value))}
                      />
                    </label>
                  ))}
                </div>
                <div className="editor-field-grid">
                  <label className="editor-field">
                    <span>Weight</span>
                    <select
                      value={String(selectedText.metadata.font_weight || 'normal')}
                      onChange={(e) => updateMetadata(selectedText.layer_id, 'font_weight', e.target.value)}
                    >
                      <option value="normal">Normal</option>
                      <option value="bold">Bold</option>
                    </select>
                  </label>
                  <label className="editor-field">
                    <span>Color</span>
                    <input
                      type="color"
                      value={String(selectedText.metadata.color || '#111111')}
                      onChange={(e) => updateMetadata(selectedText.layer_id, 'color', e.target.value)}
                    />
                  </label>
                  <label className="editor-field">
                    <span>Alignment</span>
                    <select
                      value={String(selectedText.metadata.align || 'left')}
                      onChange={(e) => updateMetadata(selectedText.layer_id, 'align', e.target.value)}
                    >
                      <option value="left">Left</option>
                      <option value="center">Center</option>
                      <option value="right">Right</option>
                    </select>
                  </label>
                  <label className="editor-field">
                    <span>Direction</span>
                    <select
                      value={String(selectedText.metadata.direction || 'auto')}
                      onChange={(e) => updateMetadata(selectedText.layer_id, 'direction', e.target.value)}
                    >
                      <option value="auto">Auto</option>
                      <option value="ltr">LTR</option>
                      <option value="rtl">RTL</option>
                    </select>
                  </label>
                </div>

                <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #333' }}>
                  <div className="editor-section-title">
                    <strong style={{ fontSize: '11px', color: '#eee' }}>Speech & Emotion Bubble</strong>
                    <span style={{ fontSize: '9px', color: '#888' }}>Story-Driven</span>
                  </div>

                  <label className="editor-field">
                    <span>Who says this line?</span>
                    <select
                      value={String(selectedText.metadata.speaker_character_id || '')}
                      onChange={(e) => {
                        const character = projectCharacters.find((item) => item.id === e.target.value);
                        updateLayer(selectedText.layer_id, (item) => ({
                          ...item,
                          metadata: {
                            ...item.metadata,
                            speaker_character_id: character?.id || null,
                            speaker: character?.name || null,
                          },
                        }));
                      }}
                    >
                      <option value="">Narration / no speaker</option>
                      {projectCharacters.map((character) => <option key={character.id} value={character.id}>{character.name}</option>)}
                    </select>
                  </label>
                  <p className="text-[10px] text-zinc-500 mb-2">
                    Drag the blue tail handle to the speaker. InkLoop can reuse that confirmed position for this character in this panel.
                  </p>
                  {Array.isArray(selectedText.metadata.layout_warnings) && selectedText.metadata.layout_warnings.map((warning: any, index: number) => (
                    <p key={`${warning.code || 'warning'}-${index}`} className="mb-2 rounded border border-amber-500/20 bg-amber-500/5 px-2 py-1 text-[10px] text-amber-200">
                      {warning.message}
                    </p>
                  ))}

                  <label className="editor-field">
                    <span>Bubble Shape (22 Expressive Styles)</span>
                    <select
                      value={String(selectedText.metadata.bubble_shape || 'oval')}
                      onChange={(e) => {
                        const newShape = e.target.value;
                        updateMetadata(selectedText.layer_id, 'bubble_shape', newShape);
                        if (newShape === 'dark_aura_ghost' && !selectedText.metadata.inverted_dark_mode) {
                          updateMetadata(selectedText.layer_id, 'inverted_dark_mode', true);
                          updateMetadata(selectedText.layer_id, 'bubble_fill', '#111111');
                          updateMetadata(selectedText.layer_id, 'bubble_stroke', '#FFFFFF');
                          updateMetadata(selectedText.layer_id, 'color', '#FFFFFF');
                        }
                      }}
                    >
                      <optgroup label="Speech & Dialogue">
                        <option value="oval">Oval (Classic Dialogue)</option>
                        <option value="rounded_rectangle">Rounded Rect (Modern Dialogue)</option>
                        <option value="double_border_impact">Double Border Impact (Concentric Frame)</option>
                        <option value="scalloped_flower">Scalloped Flower (Delicate / Cute)</option>
                        <option value="heavy_weight_emphasis">Heavy Weight (Thick Rounded Pill)</option>
                        <option value="connected_lobes">Connected Lobes (Multi-Bubble Chain)</option>
                      </optgroup>
                      <optgroup label="Thought & Whisper">
                        <option value="thought_cloud">Thought Cloud (Inner Monologue)</option>
                        <option value="whisper_cloud_soft">Soft Whisper Cloud (Dashed Pillowy)</option>
                        <option value="droplet_tear_sad">Droplet Tear (Sadness / Weeping)</option>
                      </optgroup>
                      <optgroup label="Shout & Action">
                        <option value="shout_burst">Shout Burst (Angry / Shout Starburst)</option>
                        <option value="explosive_blast">Explosive Blast (Power / Impact Radiance)</option>
                        <option value="spiky_ring_scream">Spiky Ring Scream (360° Radiating Ring)</option>
                        <option value="radio_broadcast_zigzag">Radio Broadcast Zigzag (Walkie / Intercom)</option>
                        <option value="electric_robotic">Electric Robotic (AI / Tech Polygon)</option>
                        <option value="fear_tremble">Fear Tremble (Panic / Shivering Jitter)</option>
                        <option value="splat_surprise">Slime Splat (Gooey / Shock Splatter)</option>
                        <option value="speedline_aura">Speedline Aura (Focused Tension)</option>
                      </optgroup>
                      <optgroup label="Narration & Banners">
                        <option value="tilted_banner">Tilted Banner (Dramatic Caption)</option>
                        <option value="folded_ribbon_3d">3D Folded Ribbon (Parchment Scroll Banner)</option>
                        <option value="glitch_digital_crt">Digital CRT Glitch (Cybernetic HUD)</option>
                      </optgroup>
                      <optgroup label="Emotion & Villainy">
                        <option value="dark_aura_ghost">Dark Aura Ghost (Sinister / Demon Cursed)</option>
                        <option value="icicle_frost">Icicle Frost (Murderous Cold / Frozen)</option>
                        <option value="affection_heart">Affection Heart (Love / Sweet Delight)</option>
                      </optgroup>
                      <optgroup label="Free Text">
                        <option value="none">None (Free Text)</option>
                      </optgroup>
                    </select>
                  </label>

                  <label className="editor-field">
                    <span>Tail Type (10 Dynamic Pointers)</span>
                    <select
                      value={String(selectedText.metadata.tail_type || 'smooth_pointer')}
                      onChange={(e) => updateMetadata(selectedText.layer_id, 'tail_type', e.target.value)}
                    >
                      <option value="smooth_pointer">Smooth Pointer (Classic Horn)</option>
                      <option value="lightning_bolt">Lightning Bolt (Electric Zigzag)</option>
                      <option value="bubble_chain">Bubble Chain (Thought Trail)</option>
                      <option value="whisper_dashed">Whisper Dashed (Hushed Secret)</option>
                      <option value="dual_pointer">Dual Pointer (Chorus / Two Speakers)</option>
                      <option value="off_screen_pointer">Off-Screen Pointer (Off-Camera Voice)</option>
                      <option value="curved_hook_tail">Curved Hook Tail (Sickle Dynamic Arc)</option>
                      <option value="zigzag_antenna">Zigzag Antenna (Radio Transceiver Pulse)</option>
                      <option value="smoke_puff">Smoke Puff Tail (Exhaled Cloud)</option>
                      <option value="none">No Tail</option>
                    </select>
                  </label>

                  <div className="editor-field-grid">
                    <label className="editor-field">
                      <span>Accents</span>
                      <select
                        value={String(selectedText.metadata.accents || selectedText.metadata.accent || 'none')}
                        onChange={(e) => {
                          updateMetadata(selectedText.layer_id, 'accents', e.target.value);
                          updateMetadata(selectedText.layer_id, 'accent', e.target.value);
                        }}
                      >
                        <option value="none">None</option>
                        <option value="anger_vein_cross">Anger Cross 💢</option>
                        <option value="shock_marks">Shock Marks ⚡</option>
                        <option value="speedline_needles">Speedline Needles</option>
                        <option value="sparkles">Sparkles ✦</option>
                        <option value="sweat_drop">Sweat Drop 💧</option>
                        <option value="heart_flutter">Heart Flutter 💖</option>
                        <option value="dizziness_swirl">Dizziness Swirl 🌀</option>
                        <option value="electric_sparks">Electric Sparks ⚡</option>
                      </select>
                    </label>

                    <label className="editor-field" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <span>Manga Halftone Shadow</span>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '7px', cursor: 'pointer', marginTop: '4px' }}>
                        <input
                          type="checkbox"
                          checked={Boolean(selectedText.metadata.halftone_shadow)}
                          onChange={(e) => updateMetadata(selectedText.layer_id, 'halftone_shadow', e.target.checked)}
                          style={{ width: '16px', height: '16px', accentColor: '#111' }}
                        />
                        <span style={{ fontSize: '10px', color: '#ccc' }}>Halftone Screentone</span>
                      </label>
                    </label>
                  </div>

                  <div className="editor-field" style={{ marginBottom: '8px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '7px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(selectedText.metadata.inverted_dark_mode)}
                        onChange={(e) => {
                          const inv = e.target.checked;
                          updateMetadata(selectedText.layer_id, 'inverted_dark_mode', inv);
                          if (inv) {
                            updateMetadata(selectedText.layer_id, 'bubble_fill', '#111111');
                            updateMetadata(selectedText.layer_id, 'bubble_stroke', '#FFFFFF');
                            updateMetadata(selectedText.layer_id, 'color', '#FFFFFF');
                          } else {
                            updateMetadata(selectedText.layer_id, 'bubble_fill', '#FFFFFF');
                            updateMetadata(selectedText.layer_id, 'bubble_stroke', '#111111');
                            updateMetadata(selectedText.layer_id, 'color', '#111111');
                          }
                        }}
                        style={{ width: '16px', height: '16px', accentColor: '#111' }}
                      />
                      <span style={{ fontSize: '11px', color: '#f87171', fontWeight: 500 }}>
                        Inverted Dark Mode (Villain / Sinister Speech)
                      </span>
                    </label>
                  </div>

                  <div className="editor-field-grid">
                    <label className="editor-field">
                      <span>Bubble Fill</span>
                      <input
                        type="color"
                        value={String(selectedText.metadata.bubble_fill || '#FFFFFF')}
                        onChange={(e) => updateMetadata(selectedText.layer_id, 'bubble_fill', e.target.value)}
                      />
                    </label>
                    <label className="editor-field">
                      <span>Bubble Stroke</span>
                      <input
                        type="color"
                        value={String(selectedText.metadata.bubble_stroke || '#111111')}
                        onChange={(e) => updateMetadata(selectedText.layer_id, 'bubble_stroke', e.target.value)}
                      />
                    </label>
                  </div>

                  <div className="editor-field-grid">
                    <label className="editor-field">
                      <span>Stroke Width</span>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        step={0.5}
                        value={Number(selectedText.metadata.stroke_width || 2.5)}
                        onChange={(e) => updateMetadata(selectedText.layer_id, 'stroke_width', Number(e.target.value))}
                      />
                    </label>
                    <label className="editor-field">
                      <span>Height</span>
                      <input
                        type="number"
                        min={30}
                        value={Number(selectedText.metadata.height || 140)}
                        onChange={(e) => updateMetadata(selectedText.layer_id, 'height', Number(e.target.value))}
                      />
                    </label>
                  </div>

                  <div className="editor-field-grid">
                    <label className="editor-field">
                      <span>Tail Tip X</span>
                      <input
                        type="number"
                        value={Number(selectedText.metadata.tail_tip_x ?? (Number(selectedText.metadata.x || 0) + 80))}
                        onChange={(e) => updateMetadata(selectedText.layer_id, 'tail_tip_x', Number(e.target.value))}
                      />
                    </label>
                    <label className="editor-field">
                      <span>Tail Tip Y</span>
                      <input
                        type="number"
                        value={Number(selectedText.metadata.tail_tip_y ?? (Number(selectedText.metadata.y || 0) + 180))}
                        onChange={(e) => updateMetadata(selectedText.layer_id, 'tail_tip_y', Number(e.target.value))}
                      />
                    </label>
                  </div>

                  <div className="editor-field-grid" style={{ marginTop: '8px' }}>
                    <button
                      type="button"
                      className={`editor-vertex-tools button ${Boolean(selectedText.metadata?.flip_h) ? 'border-blue-500 text-blue-400' : ''}`}
                      style={{ minHeight: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', background: '#252525' }}
                      onClick={toggleFlipH}
                    >
                      <FlipHorizontal size={13} /> {Boolean(selectedText.metadata?.flip_h) ? 'Flipped H' : 'Flip H'}
                    </button>
                    <button
                      type="button"
                      className={`editor-vertex-tools button ${Boolean(selectedText.metadata?.flip_v) ? 'border-blue-500 text-blue-400' : ''}`}
                      style={{ minHeight: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', background: '#252525' }}
                      onClick={toggleFlipV}
                    >
                      <FlipVertical size={13} /> {Boolean(selectedText.metadata?.flip_v) ? 'Flipped V' : 'Flip V'}
                    </button>
                  </div>
                </div>
                <button className="editor-font-upload" onClick={() => fontInputRef.current?.click()} disabled={busy}>
                  <Upload size={13} /> Add font file
                </button>
                <button className="editor-danger" onClick={() => removeLayer(selectedText.layer_id)}>
                  <Trash2 size={14} /> Delete text layer
                </button>
              </>
            ) : selectedLine ? (
              <>
                <div className="editor-field-grid">
                  {(['x1', 'y1', 'x2', 'y2', 'stroke_width'] as const).map((key) => (
                    <label className="editor-field" key={key}>
                      <span>{key.replace('_', ' ')}</span>
                      <input
                        type="number"
                        min={key === 'stroke_width' ? 0.1 : undefined}
                        step="1"
                        value={Number(selectedLine.metadata[key] || 0)}
                        onChange={(e) => updateMetadata(selectedLine.layer_id, key, Number(e.target.value))}
                      />
                    </label>
                  ))}
                </div>
                <label className="editor-field">
                  <span>Line color</span>
                  <input
                    type="color"
                    value={String(selectedLine.metadata.color || '#111111')}
                    onChange={(e) => updateMetadata(selectedLine.layer_id, 'color', e.target.value)}
                  />
                </label>
                <label className="editor-field">
                  <span>Dash pattern</span>
                  <input
                    value={String(selectedLine.metadata.dash || '')}
                    placeholder="e.g. 8 4"
                    onChange={(e) => updateMetadata(selectedLine.layer_id, 'dash', e.target.value)}
                  />
                </label>
                <button className="editor-danger" onClick={() => removeLayer(selectedLine.layer_id)}>
                  <Trash2 size={14} /> Delete line
                </button>
              </>
            ) : selectedPanel ? (
              <>
                <label className="editor-field">
                  <span>Panel ID</span>
                  <code>{selectedPanel.panel_id}</code>
                </label>

                {/* Panel Artwork Selector Block */}
                <div className="p-3 my-2 rounded-xl bg-zinc-900 border border-white/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                      Panel Artwork
                    </span>
                    <button
                      type="button"
                      onClick={() => setImagePickerOpen(true)}
                      className="px-2.5 py-1 rounded bg-white text-black hover:bg-zinc-200 text-xs font-semibold transition flex items-center gap-1.5 shadow-sm cursor-pointer"
                    >
                      <ImagePlus size={12} />
                      {selectedPanelImage ? 'Change Image' : 'Select Image'}
                    </button>
                  </div>
                  {selectedPanelImage ? (
                    <div className="flex items-center gap-2.5 pt-1">
                      <img
                        src={apiClient.getAssetFileUrl(selectedPanelImage.source_asset_id || '')}
                        alt=""
                        className="w-12 h-12 object-cover rounded-lg bg-black/50 shrink-0 border border-white/10"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-white font-medium truncate">{selectedPanelImage.label}</p>
                        <code className="text-[10px] text-zinc-400 block truncate">{selectedPanelImage.source_asset_id}</code>
                      </div>
                    </div>
                  ) : (
                    <p className="text-[11px] text-zinc-400">
                      No artwork in this panel. Click <strong>Select Image</strong> to browse project assets or upload a file.
                    </p>
                  )}
                </div>
                <div className="editor-field-grid">
                  {(['x', 'y', 'width', 'height'] as const).map((key) => (
                    <label className="editor-field" key={key}>
                      <span>{key}</span>
                      <input
                        type="number"
                        step="1"
                        min={key === 'width' || key === 'height' ? 1 : undefined}
                        value={selectedPanel.rect[key]}
                        onChange={(e) => updatePanelRect(key, Number(e.target.value))}
                      />
                    </label>
                  ))}
                </div>
                <label className="editor-field">
                  <span>Reading order</span>
                  <input
                    type="number"
                    min="1"
                    value={selectedPanel.reading_order}
                    onChange={(e) => {
                      const next = clone(page);
                      const p = next.layout.panel_slots.find((item: any) => item.panel_id === selectedPanel.panel_id);
                      p.reading_order = Number(e.target.value);
                      next.layout.panel_slots.sort((a: any, b: any) => a.reading_order - b.reading_order);
                      next.layout.reading_order_panel_ids = next.layout.panel_slots.map((item: any) => item.panel_id);
                      commit(next);
                    }}
                  />
                </label>

                <div className="editor-vertex-tools">
                  <button onClick={() => void addPolygonVertex()}>
                    {selectedPanel.polygon?.length ? 'Add vertex' : 'Edit as polygon'}
                  </button>
                  {selectedPanel.polygon?.length && (
                    <button
                      onClick={() => void deletePolygonVertex()}
                      disabled={selectedVertex === null || selectedPanel.polygon.length <= 3}
                    >
                      Delete vertex
                    </button>
                  )}
                </div>

                {selectedPanel.polygon?.map((point: Point, index: number) => (
                  <div className={`editor-point-row ${selectedVertex === index ? 'active' : ''}`} key={index}>
                    <button onClick={() => setSelectedVertex(index)}>P{index + 1}</button>
                    <label>
                      x
                      <input
                        type="number"
                        value={point.x}
                        onChange={(e) => editVertex(index, 'x', Number(e.target.value))}
                      />
                    </label>
                    <label>
                      y
                      <input
                        type="number"
                        value={point.y}
                        onChange={(e) => editVertex(index, 'y', Number(e.target.value))}
                      />
                    </label>
                  </div>
                ))}

                <div className="editor-asset-heading">
                  <strong>Place Registered Artwork</strong>
                  <button onClick={() => void loadAssets()}>Refresh</button>
                </div>
                <div className="editor-assets">
                  {assets
                    .filter((asset) => String(asset.asset_type).includes('image') || asset.mime_type?.startsWith('image/'))
                    .map((asset) => (
                      <button key={asset.asset_id} onClick={() => addImage(asset)}>
                        <img src={apiClient.getAssetFileUrl(asset.asset_id)} alt="" />
                        <span>{asset.name || asset.original_filename}</span>
                        <Plus size={13} />
                      </button>
                    ))}
                  {!assets.some(
                    (asset) => String(asset.asset_type).includes('image') || asset.mime_type?.startsWith('image/')
                  ) && <p className="editor-muted">No registered images in this project.</p>}
                </div>
              </>
            ) : null}
          </section>

          <section className="editor-unavailable">
            <div className="editor-section-title">
              <strong>Production Engines</strong>
            </div>
            <p>
              Editable panels, independent E3 transforms within polygon masks, text, and vector dividers are active.
              Final composite renders preserve layers without flattening raw assets.
            </p>
          </section>
        </aside>
      </div>

      {/* Diagnostics Drawer & Conflict Warnings */}
      <div className={`editor-diagnostics ${showDiagnostics || conflictPage ? 'open' : ''}`}>
        <button className="editor-diagnostics-toggle" onClick={() => setShowDiagnostics((value) => !value)}>
          {showDiagnostics ? <ChevronDown /> : <ChevronUp />}
          Diagnostics <span>{diagnostics.length}</span>
        </button>
        {showDiagnostics && (
          <div className="editor-diagnostic-list">
            {diagnostics.length ? (
              diagnostics.map((item, index) => (
                <div key={index} className={`diagnostic-${item.severity}`}>
                  <b>{item.severity}</b>
                  <span>{item.message}</span>
                </div>
              ))
            ) : (
              <p>Run “Check geometry” to inspect current E2 layout constraints.</p>
            )}
          </div>
        )}
        {conflictPage && page && (
          <div className="editor-conflict">
            <strong>Page changed on server · revision {conflictPage.revision}</strong>
            <span>
              Your local edits are preserved. Reapplying will create a new revision incrementing the server version.
            </span>
            <button
              onClick={() => {
                setPage(conflictPage);
                setSavedRevision(conflictPage.revision);
                setHasChanges(false);
                setConflictPage(null);
                setError('');
              }}
            >
              Reload server version
            </button>
            <button
              onClick={async () => {
                setBusy(true);
                try {
                  const local = clone(page);
                  local.revision = conflictPage.revision;
                  const res = await apiClient.saveEditablePage(page.page_id, conflictPage.revision, local);
                  setPage(res);
                  setSavedRevision(res.revision);
                  setHasChanges(false);
                  setConflictPage(null);
                } catch (e: any) {
                  setError(e.message);
                } finally {
                  setBusy(false);
                }
              }}
              disabled={busy}
            >
              Reapply local edits
            </button>
          </div>
        )}
        {error && <div className="editor-error-inline">{error}</div>}
        {successMsg && <div className="p-2 bg-emerald-950/80 border border-emerald-800 text-xs text-emerald-300 rounded mt-2">{successMsg}</div>}
      </div>

      {/* Keyboard Shortcuts Dialog Modal */}
      {showShortcutsModal && (
        <div className="editor-modal-overlay" onClick={() => setShowShortcutsModal(false)}>
          <div className="editor-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="editor-modal-head">
              <h3>
                <Keyboard size={18} className="text-blue-400" />
                Page Editor Keyboard Shortcuts & Pro Controls
              </h3>
              <button
                type="button"
                onClick={() => setShowShortcutsModal(false)}
                className="p-1 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            <div className="editor-shortcut-grid">
              <div>
                <h4 className="text-[11px] uppercase tracking-wider text-zinc-400 font-semibold mb-2">
                  Clipboard & Editing
                </h4>
                <div className="editor-shortcut-row">
                  <span>Copy Element</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>C</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Paste Element</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>V</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Duplicate In-Place</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>D</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Delete Element</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Del</kbd> / <kbd>Backspace</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Crop / Fit Toggle</span>
                  <div className="editor-shortcut-keys">
                    <kbd>C</kbd>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-[11px] uppercase tracking-wider text-zinc-400 font-semibold mb-2">
                  Transform & Arrange
                </h4>
                <div className="editor-shortcut-row">
                  <span>Flip Horizontal (Mirror)</span>
                  <div className="editor-shortcut-keys">
                    <kbd>H</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Flip Vertical (Mirror)</span>
                  <div className="editor-shortcut-keys">
                    <kbd>V</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Nudge (1px / 10px)</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Arrows</kbd> / <kbd>Shift</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Send Backward</span>
                  <div className="editor-shortcut-keys">
                    <kbd>[</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Bring Forward</span>
                  <div className="editor-shortcut-keys">
                    <kbd>]</kbd>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-[11px] uppercase tracking-wider text-zinc-400 font-semibold mb-2">
                  History & Persistence
                </h4>
                <div className="editor-shortcut-row">
                  <span>Undo</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>Z</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Redo</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>Y</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Save Server Revision</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>S</kbd>
                  </div>
                </div>
                <div className="editor-shortcut-row">
                  <span>Deselect Active</span>
                  <div className="editor-shortcut-keys">
                    <kbd>Esc</kbd>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-[11px] uppercase tracking-wider text-zinc-400 font-semibold mb-2">
                  Pro Interactive Gizmo
                </h4>
                <div className="editor-shortcut-row">
                  <span>Scale Corner Handle</span>
                  <span className="text-[10px] text-zinc-300">Drag corner square</span>
                </div>
                <div className="editor-shortcut-row">
                  <span>Rotate Top Handle</span>
                  <span className="text-[10px] text-zinc-300">Drag knob (Shift=15°)</span>
                </div>
                <div className="editor-shortcut-row">
                  <span>Move Element</span>
                  <span className="text-[10px] text-zinc-300">Drag inside box</span>
                </div>
                <div className="editor-shortcut-row">
                  <span>Auto-saved Drafts</span>
                  <span className="text-[10px] text-emerald-400">Continuous 250ms</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-white/10 flex justify-end">
              <button
                type="button"
                onClick={() => setShowShortcutsModal(false)}
                className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs text-white transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {compositeModalUrl && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-6" onClick={() => setCompositeModalUrl(null)}>
          <div className="bg-zinc-900 border border-white/10 rounded-xl max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-zinc-950">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Eye size={16} className="text-indigo-400" />
                High-DPI Page Composite Preview (300 DPI)
              </h3>
              <div className="flex items-center gap-2">
                <a
                  href={compositeModalUrl}
                  download={`composite_${page?.page_id || 'page'}.png`}
                  className="px-2.5 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded font-medium flex items-center gap-1 transition"
                >
                  <Download size={13} />
                  Download PNG
                </a>
                <button
                  onClick={() => setCompositeModalUrl(null)}
                  className="text-zinc-400 hover:text-white p-1 rounded"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
            <div className="p-4 overflow-auto flex-1 flex items-center justify-center bg-zinc-950/50">
              <img src={compositeModalUrl} alt="Composite preview" className="max-h-[75vh] object-contain rounded shadow-lg border border-white/5" />
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
