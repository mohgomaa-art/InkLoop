import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { usePresence } from '../../hooks/usePresence';
import { MOTION_DURATIONS } from '../../utils/motion';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '4xl';
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '4xl';
}

const widthStyles = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '4xl': 'max-w-4xl',
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  maxWidth = 'lg',
  size,
}) => {
  const effectiveWidth = size || maxWidth;
  const { isMounted, isExiting } = usePresence(isOpen, MOTION_DURATIONS.slow);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isMounted) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop with Smooth Enter & Exit */}
      <div
        className={`fixed inset-0 bg-ink-950/80 backdrop-blur-md ${
          isExiting ? 'motion-backdrop-exit' : 'motion-backdrop-enter'
        }`}
        onClick={onClose}
      />

      {/* Dialog box with Calm Scale & Fade */}
      <div
        role="dialog"
        aria-modal="true"
        className={`relative w-full ${widthStyles[effectiveWidth]} rounded-2xl bg-ink-900 border border-white/10 shadow-2xl p-6 overflow-hidden z-10 ${
          isExiting ? 'motion-dialog-exit' : 'motion-dialog-enter'
        }`}
      >
        <div className="flex items-center justify-between pb-4 border-b border-white/5">
          <h3 className="text-base font-semibold text-white tracking-tight">{title}</h3>
          <button
            onClick={onClose}
            className="text-ink-400 hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors motion-interactive"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="py-4 max-h-[75vh] overflow-y-auto">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/5">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
