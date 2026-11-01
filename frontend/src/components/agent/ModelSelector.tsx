import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Sparkles, AlertCircle } from 'lucide-react';
import {
  MetaLogo,
  MuseImageLogo,
} from './ModelLogos';

export interface ModelOption {
  id: string;
  name: string;
  shortName: string;
  provider: string;
  category: 'production' | 'frontier';
  tag: string;
  role: string;
  logo: React.ReactNode;
  isDefault?: boolean;
}

export const AVAILABLE_MODELS: ModelOption[] = [
  {
    id: 'muse-spark-1.3',
    name: 'Meta Muse Spark 1.3',
    shortName: 'Muse Spark 1.3',
    provider: 'Meta AI',
    category: 'production',
    tag: 'Active S9 Coordinator',
    role: 'Reasoning, script parsing, tool calling & creative planning',
    logo: <MetaLogo className="w-4 h-4 text-[#0081FB] shrink-0" />,
    isDefault: true,
  },
  {
    id: 'muse-image-1.0',
    name: 'Meta Muse Image 1.0',
    shortName: 'Muse Image 1.0',
    provider: 'Meta AI',
    category: 'production',
    tag: 'Vision Art Synthesis',
    role: 'Character consistency & high-fidelity comic panel rendering',
    logo: <MuseImageLogo className="w-4 h-4 text-purple-400 shrink-0" />,
  },
];

interface ModelSelectorProps {
  selectedModelId: string;
  onSelectModel: (modelId: string) => void;
  agentMode?: 'checking' | 'live_configured' | 'offline_explicit' | 'provider_unavailable';
  coordinatorConnected?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModelId,
  onSelectModel,
  agentMode = 'live_configured',
  coordinatorConnected = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const activeModel =
    AVAILABLE_MODELS.find((m) => m.id === selectedModelId) ||
    AVAILABLE_MODELS[0];

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const productionModels = AVAILABLE_MODELS.filter((m) => m.category === 'production');
  const frontierModels = AVAILABLE_MODELS.filter((m) => m.category === 'frontier');

  // Status indicator styling
  const statusConfig = {
    live_configured: {
      dot: 'bg-emerald-400',
      label: 'Live',
      ring: 'ring-emerald-400/20',
      title: 'Model credentials configured & ready for production reasoning',
    },
    offline_explicit: {
      dot: 'bg-amber-400',
      label: 'Offline Test',
      ring: 'ring-amber-400/20',
      title: 'Deterministic offline mode is explicitly enabled; simulated responses',
    },
    provider_unavailable: {
      dot: 'bg-rose-400',
      label: 'Unavailable',
      ring: 'ring-rose-400/20',
      title: 'Model provider credentials missing. Please configure MODEL_API_KEY',
    },
    checking: {
      dot: 'bg-sky-400 animate-pulse',
      label: 'Checking',
      ring: 'ring-sky-400/20',
      title: 'Checking agent runtime status...',
    },
  }[agentMode];

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      {/* Model Selector Pill / Badge */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`group flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs transition-all duration-200 select-none ${
          isOpen
            ? 'bg-[#222222] border-white/25 text-white shadow-lg'
            : 'bg-[#161616]/90 hover:bg-[#1f1f1f] border-white/10 hover:border-white/20 text-ink-200 hover:text-white'
        }`}
        title={`${activeModel.name} · ${statusConfig.title}`}
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        {/* Model Logo */}
        <div className="flex items-center justify-center">{activeModel.logo}</div>

        {/* Model Name */}
        <span className="font-medium text-white tracking-tight">{activeModel.name}</span>

        {/* Status Dot */}
        <span
          className={`w-2 h-2 rounded-full ${statusConfig.dot} ring-2 ${statusConfig.ring} shrink-0`}
          title={`Status: ${statusConfig.label}`}
        />

        {/* Chevron Dropdown Arrow */}
        <ChevronDown
          className={`w-3.5 h-3.5 text-ink-400 group-hover:text-ink-200 transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-white' : ''
          }`}
        />
      </button>

      {/* Floating Dropdown Menu */}
      {isOpen && (
        <div
          className="absolute right-0 mt-1.5 w-84 rounded-xl bg-[#141414]/95 backdrop-blur-xl border border-white/10 shadow-2xl p-1.5 z-50 text-xs animate-in fade-in zoom-in-95 duration-150"
          style={{ width: '22rem' }}
          role="menu"
        >
          {/* Menu Header */}
          <div className="px-3 py-2 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-ink-400 text-[11px] font-semibold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-white" />
              <span>Production AI Engines</span>
            </div>
            <span className="text-[10px] font-mono text-ink-400">
              {AVAILABLE_MODELS.length} Available
            </span>
          </div>

          <div className="max-h-[380px] overflow-y-auto py-1 space-y-2 pr-0.5">
            <div className="px-3 pt-1 pb-1 text-[10px] font-mono uppercase tracking-wider text-ink-500">
              Specialist Production Engines
            </div>
            <div className="space-y-0.5">
              {AVAILABLE_MODELS.map((model) => {
                const isSelected = model.id === activeModel.id;
                return (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => {
                      onSelectModel(model.id);
                      setIsOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg flex items-start gap-2.5 transition-all ${
                      isSelected
                        ? 'bg-white/10 text-white'
                        : 'hover:bg-white/5 text-ink-300 hover:text-white'
                    }`}
                    role="menuitem"
                  >
                    <div className="pt-0.5">{model.logo}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold text-white text-[12px] truncate">
                          {model.name}
                        </span>
                        <span
                          className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase tracking-wider shrink-0 ${
                            isSelected
                              ? 'bg-white/20 text-white'
                              : 'bg-white/[0.04] text-ink-400'
                          }`}
                        >
                          {model.tag}
                        </span>
                      </div>
                      <p className="text-[11px] text-ink-400 line-clamp-1 mt-0.5">
                        {model.role}
                      </p>
                    </div>
                    {isSelected && (
                      <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Menu Footer with Live Connection Status */}
          <div className="pt-2 mt-1 border-t border-white/5 px-3 py-1.5 flex items-center justify-between text-[11px] text-ink-400">
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${statusConfig.dot}`} />
              <span className="text-white font-medium">{statusConfig.label}</span>
              <span className="text-ink-500">•</span>
              <span className="text-ink-400 truncate max-w-[140px]">{activeModel.provider}</span>
            </div>
            {agentMode === 'provider_unavailable' && (
              <span className="text-rose-400 flex items-center gap-1 text-[10px]">
                <AlertCircle className="w-3 h-3" /> Config Required
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
