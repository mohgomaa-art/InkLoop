import React, { useState } from 'react';
import { NavTab } from '../../common/Sidebar';
import { StaticPoseId, AnimatedPoseId, MonochromeThemeId } from './types';
import { AgentCharacter } from './AgentCharacter';
import { usePageVisibility } from '../../../hooks/usePageVisibility';
import { useReducedMotion } from '../../../hooks/useReducedMotion';

export interface TabMapping {
  tab: NavTab;
  title: string;
  staticPose: StaticPoseId;
  animatedPose: AnimatedPoseId;
  conceptNote: string;
}

export const TAB_CHARACTER_MAP: Record<NavTab, TabMapping> = {
  agent: {
    tab: 'agent',
    title: 'Create & Run',
    staticPose: 'pose-wave',
    animatedPose: 'anim-wave-loop',
    conceptNote: 'Friendly welcoming AI assistant greeting the creator',
  },
  editor: {
    tab: 'editor',
    title: 'Page Editor',
    staticPose: 'pose-confident',
    animatedPose: 'anim-breathing',
    conceptNote: 'Proud akimbo stance, master artisan directing page composition',
  },
  'style-copier': {
    tab: 'style-copier',
    title: 'Style Copier',
    staticPose: 'pose-shy',
    animatedPose: 'anim-fluff-shiver',
    conceptNote: 'Fur puff & aura shiver, analyzing artistic brush and style textures',
  },
  'character-copier': {
    tab: 'character-copier',
    title: 'Character Copier',
    staticPose: 'pose-shy',
    animatedPose: 'anim-cheek-squish',
    conceptNote: 'Cheek squish & expression study, capturing facial proportions',
  },
  creative: {
    tab: 'creative',
    title: 'Creative Director',
    staticPose: 'pose-thinking',
    animatedPose: 'anim-breathing',
    conceptNote: 'Curious ponder looking up with chin on paw, deep ideation',
  },
  'location-studio': {
    tab: 'location-studio',
    title: 'Location Studio',
    staticPose: 'pose-thinking',
    animatedPose: 'anim-zen-float',
    conceptNote: 'Mapping reusable places and their scene conditions',
  },
  'object-studio': {
    tab: 'object-studio',
    title: 'Object Studio',
    staticPose: 'pose-thinking',
    animatedPose: 'anim-breathing',
    conceptNote: 'Carefully preserving a recurring object design and its visual evidence',
  },
  bible: {
    tab: 'bible',
    title: 'Story Bible & Canon',
    staticPose: 'pose-sitting',
    animatedPose: 'anim-breathing',
    conceptNote: 'Seated calmly on the floor like a wise canon lore-master',
  },
  timeline: {
    tab: 'timeline',
    title: 'Continuity Timeline',
    staticPose: 'pose-neutral',
    animatedPose: 'anim-waddle-walk',
    conceptNote: 'Jaunty waddle walk cycle, marching through continuity timeline',
  },
  assets: {
    tab: 'assets',
    title: 'Asset Library',
    staticPose: 'pose-heart-gift',
    animatedPose: 'anim-breathing',
    conceptNote: 'Plush offering, holding precious registered library assets',
  },
  batches: {
    tab: 'batches',
    title: 'Runs History',
    staticPose: 'pose-star-jump',
    animatedPose: 'anim-happy-hop',
    conceptNote: 'Squash & stretch bounce, springing across batch runs',
  },
  studio: {
    tab: 'studio',
    title: 'Manual Studio',
    staticPose: 'pose-star-jump',
    animatedPose: 'anim-boogie-dance',
    conceptNote: 'Joyful star leap with 4-point monochrome sparkles and magic',
  },
  verification: {
    tab: 'verification',
    title: 'Verification Lab',
    staticPose: 'pose-thinking',
    animatedPose: 'anim-peekaboo',
    conceptNote: 'Curious peek-a-boo scanning left-to-right, vigilant inspector',
  },
  catalogue: {
    tab: 'catalogue',
    title: 'Knowledge Catalogue',
    staticPose: 'pose-warm-mug',
    animatedPose: 'anim-breathing',
    conceptNote: 'Warm cocoa hug, relaxed researcher browsing the archive',
  },
  budgets: {
    tab: 'budgets',
    title: 'Budgets & Costs',
    staticPose: 'pose-neutral',
    animatedPose: 'anim-breathing',
    conceptNote: 'Classic balanced plush stand, grounded financial equilibrium',
  },
  benchmarks: {
    tab: 'benchmarks',
    title: 'Benchmarks',
    staticPose: 'pose-star-jump',
    animatedPose: 'anim-boogie-dance',
    conceptNote: 'Upbeat groove boogie with pulsing beat stars, peak performance',
  },
  settings: {
    tab: 'settings',
    title: 'System Diagnostics',
    staticPose: 'pose-sleeping',
    animatedPose: 'anim-sleepy-nod',
    conceptNote: 'Sleepy nod-off and startle, maintenance standby and diagnostics',
  },
  workspace: {
    tab: 'workspace',
    title: 'Workspace KPI',
    staticPose: 'pose-sitting',
    animatedPose: 'anim-zen-float',
    conceptNote: 'Levitating lotus zen float, elevated holistic KPI overview',
  },
};

export interface TabCharacterIconProps {
  tab: NavTab;
  active?: boolean;
  size?: number;
  theme?: MonochromeThemeId;
  animateOnActive?: boolean;
  animateOnHover?: boolean;
  tight?: boolean;
  className?: string;
}

export const TabCharacterIcon: React.FC<TabCharacterIconProps> = ({
  tab,
  active = false,
  size = 32,
  theme = 'ink-dark',
  animateOnActive = true,
  animateOnHover = true,
  tight = true,
  className = '',
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const isVisible = usePageVisibility();
  const { isReduced } = useReducedMotion();
  const mapping = TAB_CHARACTER_MAP[tab] || TAB_CHARACTER_MAP['agent'];

  // Calm, intentional interaction: active tab stays composed with its dignified static pose.
  // Animation triggers only on deliberate hover when visible and reduced-motion is not requested.
  const shouldAnimate = !isReduced && isVisible && animateOnHover && isHovered;

  return (
    <span
      className={`tab-character-icon inline-flex items-center justify-center shrink-0 transition-transform duration-200 ${
        active ? 'scale-110 drop-shadow-[0_2px_8px_rgba(255,255,255,0.15)]' : 'opacity-85 hover:opacity-100 hover:scale-105'
      } ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      title={`${mapping.title} — ${mapping.conceptNote}`}
      aria-hidden="true"
    >
      <AgentCharacter
        pose={shouldAnimate ? undefined : mapping.staticPose}
        animation={shouldAnimate ? mapping.animatedPose : undefined}
        theme={theme}
        size={size}
        tight={tight}
        speedMultiplier={1.1}
        showFurTexture={size >= 24}
        strokeScale={size < 24 ? 1.2 : 1}
        showGroundShadow={false}
      />
    </span>
  );
};
