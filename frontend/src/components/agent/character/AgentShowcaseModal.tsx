import React, { useState, useRef } from 'react';
import {
  X,
  Copy,
  Check,
  Download,
  Grid,
  Sparkles,
  Film,
  Image as ImageIcon,
  Play,
  Pause,
  Layers,
} from 'lucide-react';
import {
  CharacterAssetMeta,
  MonochromeThemeId,
  StaticPoseId,
  AnimatedPoseId,
} from './types';
import {
  BW_PALETTES,
  STATIC_POSES_META,
  ANIMATED_POSES_META,
} from './palettes';
import { AgentCharacter } from './AgentCharacter';
import { TAB_CHARACTER_MAP } from './TabCharacterIcon';
import { NavTab } from '../../common/Sidebar';

export interface AgentShowcaseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AgentShowcaseModal: React.FC<AgentShowcaseModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'static' | 'animated' | 'tabs'>('all');
  const [themeId, setThemeId] = useState<MonochromeThemeId>('ink-dark');
  const [selectedAsset, setSelectedAsset] = useState<CharacterAssetMeta>(STATIC_POSES_META[0]);
  const [isPaused, setIsPaused] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const heroSvgRef = useRef<SVGSVGElement | null>(null);

  if (!isOpen) return null;

  const allAssets = [...STATIC_POSES_META, ...ANIMATED_POSES_META];

  const handleCopySvg = (assetId: string) => {
    const node = heroSvgRef.current;
    if (!node) return;
    const serializer = new XMLSerializer();
    let source = serializer.serializeToString(node);
    if (!source.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
      source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    const svgCode = `<?xml version="1.0" encoding="UTF-8"?>\n${source}`;
    navigator.clipboard.writeText(svgCode);
    setCopiedId(assetId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDownloadSvg = (assetId: string) => {
    const node = heroSvgRef.current;
    if (!node) return;
    const serializer = new XMLSerializer();
    let source = serializer.serializeToString(node);
    if (!source.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
      source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    const svgCode = `<?xml version="1.0" encoding="UTF-8"?>\n${source}`;
    const blob = new Blob([svgCode], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `inkloop-agent-${assetId}-${themeId}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-zinc-950 border border-zinc-800 rounded-3xl max-w-6xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden text-zinc-100">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between shrink-0 bg-zinc-900/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-700 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">
                  InkLoop Agent Monochrome Vector & Motion Studio
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-mono bg-zinc-800 text-zinc-300 border border-zinc-700">
                  Strict Black &amp; White
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                10 Static Poses + 10 CSS Keyframe Animations + 16 Unique Tab Logos
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Filter Tabs */}
            <div className="flex items-center bg-zinc-900 p-1 rounded-xl border border-zinc-800 text-xs">
              <button
                onClick={() => setActiveTab('all')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === 'all' ? 'bg-zinc-100 text-zinc-950' : 'text-zinc-400 hover:text-white'
                }`}
              >
                All (20)
              </button>
              <button
                onClick={() => setActiveTab('static')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === 'static' ? 'bg-zinc-100 text-zinc-950' : 'text-zinc-400 hover:text-white'
                }`}
              >
                10 Poses
              </button>
              <button
                onClick={() => setActiveTab('animated')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === 'animated' ? 'bg-zinc-100 text-zinc-950' : 'text-zinc-400 hover:text-white'
                }`}
              >
                10 Anims
              </button>
              <button
                onClick={() => setActiveTab('tabs')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === 'tabs' ? 'bg-zinc-100 text-zinc-950' : 'text-zinc-400 hover:text-white'
                }`}
              >
                16 Tab Logos
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Top Hero Preview */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-5">
            {/* Stage */}
            <div className="lg:col-span-7 flex flex-col items-center justify-center p-6 rounded-xl border border-zinc-800/80 bg-zinc-900/60 relative min-h-[300px]">
              <div className="absolute top-3 left-3 flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded text-[11px] font-semibold uppercase bg-zinc-950/80 text-white border border-zinc-800">
                  {selectedAsset.badge}
                </span>
                <span className="text-xs text-zinc-400 font-medium">
                  {selectedAsset.title}
                </span>
              </div>

              <div className="w-64 h-64 flex items-center justify-center">
                <AgentCharacter
                  pose={selectedAsset.category === 'static' ? (selectedAsset.id as StaticPoseId) : undefined}
                  animation={selectedAsset.category === 'animated' ? (selectedAsset.id as AnimatedPoseId) : undefined}
                  theme={themeId}
                  size={240}
                  isPaused={isPaused}
                  showFurTexture
                  svgRef={heroSvgRef}
                />
              </div>

              <div className="absolute bottom-3 right-3 flex items-center gap-2">
                {selectedAsset.category === 'animated' && (
                  <button
                    onClick={() => setIsPaused(!isPaused)}
                    className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-white flex items-center gap-1.5"
                  >
                    {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                    {isPaused ? 'Resume' : 'Pause'}
                  </button>
                )}
                <button
                  onClick={() => handleCopySvg(selectedAsset.id)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-white flex items-center gap-1.5"
                >
                  {copiedId === selectedAsset.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedId === selectedAsset.id ? 'Copied' : 'Copy SVG'}
                </button>
                <button
                  onClick={() => handleDownloadSvg(selectedAsset.id)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-100 hover:bg-white text-zinc-950 flex items-center gap-1.5 font-semibold"
                >
                  <Download className="w-3.5 h-3.5" />
                  .SVG
                </button>
              </div>
            </div>

            {/* Inspector Controls */}
            <div className="lg:col-span-5 flex flex-col justify-between space-y-4">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedAsset.title}</h3>
                <p className="text-xs text-zinc-300 mt-1 leading-relaxed">{selectedAsset.description}</p>
                <p className="text-[11px] font-mono text-zinc-400 bg-zinc-950 p-2.5 rounded-lg border border-zinc-800/80 mt-2">
                  {selectedAsset.technicalNotes}
                </p>
              </div>

              {/* Theme selector */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  Monochrome Palette (Black &amp; White Only)
                </span>
                <div className="grid grid-cols-1 gap-2">
                  {(Object.keys(BW_PALETTES) as MonochromeThemeId[]).map((id) => {
                    const pal = BW_PALETTES[id];
                    const active = themeId === id;
                    return (
                      <button
                        key={id}
                        onClick={() => setThemeId(id)}
                        className={`p-2.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                          active ? 'bg-zinc-800 border-zinc-400 shadow-sm' : 'bg-zinc-950/70 border-zinc-800 hover:border-zinc-700'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <span
                            className="w-4 h-4 rounded-full border border-zinc-600"
                            style={{ backgroundColor: pal.bgCard }}
                          />
                          <div>
                            <span className="text-xs font-semibold text-white block">{pal.name}</span>
                            <span className="text-[10px] text-zinc-400 block">{pal.subtitle}</span>
                          </div>
                        </div>
                        {active && <Check className="w-4 h-4 text-white" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* 16 TAB LOGOS VIEW */}
          {activeTab === 'tabs' ? (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
                16 Unique Tab Brand Logos (Sidebar Navigation)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                {(Object.keys(TAB_CHARACTER_MAP) as NavTab[]).map((tabId) => {
                  const m = TAB_CHARACTER_MAP[tabId];
                  return (
                    <div
                      key={tabId}
                      className="p-3.5 rounded-2xl bg-zinc-900/60 border border-zinc-800 hover:border-zinc-700 flex items-center gap-3.5 transition-all group"
                    >
                      <div className="w-12 h-12 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                        <AgentCharacter
                          animation={m.animatedPose}
                          theme={themeId}
                          size={38}
                          showFurTexture
                        />
                      </div>
                      <div className="min-w-0">
                        <span className="font-semibold text-xs text-white block truncate">{m.title}</span>
                        <span className="text-[10px] font-mono text-zinc-400 block">{tabId}</span>
                        <span className="text-[10px] text-zinc-500 line-clamp-1 mt-0.5">{m.conceptNote}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* POSES & ANIMATIONS GRID */
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3.5">
              {(activeTab === 'all'
                ? allAssets
                : activeTab === 'static'
                ? STATIC_POSES_META
                : ANIMATED_POSES_META
              ).map((asset) => {
                const isSelected = selectedAsset.id === asset.id;
                return (
                  <div
                    key={asset.id}
                    onClick={() => setSelectedAsset(asset)}
                    className={`p-3 rounded-2xl border cursor-pointer transition-all flex flex-col items-center text-center space-y-2 ${
                      isSelected
                        ? 'border-white bg-zinc-900 ring-2 ring-white/10'
                        : 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-900'
                    }`}
                  >
                    <div className="w-24 h-24 flex items-center justify-center">
                      <AgentCharacter
                        pose={asset.category === 'static' ? (asset.id as StaticPoseId) : undefined}
                        animation={asset.category === 'animated' ? (asset.id as AnimatedPoseId) : undefined}
                        theme={themeId}
                        size={84}
                        showFurTexture
                      />
                    </div>
                    <div className="w-full">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500 block">{asset.badge}</span>
                      <span className="text-xs font-semibold text-white truncate block">{asset.title}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
