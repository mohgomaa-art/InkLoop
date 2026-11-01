import React, { useState } from 'react';
import {
  AgentLogoVariant,
  CharacterSize,
  MonochromeThemeId,
} from './types';
import { AgentCharacter, SIZE_MAP } from './AgentCharacter';

export interface AgentLogoProps {
  variant?: AgentLogoVariant;
  size?: CharacterSize;
  theme?: MonochromeThemeId;
  title?: string;
  subtitle?: string;
  showSubtitle?: boolean;
  interactive?: boolean;
  className?: string;
  onClick?: () => void;
}

export const AgentLogo: React.FC<AgentLogoProps> = ({
  variant = 'lockup',
  size = 'md',
  theme = 'ink-dark',
  title = 'InkLoop Agent',
  subtitle = 'Production Orchestrator',
  showSubtitle = true,
  interactive = true,
  className = '',
  onClick,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const pixelSize = typeof size === 'number' ? size : SIZE_MAP[size] || 32;

  const isAnimated = variant === 'animated' || (interactive && isHovered);

  // Emblem / Silhouette / Badge / Lockup
  const renderMark = () => {
    return (
      <div
        className={`agent-logo-mark-wrap relative inline-flex items-center justify-center shrink-0 transition-transform duration-300 ${
          interactive ? 'hover:scale-110' : ''
        }`}
      >
        <AgentCharacter
          pose={isAnimated ? undefined : 'pose-neutral'}
          animation={isAnimated ? 'anim-breathing' : undefined}
          theme={theme}
          size={pixelSize}
          showFurTexture={pixelSize >= 32}
          strokeScale={pixelSize < 24 ? 1.25 : 1}
          showGroundShadow={false}
        />
      </div>
    );
  };

  if (variant === 'emblem' || variant === 'silhouette' || variant === 'badge') {
    return (
      <div
        className={`agent-logo-root inline-flex items-center cursor-pointer ${className}`}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={onClick}
        role={onClick ? 'button' : undefined}
        tabIndex={onClick ? 0 : undefined}
        title={title}
      >
        {renderMark()}
      </div>
    );
  }

  // Full Brand Lockup (Mark + Typography)
  return (
    <div
      className={`agent-logo-lockup inline-flex items-center gap-2.5 select-none ${
        onClick ? 'cursor-pointer' : ''
      } ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {renderMark()}
      <div className="flex flex-col text-left leading-tight">
        <span
          className={`font-semibold tracking-tight text-white ${
            pixelSize >= 48 ? 'text-lg' : pixelSize >= 32 ? 'text-sm' : 'text-xs'
          }`}
        >
          {title}
        </span>
        {showSubtitle && subtitle && (
          <span
            className={`font-mono text-zinc-400 ${
              pixelSize >= 48 ? 'text-xs' : 'text-[10px]'
            }`}
          >
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
};
