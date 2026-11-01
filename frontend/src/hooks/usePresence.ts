import { useState, useEffect } from 'react';
import { MOTION_DURATIONS, isReducedMotionActive } from '../utils/motion';

export interface UsePresenceResult {
  /** Whether the component should remain mounted in the DOM */
  isMounted: boolean;
  /** Whether the component is currently playing its enter animation */
  isEntering: boolean;
  /** Whether the component is currently playing its exit animation */
  isExiting: boolean;
  /** Phase helper */
  phase: 'entering' | 'entered' | 'exiting' | 'exited';
}

/**
 * Coordinates unmounting with exit animations without requiring heavy external libraries.
 * Keeps `isMounted: true` while `isExiting: true` until `durationMs` has elapsed,
 * then cleanly unmounts the element from React DOM.
 */
export function usePresence(
  isOpen: boolean,
  durationMs: number = MOTION_DURATIONS.slow
): UsePresenceResult {
  const [isMounted, setIsMounted] = useState(isOpen);
  const [phase, setPhase] = useState<'entering' | 'entered' | 'exiting' | 'exited'>(
    isOpen ? 'entered' : 'exited'
  );

  useEffect(() => {
    const reduced = isReducedMotionActive();
    const effectiveDuration = reduced ? 0 : durationMs;

    if (isOpen) {
      setIsMounted(true);
      if (effectiveDuration === 0) {
        setPhase('entered');
      } else {
        setPhase('entering');
        const timer = setTimeout(() => {
          setPhase('entered');
        }, effectiveDuration);
        return () => clearTimeout(timer);
      }
    } else {
      if (!isMounted) return;

      if (effectiveDuration === 0) {
        setPhase('exited');
        setIsMounted(false);
      } else {
        setPhase('exiting');
        const timer = setTimeout(() => {
          setPhase('exited');
          setIsMounted(false);
        }, effectiveDuration);
        return () => clearTimeout(timer);
      }
    }
  }, [isOpen, durationMs, isMounted]);

  return {
    isMounted,
    isEntering: phase === 'entering',
    isExiting: phase === 'exiting',
    phase,
  };
}
