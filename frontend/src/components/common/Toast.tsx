import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'warning' | 'error' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  showToast: (toast: Omit<ToastItem, 'id'>) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [exitingIds, setExitingIds] = useState<Set<string>>(new Set());

  const removeToast = useCallback((id: string) => {
    setExitingIds((prev) => new Set(prev).add(id));
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
      setExitingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }, 160);
  }, []);

  const showToast = useCallback(
    ({ type, title, message, duration = 4000 }: Omit<ToastItem, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, type, title, message, duration }]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-md pointer-events-none">
        {toasts.map((toast) => {
          const isExiting = exitingIds.has(toast.id);
          const icons = {
            success: <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />,
            warning: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />,
            error: <XCircle className="w-5 h-5 text-rose-400 shrink-0" />,
            info: <Info className="w-5 h-5 text-sky-400 shrink-0" />,
          };

          const borders = {
            success: 'border-emerald-500/30',
            warning: 'border-amber-500/30',
            error: 'border-rose-500/30',
            info: 'border-sky-500/30',
          };

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl bg-ink-900/90 backdrop-blur-xl border ${
                borders[toast.type]
              } shadow-card text-ink-100 ${
                isExiting ? 'motion-slide-up-out' : 'motion-slide-up-in'
              }`}
            >
              {icons[toast.type]}
              <div className="flex-1 pr-2">
                <h4 className="text-sm font-medium text-white">{toast.title}</h4>
                {toast.message && (
                  <p className="text-xs text-ink-300 mt-0.5 leading-relaxed">{toast.message}</p>
                )}
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="text-ink-400 hover:text-white p-1 rounded-md transition-colors motion-interactive"
                aria-label="Dismiss toast"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
};
