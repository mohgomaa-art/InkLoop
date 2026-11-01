export type MonochromeThemeId = 'ink-light' | 'ink-dark' | 'pure-contrast';

export interface MonochromePalette {
  id: MonochromeThemeId;
  name: string;
  subtitle: string;
  bgCard: string;
  suitLight: string;
  suitMid: string;
  suitShadow: string;
  suitDeepShadow: string;
  suitRim: string;
  faceLight: string;
  faceMid: string;
  faceShadow: string;
  hoodInnerShadow: string;
  eyeFill: string;
  eyeHighlight: string;
  cheekGlow: string;
  strokeColor: string;
  furStroke: string;
  groundShadow: string;
  accentTone: string;
}

export type StaticPoseId =
  | 'pose-neutral'
  | 'pose-wave'
  | 'pose-sitting'
  | 'pose-thinking'
  | 'pose-star-jump'
  | 'pose-shy'
  | 'pose-sleeping'
  | 'pose-confident'
  | 'pose-warm-mug'
  | 'pose-heart-gift';

export type AnimatedPoseId =
  | 'anim-breathing'
  | 'anim-wave-loop'
  | 'anim-happy-hop'
  | 'anim-waddle-walk'
  | 'anim-fluff-shiver'
  | 'anim-zen-float'
  | 'anim-cheek-squish'
  | 'anim-peekaboo'
  | 'anim-sleepy-nod'
  | 'anim-boogie-dance';

export interface CharacterAssetMeta {
  id: StaticPoseId | AnimatedPoseId;
  index: number;
  title: string;
  category: 'static' | 'animated';
  badge: string;
  description: string;
  technicalNotes: string;
}

export interface CharacterRenderConfig {
  palette: MonochromePalette;
  showFurTexture: boolean;
  strokeScale: number;
  speedMultiplier: number;
  isPaused: boolean;
  showStudioGrid?: boolean;
  showGroundShadow?: boolean;
  tight?: boolean;
  viewBox?: string;
}

export type AgentStatusState =
  | 'idle'
  | 'thinking'
  | 'working'
  | 'inspecting'
  | 'waiting_approval'
  | 'success'
  | 'sleeping'
  | 'error';

export type LoaderVariant =
  | 'hop'
  | 'zen'
  | 'peek'
  | 'waddle'
  | 'shiver'
  | 'boogie'
  | 'orbit';

export type AgentLogoVariant =
  | 'emblem'
  | 'silhouette'
  | 'badge'
  | 'lockup'
  | 'animated';

export type CharacterSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'hero' | number;
