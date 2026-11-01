import { useState, useEffect } from 'react';

/**
 * Tracks document visibility state to pause animations and decorative loops
 * when the application tab/window is hidden or backgrounded.
 */
export function usePageVisibility(): boolean {
  const [isVisible, setIsVisible] = useState<boolean>(() => {
    if (typeof document === 'undefined') return true;
    return document.visibilityState !== 'hidden';
  });

  useEffect(() => {
    if (typeof document === 'undefined') return;

    const handleVisibilityChange = () => {
      setIsVisible(document.visibilityState !== 'hidden');
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return isVisible;
}
