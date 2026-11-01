import React from 'react';

interface CardProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  glow?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  action,
  className = '',
  glow = false,
}) => {
  return (
    <div
      className={`glass-card motion-card rounded-2xl p-5 border ${
        glow ? 'border-white/20' : 'border-white/5'
      } ${className}`}
    >
      {(title || action || subtitle) && (
        <div className="flex items-start justify-between gap-4 mb-4 pb-3 border-b border-white/5">
          <div>
            {title && (
              <h3 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-ink-400 mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div className="flex items-center gap-2 shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
};
