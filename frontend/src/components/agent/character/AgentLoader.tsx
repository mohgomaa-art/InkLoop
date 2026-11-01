import React from 'react';
import {
  LoaderVariant,
  AnimatedPoseId,
  CharacterSize,
  MonochromeThemeId,
} from './types';
import { AgentCharacter, SIZE_MAP } from './AgentCharacter';

export interface AgentLoaderProps {
  variant?: LoaderVariant;
  mode?: 'inline' | 'block' | 'overlay' | 'fullscreen';
  size?: CharacterSize;
  theme?: MonochromeThemeId;
  message?: string;
  submessage?: string;
  className?: string;
}

const VARIANT_TO_ANIMATION: Record<LoaderVariant, AnimatedPoseId> = {
  hop: 'anim-happy-hop',
  zen: 'anim-zen-float',
  peek: 'anim-peekaboo',
  waddle: 'anim-waddle-walk',
  shiver: 'anim-fluff-shiver',
  boogie: 'anim-boogie-dance',
  orbit: 'anim-breathing',
};

export const AgentLoader: React.FC<AgentLoaderProps> = ({
  variant = 'waddle',
  mode = 'block',
  size,
  theme = 'ink-dark',
  message = 'Agent is thinking...',
  submessage,
  className = '',
}) => {
  const animId = VARIANT_TO_ANIMATION[variant] || 'anim-waddle-walk';

  // Default sizes per mode if not explicitly provided
  const defaultSize: CharacterSize =
    size || (mode === 'inline' ? 'xs' : mode === 'fullscreen' ? 'xl' : 'lg');
  const pixelSize = typeof defaultSize === 'number' ? defaultSize : SIZE_MAP[defaultSize] || 64;

  const characterMarkup = (
    <div className="relative inline-flex items-center justify-center">
      <AgentCharacter
        animation={animId}
        theme={theme}
        size={pixelSize}
        speedMultiplier={variant === 'hop' ? 1.2 : 1}
        showFurTexture={pixelSize >= 48}
        strokeScale={pixelSize < 32 ? 1.3 : 1}
      />

      {variant === 'orbit' && (
        <div className="absolute inset-0 rounded-full border border-white/20 border-t-white animate-spin" />
      )}
    </div>
  );

  // MODE 1: Inline (e.g. inside a button or chat stream)
  if (mode === 'inline') {
    return (
      <span className={`agent-loader-inline inline-flex items-center gap-2 text-xs text-zinc-300 ${className}`}>
        {characterMarkup}
        {message && (
          <span className="font-mono text-[11px] text-zinc-200">
            {message}
            <span className="inline-block animate-pulse">...</span>
          </span>
        )}
      </span>
    );
  }

  // Content block containing character + message
  const contentBlock = (
    <div className="flex flex-col items-center justify-center text-center space-y-3 p-4">
      {characterMarkup}

      {message && (
        <div className="space-y-1">
          <div className="text-sm font-semibold tracking-tight text-white flex items-center justify-center gap-1">
            <span>{message}</span>
            <span className="inline-flex space-x-0.5">
              <span className="w-1 h-1 rounded-full bg-white animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1 h-1 rounded-full bg-white animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1 h-1 rounded-full bg-white animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
          </div>

          {submessage && (
            <p className="text-xs text-zinc-400 font-mono max-w-xs mx-auto">
              {submessage}
            </p>
          )}
        </div>
      )}
    </div>
  );

  // MODE 2: Overlay over an existing panel
  if (mode === 'overlay') {
    return (
      <div
        className={`agent-loader-overlay absolute inset-0 z-40 bg-zinc-950/75 backdrop-blur-sm flex items-center justify-center animate-in fade-in duration-200 ${className}`}
      >
        <div className="flex flex-col items-center justify-center max-w-sm w-full mx-4">
          {contentBlock}
        </div>
      </div>
    );
  }

  // MODE 3: Fullscreen (Bootstrap or major chapter generation)
  if (mode === 'fullscreen') {
    return (
      <div
        className={`agent-loader-fullscreen fixed inset-0 z-50 bg-zinc-950 flex flex-col items-center justify-center p-6 select-none ${className}`}
      >
        <div className="max-w-md w-full">{contentBlock}</div>
      </div>
    );
  }

  // MODE 4: Block (default card/view loader)
  return (
    <div className={`agent-loader-block w-full py-8 flex items-center justify-center ${className}`}>
      {contentBlock}
    </div>
  );
};
