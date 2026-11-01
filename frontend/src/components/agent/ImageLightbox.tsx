import React, { useState, useEffect, useRef } from 'react';
import { X, ZoomIn, ZoomOut, RotateCcw, Copy, Check, ShieldCheck, Database, FileImage } from 'lucide-react';
import { usePresence } from '../../hooks/usePresence';
import { MOTION_DURATIONS } from '../../utils/motion';

export interface LightboxImage {
  src: string;
  name: string;
  sourceType?: 'user_upload' | 'registered_asset' | 'canonical_anchor';
  dimensions?: { width: number; height: number };
  sizeBytes?: number;
  sha256?: string;
  mimeType?: string;
  assetId?: string;
  verificationVerdict?: 'PASS' | 'FAIL' | 'UNSURE';
}

interface ImageLightboxProps {
  image: LightboxImage | null;
  onClose: () => void;
}

export const ImageLightbox: React.FC<ImageLightboxProps> = ({ image, onClose }) => {
  const [scale, setScale] = useState(1);
  const [copiedHash, setCopiedHash] = useState(false);
  const lastImageRef = useRef<LightboxImage | null>(image);
  if (image) lastImageRef.current = image;
  const activeImage = image || lastImageRef.current;
  const { isMounted, isExiting } = usePresence(Boolean(image), MOTION_DURATIONS.slow);

  useEffect(() => {
    setScale(1);
    setCopiedHash(false);
  }, [image]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === '+' || e.key === '=') setScale((s) => Math.min(s + 0.25, 4));
      if (e.key === '-') setScale((s) => Math.max(s - 0.25, 0.5));
      if (e.key === '0') setScale(1);
    };
    if (image) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [image, onClose]);

  if (!isMounted || !activeImage) return null;

  const handleCopyHash = () => {
    if (activeImage.sha256) {
      navigator.clipboard.writeText(activeImage.sha256);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col bg-ink-950/95 backdrop-blur-xl select-none ${
        isExiting ? 'motion-backdrop-exit' : 'motion-backdrop-enter'
      }`}
    >
      {/* Top Controls Bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-white/10 bg-ink-900/80">
        <div className="flex items-center gap-3">
          <FileImage className="w-5 h-5 text-white" />
          <div>
            <h3 className="text-sm font-semibold text-white truncate max-w-md">{activeImage.name}</h3>
            <div className="flex items-center gap-2 text-[11px] text-ink-400">
              <span className="capitalize">{(activeImage.sourceType || 'registered_asset').replace('_', ' ')}</span>
              {activeImage.dimensions && (
                <>
                  <span>•</span>
                  <span>{activeImage.dimensions.width} × {activeImage.dimensions.height} px</span>
                </>
              )}
              {activeImage.sizeBytes && (
                <>
                  <span>•</span>
                  <span>{(activeImage.sizeBytes / 1024).toFixed(1)} KB</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Zoom & Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setScale((s) => Math.max(s - 0.25, 0.5))}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-ink-300 hover:text-white transition-all"
            title="Zoom Out (-)"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs font-mono text-ink-300 min-w-[48px] text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((s) => Math.min(s + 0.25, 4))}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-ink-300 hover:text-white transition-all"
            title="Zoom In (+)"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setScale(1)}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-ink-300 hover:text-white transition-all"
            title="Reset Zoom (0)"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <div className="h-5 w-px bg-white/10 mx-1" />
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-white/10 hover:bg-rose-500/20 text-ink-300 hover:text-white transition-all"
            title="Close (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Image Viewport & Metadata Drawer */}
      <div className="flex-1 flex overflow-hidden">
        {/* Pan/Zoom Stage */}
        <div className="flex-1 flex items-center justify-center p-6 overflow-auto bg-dot-grid">
          <div
            style={{ transform: `scale(${scale})`, transition: 'transform 0.15s ease-out' }}
            className="relative max-w-full max-h-full flex items-center justify-center"
          >
            <img
              src={activeImage.src}
              alt={activeImage.name}
              className="max-h-[82vh] max-w-[80vw] object-contain rounded-lg border border-white/10 shadow-2xl"
              draggable={false}
            />
          </div>
        </div>

        {/* Sidebar Metadata Strip */}
        <div className="w-80 border-l border-white/10 bg-ink-900/60 p-5 space-y-4 overflow-y-auto text-xs hidden md:block">
          <div>
            <h4 className="text-[10px] font-semibold uppercase tracking-wider text-ink-500 mb-2">
              Cryptographic Integrity
            </h4>
            {activeImage.sha256 ? (
              <div className="p-3 rounded-xl bg-ink-950 border border-white/5 space-y-2">
                <div className="flex items-center justify-between text-ink-400">
                  <span className="text-[10px]">SHA-256 Digest</span>
                  <button
                    onClick={handleCopyHash}
                    className="flex items-center gap-1 text-[10px] text-ink-300 hover:text-white"
                  >
                    {copiedHash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedHash ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <div className="font-mono text-[11px] text-ink-200 break-all select-all leading-relaxed">
                  {activeImage.sha256}
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-ink-950 text-ink-500 text-[11px] border border-white/5">
                Hash computed at ingest
              </div>
            )}
          </div>

          <div>
            <h4 className="text-[10px] font-semibold uppercase tracking-wider text-ink-500 mb-2">
              Asset Properties
            </h4>
            <div className="space-y-2 font-mono text-[11px]">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-ink-400">Origin:</span>
                <span className="text-white capitalize">{(activeImage.sourceType || 'registered_asset').replace('_', ' ')}</span>
              </div>
              {activeImage.assetId && (
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-ink-400">Asset ID:</span>
                  <span className="text-white">{activeImage.assetId}</span>
                </div>
              )}
              {activeImage.mimeType && (
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-ink-400">MIME:</span>
                  <span className="text-ink-200">{activeImage.mimeType}</span>
                </div>
              )}
              {activeImage.dimensions && (
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-ink-400">Geometry:</span>
                  <span className="text-ink-200">{activeImage.dimensions.width} × {activeImage.dimensions.height} px</span>
                </div>
              )}
              {activeImage.verificationVerdict && (
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-ink-400">Verification:</span>
                  <span
                    className={`font-semibold ${
                      activeImage.verificationVerdict === 'PASS'
                        ? 'text-emerald-400'
                        : activeImage.verificationVerdict === 'FAIL'
                        ? 'text-rose-400'
                        : 'text-amber-400'
                    }`}
                  >
                    {activeImage.verificationVerdict}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
