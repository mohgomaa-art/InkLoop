import { useState, useEffect, useCallback } from 'react';
import type { MotionPreference } from '../utils/motion';

const STORAGE_KEY = 'inkloop_motion_preference';

export function useReducedMotion() {
  const [preference, setPreferenceState] = useState<MotionPreference>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as MotionPreference | null;
      if (saved === 'normal' || saved === 'reduced' || saved === 'off') {
        return saved;
      }
    } catch {
      // Storage unavailable
    }
    return 'normal';
  });

  const [systemReduced, setSystemReduced] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  });

  // Listen to OS-level preference changes
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => {
      setSystemReduced(e.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Update HTML data attribute whenever preference or system setting changes
  useEffect(() => {
    if (typeof document === 'undefined') return;
    const effective = preference === 'normal' && systemReduced ? 'reduced' : preference;
    document.documentElement.dataset.motion = effective;
  }, [preference, systemReduced]);

  const setPreference = useCallback((next: MotionPreference) => {
    setPreferenceState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage unavailable
    }
  }, []);

  const isReduced = preference === 'reduced' || preference === 'off' || (preference === 'normal' && systemReduced);

  return {
    preference,
    setPreference,
    systemReduced,
    isReduced,
  };
}
