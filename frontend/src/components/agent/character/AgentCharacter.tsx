import React, { useId } from 'react';
import {
  StaticPoseId,
  AnimatedPoseId,
  MonochromeThemeId,
  CharacterSize,
  CharacterRenderConfig,
} from './types';
import { BW_PALETTES } from './palettes';
import { StaticPoseSvg } from './StaticPoses';
import { AnimatedPoseSvg } from './AnimatedPoses';

export interface AgentCharacterProps {
  pose?: StaticPoseId;
  animation?: AnimatedPoseId;
  theme?: MonochromeThemeId;
  size?: CharacterSize;
  speedMultiplier?: number;
  isPaused?: boolean;
  showFurTexture?: boolean;
  strokeScale?: number;
  showStudioGrid?: boolean;
  showGroundShadow?: boolean;
  tight?: boolean;
  viewBox?: string;
  className?: string;
  style?: React.CSSProperties;
  svgRef?: React.Ref<SVGSVGElement>;
}

export const SIZE_MAP: Record<string, number> = {
  xs: 20,
  sm: 28,
  md: 40,
  lg: 64,
  xl: 96,
  '2xl': 140,
  hero: 220,
};

export const AgentCharacter: React.FC<AgentCharacterProps> = ({
  pose,
  animation,
  theme = 'ink-light',
  size = 'md',
  speedMultiplier = 1,
  isPaused = false,
  showFurTexture = true,
  strokeScale = 1,
  showStudioGrid = false,
  showGroundShadow = false,
  tight = true,
  viewBox,
  className = '',
  style,
  svgRef,
}) => {
  const reactId = useId().replace(/:/g, '');
  const palette = BW_PALETTES[theme] || BW_PALETTES['ink-light'];

  const pixelSize = typeof size === 'number' ? size : SIZE_MAP[size] || 40;

  const config: CharacterRenderConfig = {
    palette,
    showFurTexture,
    strokeScale,
    speedMultiplier,
    isPaused,
    showStudioGrid,
    showGroundShadow,
    tight,
    viewBox,
  };

  const containerStyle: React.CSSProperties = {
    width: pixelSize,
    height: pixelSize,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    ...style,
  };

  // Default to neutral stand if neither is specified
  const effectivePose = !animation && !pose ? 'pose-neutral' : pose;

  return (
    <div className={`agent-character-root ${className}`} style={containerStyle}>
      {animation ? (
        <AnimatedPoseSvg
          animId={animation}
          config={config}
          svgRef={svgRef}
          idPrefix={`inst-${reactId}`}
        />
      ) : (
        <StaticPoseSvg
          poseId={effectivePose!}
          config={config}
          svgRef={svgRef}
          idPrefix={`inst-${reactId}`}
        />
      )}
    </div>
  );
};
