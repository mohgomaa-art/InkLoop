import React, { useEffect, useState, useMemo } from 'react';
import {
  Database,
  ShieldCheck,
  Download,
  GitFork,
  Image as ImageIcon,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Copy,
  Check,
  FileCode,
  Search,
  Filter,
  Maximize2,
  ExternalLink,
  FileText,
  Type,
  Layers,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { TabCharacterIcon } from '../components/agent/character';
import { ImageLightbox, LightboxImage } from '../components/agent/ImageLightbox';
import { apiClient } from '../api/client';
import { useToast } from '../components/common/Toast';

interface AssetLibraryViewProps {
  currentProject: string;
}

export const AssetLibraryView: React.FC<AssetLibraryViewProps> = ({ currentProject }) => {
  const { showToast } = useToast();
  const [assets, setAssets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAsset, setSelectedAsset] = useState<any | null>(null);
  const [lineageData, setLineageData] = useState<any | null>(null);
  const [verifyingHash, setVerifyingHash] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);
  const [manifestModalOpen, setManifestModalOpen] = useState(false);
  const [manifestJson, setManifestJson] = useState<any | null>(null);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterScope, setFilterScope] = useState<'project' | 'all'>('project');
  const [typeFilter, setTypeFilter] = useState<'all' | 'images' | 'documents' | 'fonts'>('all');
  const [lightboxImage, setLightboxImage] = useState<LightboxImage | null>(null);
  const [failedImages, setFailedImages] = useState<Record<string, boolean>>({});

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const params = filterScope === 'project' && currentProject ? { project_id: currentProject } : undefined;
      const data = await apiClient.listAssets(params);
      setAssets(data);
      if (selectedAsset && !data.some((a: any) => a.asset_id === selectedAsset.asset_id)) {
        setSelectedAsset(null);
        setLineageData(null);
      }
    } catch (err: any) {
      showToast({ type: 'error', title: 'Failed to load assets', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, [currentProject, filterScope]);

  const handleSelectAsset = async (asset: any) => {
    setSelectedAsset(asset);
    try {
      const lineage = await apiClient.getAssetLineage(asset.asset_id);
      setLineageData(lineage);
    } catch {
      setLineageData(null);
    }
  };

  const handleVerifyIntegrity = async (assetId: string) => {
    try {
      setVerifyingHash(true);
      const res = await apiClient.verifyAssetIntegrity(assetId);
      if (res.integrity_verified) {
        showToast({
          type: 'success',
          title: 'Physical Disk Integrity Verified',
          message: `Streaming on-disk SHA-256 matches: ${res.content_sha256.substring(0, 16)}...`,
        });
      } else {
        showToast({
          type: 'error',
          title: 'Integrity Check Failed',
          message: 'On-disk bytes do not match registered content checksum.',
        });
      }
    } catch (err: any) {
      showToast({ type: 'error', title: 'Integrity Verification Error', message: err.message });
    } finally {
      setVerifyingHash(false);
    }
  };

  const handleExportManifest = async () => {
    try {
      const manifest = await apiClient.exportManifest(currentProject);
      setManifestJson(manifest);
      setManifestModalOpen(true);
    } catch (err: any) {
      showToast({ type: 'error', title: 'Manifest Export Failed', message: err.message });
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
    showToast({ type: 'info', title: 'Copied to Clipboard', message: text.substring(0, 20) + '...' });
  };

  const getAssetLabel = (asset: any): string => {
    return asset.original_filename || asset.name || asset.logical_filename || asset.asset_id;
  };

  const isImageAsset = (asset: any): boolean => {
    if (asset.mime_type && asset.mime_type.startsWith('image/')) return true;
    const name = (asset.original_filename || asset.name || asset.asset_id || '').toLowerCase();
    if (/\.(png|jpe?g|webp|svg|gif|avif)$/i.test(name)) return true;
    if (asset.asset_type && (
      asset.asset_type.includes('image') ||
      asset.asset_type.includes('panel') ||
      asset.asset_type.includes('composite') ||
      asset.asset_type.includes('reference')
    )) return true;
    return false;
  };

  const isFontAsset = (asset: any): boolean => {
    if (asset.asset_type === 'font_file') return true;
    const name = (asset.original_filename || asset.name || '').toLowerCase();
    return /\.(woff2?|ttf|otf)$/i.test(name);
  };

  // Filtered Assets list
  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      // Type filter
      if (typeFilter === 'images' && !isImageAsset(asset)) return false;
      if (typeFilter === 'fonts' && !isFontAsset(asset)) return false;
      if (typeFilter === 'documents' && (isImageAsset(asset) || isFontAsset(asset))) return false;

      // Text search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const label = getAssetLabel(asset).toLowerCase();
        const id = (asset.asset_id || '').toLowerCase();
        const hash = (asset.content_sha256 || '').toLowerCase();
        const type = (asset.asset_type || '').toLowerCase();
        if (!label.includes(q) && !id.includes(q) && !hash.includes(q) && !type.includes(q)) {
          return false;
        }
      }

      return true;
    });
  }, [assets, typeFilter, searchQuery]);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-card border border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <TabCharacterIcon tab="assets" size={38} />
              Content-Addressed Asset Library & Lineage
            </h1>
            <Badge variant="neutral" size="sm">
              SHA-256 Addressed
            </Badge>
          </div>
          <p className="text-xs text-ink-300 mt-1">
            Tamper-evident storage: artifacts decoupled from metadata, verified on-disk checksums, and DAG provenance.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={handleExportManifest}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-medium transition-colors"
          >
            <FileCode className="w-4 h-4 text-white" />
            Export Deterministic Manifest
          </button>
          <button
            onClick={fetchAssets}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-ink-300 hover:text-white transition-colors"
            title="Refresh assets"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Control Bar: Search, Scope Toggle, and Type Filters */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-3.5 rounded-2xl glass-card border border-white/5">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-ink-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, asset ID, hash..."
              className="w-full bg-ink-950/70 border border-white/10 rounded-xl pl-9 pr-3.5 py-1.5 text-xs text-white placeholder-ink-500 focus:outline-none focus:border-white/20"
            />
          </div>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="text-[11px] text-ink-400 hover:text-white px-2 py-1"
            >
              Clear
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Project Scope Toggle */}
          <div className="flex items-center bg-ink-950/80 border border-white/10 rounded-xl p-0.5 text-xs">
            <button
              onClick={() => setFilterScope('project')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                filterScope === 'project'
                  ? 'bg-white/15 text-white shadow-sm'
                  : 'text-ink-400 hover:text-white'
              }`}
            >
              Current Project
            </button>
            <button
              onClick={() => setFilterScope('all')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                filterScope === 'all'
                  ? 'bg-white/15 text-white shadow-sm'
                  : 'text-ink-400 hover:text-white'
              }`}
            >
              All Projects
            </button>
          </div>

          {/* Type Filter Buttons */}
          <div className="flex items-center bg-ink-950/80 border border-white/10 rounded-xl p-0.5 text-xs">
            <button
              onClick={() => setTypeFilter('all')}
              className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
                typeFilter === 'all' ? 'bg-white/15 text-white' : 'text-ink-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setTypeFilter('images')}
              className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
                typeFilter === 'images' ? 'bg-white/15 text-white' : 'text-ink-400 hover:text-white'
              }`}
            >
              Images
            </button>
            <button
              onClick={() => setTypeFilter('documents')}
              className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
                typeFilter === 'documents' ? 'bg-white/15 text-white' : 'text-ink-400 hover:text-white'
              }`}
            >
              Docs
            </button>
            <button
              onClick={() => setTypeFilter('fonts')}
              className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
                typeFilter === 'fonts' ? 'bg-white/15 text-white' : 'text-ink-400 hover:text-white'
              }`}
            >
              Fonts
            </button>
          </div>
        </div>
      </div>

      {/* Grid: Assets Cards + Asset Inspector Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Assets Cards Grid */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white tracking-tight">
              Registered Artifacts ({filteredAssets.length}{filteredAssets.length !== assets.length ? ` of ${assets.length}` : ''})
            </h2>
            <span className="text-[11px] text-ink-400">
              {filterScope === 'project' ? `Scoped to ${currentProject}` : 'Across all registered repositories'}
            </span>
          </div>

          {loading ? (
            <div className="py-16 text-center text-xs text-ink-400 animate-pulse">Loading visual assets...</div>
          ) : filteredAssets.length === 0 ? (
            <Card className="text-center py-16">
              <Database className="w-10 h-10 text-ink-500 mx-auto mb-3 opacity-40" />
              <p className="text-xs text-ink-300 font-medium">No matching assets found.</p>
              <p className="text-[11px] text-ink-500 mt-1">
                {searchQuery ? 'Try adjusting your search query or filters.' : 'Artifacts created during generations will be listed here with visual previews.'}
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {filteredAssets.map((asset) => {
                const isSelected = selectedAsset?.asset_id === asset.asset_id;
                const isCanonicalAnchor = asset.original_filename === 'nour_reference.png' || asset.name === 'nour_reference';
                const label = getAssetLabel(asset);
                const isImage = isImageAsset(asset);
                const isFont = isFontAsset(asset);
                const fileUrl = apiClient.getAssetFileUrl(asset.asset_id);
                const hasFailed = failedImages[asset.asset_id];

                return (
                  <div
                    key={asset.asset_id}
                    onClick={() => handleSelectAsset(asset)}
                    className={`rounded-2xl glass-card border transition-all cursor-pointer flex flex-col justify-between overflow-hidden group ${
                      isSelected
                        ? 'border-white/30 bg-ink-850 ring-1 ring-white/20 shadow-lg'
                        : 'border-white/5 hover:border-white/20 bg-ink-900/60'
                    }`}
                  >
                    {/* Visual Image Preview / Thumbnail Box */}
                    <div className="relative aspect-[16/10] w-full bg-ink-950 border-b border-white/5 overflow-hidden flex items-center justify-center">
                      {isImage && !hasFailed ? (
                        <>
                          <img
                            src={fileUrl}
                            alt={label}
                            decoding="async"
                            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                            onError={() => {
                              setFailedImages((prev) => ({ ...prev, [asset.asset_id]: true }));
                            }}
                          />
                          {/* Quick Lightbox Action Button */}
                          <button
                            type="button"
                            title="Expand preview"
                            onClick={(e) => {
                              e.stopPropagation();
                              setLightboxImage({
                                src: fileUrl,
                                name: label,
                                sourceType: isCanonicalAnchor ? 'canonical_anchor' : 'registered_asset',
                                dimensions: asset.width && asset.height ? { width: asset.width, height: asset.height } : undefined,
                                sizeBytes: asset.byte_size,
                                sha256: asset.content_sha256,
                                mimeType: asset.mime_type,
                                assetId: asset.asset_id,
                              });
                            }}
                            className="absolute bottom-2 right-2 p-1.5 rounded-lg bg-black/60 hover:bg-black/80 text-white/80 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm"
                          >
                            <Maximize2 className="w-3.5 h-3.5" />
                          </button>
                        </>
                      ) : isFont ? (
                        <div className="flex flex-col items-center justify-center gap-1.5 text-ink-400">
                          <Type className="w-8 h-8 opacity-60 text-indigo-400" />
                          <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500">Typography Font</span>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center gap-1.5 text-ink-400">
                          {asset.mime_type === 'application/pdf' ? (
                            <FileText className="w-8 h-8 opacity-60 text-rose-400" />
                          ) : (
                            <FileCode className="w-8 h-8 opacity-60 text-sky-400" />
                          )}
                          <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500">
                            {asset.extension || asset.mime_type || 'Artifact Document'}
                          </span>
                        </div>
                      )}

                      {/* Top Badges Overlay */}
                      <div className="absolute top-2 left-2 right-2 flex items-center justify-between pointer-events-none">
                        <span className="text-[9px] font-mono px-2 py-0.5 rounded-md bg-black/70 backdrop-blur-md text-ink-300 border border-white/10 truncate max-w-[140px]">
                          {asset.extension || (asset.mime_type ? asset.mime_type.split('/')[1] : 'bin')}
                        </span>
                        {isCanonicalAnchor ? (
                          <Badge variant="success" size="sm">
                            Anchor
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            {asset.asset_type}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Metadata & Details Section */}
                    <div className="p-3.5 space-y-2">
                      <div className="flex items-center gap-2">
                        <ImageIcon className="w-3.5 h-3.5 text-white/80 shrink-0" />
                        <span className="text-xs font-semibold text-white truncate" title={label}>
                          {label}
                        </span>
                      </div>

                      <div className="space-y-0.5 font-mono text-[10px] text-ink-400">
                        <div className="truncate">
                          ID: <span className="text-ink-300">{asset.asset_id}</span>
                        </div>
                        <div className="truncate">
                          SHA-256: <span className="text-emerald-400">{asset.content_sha256}</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-white/5 text-[10px] text-ink-400">
                        <span>
                          {asset.width && asset.height
                            ? `${asset.width}×${asset.height}px`
                            : asset.dimensions
                            ? `${asset.dimensions.width}×${asset.dimensions.height}px`
                            : 'Raster Asset'}
                        </span>
                        <span>{asset.byte_size ? `${(asset.byte_size / 1024).toFixed(1)} KB` : ''}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Asset Detail Inspector */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-white tracking-tight">Asset Inspector</h2>

          {selectedAsset ? (
            <Card
              title={getAssetLabel(selectedAsset)}
              subtitle={`Asset Type: ${selectedAsset.asset_type}`}
            >
              <div className="space-y-4 pt-2">
                {/* Image Preview & Full Lightbox Action */}
                <div className="relative rounded-xl overflow-hidden bg-ink-950 border border-white/10 aspect-square flex items-center justify-center group">
                  {isImageAsset(selectedAsset) ? (
                    <>
                      <img
                        src={apiClient.getAssetFileUrl(selectedAsset.asset_id)}
                        alt={getAssetLabel(selectedAsset)}
                        className="max-h-full max-w-full object-contain cursor-zoom-in"
                        onClick={() => {
                          setLightboxImage({
                            src: apiClient.getAssetFileUrl(selectedAsset.asset_id),
                            name: getAssetLabel(selectedAsset),
                            sourceType: 'registered_asset',
                            dimensions: selectedAsset.width && selectedAsset.height ? { width: selectedAsset.width, height: selectedAsset.height } : undefined,
                            sizeBytes: selectedAsset.byte_size,
                            sha256: selectedAsset.content_sha256,
                            mimeType: selectedAsset.mime_type,
                            assetId: selectedAsset.asset_id,
                          });
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setLightboxImage({
                            src: apiClient.getAssetFileUrl(selectedAsset.asset_id),
                            name: getAssetLabel(selectedAsset),
                            sourceType: 'registered_asset',
                            dimensions: selectedAsset.width && selectedAsset.height ? { width: selectedAsset.width, height: selectedAsset.height } : undefined,
                            sizeBytes: selectedAsset.byte_size,
                            sha256: selectedAsset.content_sha256,
                            mimeType: selectedAsset.mime_type,
                            assetId: selectedAsset.asset_id,
                          });
                        }}
                        className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/60 hover:bg-black/80 text-white opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm"
                        title="Open full view"
                      >
                        <Maximize2 className="w-3.5 h-3.5" />
                      </button>
                    </>
                  ) : (
                    <div className="text-center p-6 text-ink-500">
                      <FileCode className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p className="text-xs">Non-image asset</p>
                      <span className="text-[10px] font-mono">{selectedAsset.mime_type || 'Unknown MIME'}</span>
                    </div>
                  )}
                </div>

                {/* Direct File Download / Open Link */}
                <a
                  href={apiClient.getAssetFileUrl(selectedAsset.asset_id)}
                  target="_blank"
                  rel="noreferrer"
                  download={selectedAsset.original_filename || `${selectedAsset.asset_id}`}
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
                >
                  <Download className="w-3.5 h-3.5 text-sky-400" />
                  Download Asset File ({selectedAsset.byte_size ? `${(selectedAsset.byte_size / 1024).toFixed(1)} KB` : 'file'})
                </a>

                {/* Technical Metadata */}
                <div className="space-y-1.5 p-3 rounded-xl bg-ink-950 border border-white/5 font-mono text-[10px]">
                  <div className="flex justify-between text-ink-400">
                    <span>Project:</span>
                    <span className="text-white font-medium">{selectedAsset.project_id || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between text-ink-400">
                    <span>Dimensions:</span>
                    <span className="text-white">
                      {selectedAsset.width && selectedAsset.height ? `${selectedAsset.width} × ${selectedAsset.height} px` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between text-ink-400">
                    <span>DPI / Density:</span>
                    <span className="text-white">{selectedAsset.dpi ? `${selectedAsset.dpi} DPI` : '96 DPI'}</span>
                  </div>
                  <div className="flex justify-between text-ink-400">
                    <span>MIME Type:</span>
                    <span className="text-white">{selectedAsset.mime_type || 'unknown'}</span>
                  </div>
                  <div className="flex justify-between text-ink-400">
                    <span>Validation:</span>
                    <span className="text-emerald-400">{selectedAsset.validation_state || 'valid'}</span>
                  </div>
                </div>

                {/* SHA-256 Verification Action */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-white">SHA-256 Digest</span>
                    <button
                      onClick={() => copyToClipboard(selectedAsset.content_sha256)}
                      className="text-xs text-ink-300 hover:text-white flex items-center gap-1"
                    >
                      {copiedHash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      {copiedHash ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <div className="p-2.5 rounded-xl bg-ink-950 border border-white/5 font-mono text-[10px] text-emerald-400 break-all select-all">
                    {selectedAsset.content_sha256}
                  </div>
                </div>

                <button
                  onClick={() => handleVerifyIntegrity(selectedAsset.asset_id)}
                  disabled={verifyingHash}
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white transition-colors"
                >
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  {verifyingHash ? 'Streaming & Recalculating Hash...' : 'Verify Physical Disk Integrity'}
                </button>

                {/* Lineage DAG Section */}
                <div className="pt-2 border-t border-white/5">
                  <div className="flex items-center gap-1.5 mb-2">
                    <GitFork className="w-4 h-4 text-white" />
                    <span className="text-xs font-semibold text-white">Lineage Provenance (DAG)</span>
                  </div>

                  <div className="text-xs space-y-2">
                    <div>
                      <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Parents (Inputs):</span>
                      {lineageData?.parents?.length > 0 ? (
                        <div className="space-y-1 mt-1">
                          {lineageData.parents.map((p: any) => (
                            <div key={p.asset_id} className="p-1.5 rounded bg-ink-950 text-[10px] font-mono text-ink-300 flex items-center justify-between">
                              <span className="truncate max-w-[180px]">{p.original_filename || p.name || p.asset_id}</span>
                              <span className="text-[9px] text-ink-500">{p.asset_id}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[11px] text-ink-500">Root / Canonical Anchor</span>
                      )}
                    </div>

                    <div>
                      <span className="text-[10px] text-ink-500 uppercase tracking-wider block">Children (Derivatives):</span>
                      {lineageData?.children?.length > 0 ? (
                        <div className="space-y-1 mt-1">
                          {lineageData.children.map((c: any) => (
                            <div key={c.asset_id} className="p-1.5 rounded bg-ink-950 text-[10px] font-mono text-ink-300 flex items-center justify-between">
                              <span className="truncate max-w-[180px]">{c.original_filename || c.name || c.asset_id}</span>
                              <span className="text-[9px] text-ink-500">{c.asset_id}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[11px] text-ink-500">No derivatives registered yet</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ) : (
            <Card className="text-center py-12">
              <p className="text-xs text-ink-400">Select an asset to inspect content hash and lineage.</p>
            </Card>
          )}
        </div>
      </div>

      {/* MANIFEST EXPORT MODAL */}
      <Modal
        isOpen={manifestModalOpen}
        onClose={() => setManifestModalOpen(false)}
        title="Deterministic Project Manifest"
        maxWidth="xl"
        footer={
          <button
            onClick={() => setManifestModalOpen(false)}
            className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-medium"
          >
            Close
          </button>
        }
      >
        <div className="space-y-3">
          <p className="text-xs text-ink-300">
            Reproducible, sorted JSON manifest in accordance with ADR-009 and Section 16 of INKLOOP_TASKS.md.
          </p>
          <div className="p-3 rounded-xl bg-ink-950 font-mono text-[10px] text-white max-h-96 overflow-y-auto border border-white/5">
            <pre>{JSON.stringify(manifestJson, null, 2)}</pre>
          </div>
        </div>
      </Modal>

      {/* LIGHTBOX FOR FULL RESOLUTION PREVIEW */}
      {lightboxImage && (
        <ImageLightbox
          image={lightboxImage}
          onClose={() => setLightboxImage(null)}
        />
      )}
    </div>
  );
};
