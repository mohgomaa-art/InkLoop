/**
 * InkLoop Motion System Tokens & Utilities
 * Type-safe access to durations, easings, and animation execution helpers.
 */

export const MOTION_DURATIONS = {
  instant: 0,
  fast: 120,       // ms
  normal: 180,     // ms
  slow: 260,       // ms
  deliberate: 320, // ms
} as const;

export const MOTION_EASINGS = {
  enter: 'cubic-bezier(0.16, 1, 0.3, 1)',
  exit: 'cubic-bezier(0.4, 0, 1, 1)',
  standard: 'cubic-bezier(0.2, 0, 0, 1)',
  spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.1)',
  linear: 'linear',
} as const;

export const MOTION_DISTANCES = {
  xs: 2,
  sm: 4,
  md: 8,
  lg: 16,
  xl: 24,
} as const;

export type MotionPreference = 'normal' | 'reduced' | 'off';

/**
 * Check whether reduced motion is active either via OS preference or application setting.
 */
export function isReducedMotionActive(): boolean {
  if (typeof window === 'undefined') return false;
  const inAppPref = document.documentElement.dataset.motion;
  if (inAppPref === 'reduced' || inAppPref === 'off') return true;
  return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
}

/**
 * Safely animate an element via Web Animations API with respect for user preferences.
 */
export function safeAnimate(
  element: HTMLElement | SVGElement | null,
  keyframes: Keyframe[] | PropertyIndexedKeyframes,
  options: KeyframeAnimationOptions = {}
): Animation | null {
  if (!element || typeof element.animate !== 'function') return null;

  if (isReducedMotionActive()) {
    // In reduced motion, execute instantaneously
    const reducedOptions: KeyframeAnimationOptions = {
      ...options,
      duration: 0,
      delay: 0,
    };
    return element.animate(keyframes, reducedOptions);
  }

  return element.animate(keyframes, {
    easing: MOTION_EASINGS.standard,
    duration: MOTION_DURATIONS.normal,
    fill: 'forwards',
    ...options,
  });
}

/**
 * Execute a DOM mutation within a View Transition if supported, with fallback.
 */
export async function executeViewTransition(callback: () => void | Promise<void>): Promise<void> {
  if (typeof document !== 'undefined' && 'startViewTransition' in document && !isReducedMotionActive()) {
    return (document as any).startViewTransition(callback).finished;
  }
  await callback();
}
