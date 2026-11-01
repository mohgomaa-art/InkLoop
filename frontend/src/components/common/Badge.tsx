import React from 'react';

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'danger'
  | 'simulated'
  | 'info'
  | 'purple'
  | 'studio'
  | 'neutral';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  className?: string;
  title?: string;
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; border: string; dotColor: string }> = {
  success: {
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/20',
    dotColor: 'bg-emerald-400',
  },
  warning: {
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/20',
    dotColor: 'bg-amber-400',
  },
  danger: {
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/20',
    dotColor: 'bg-rose-400',
  },
  simulated: {
    bg: 'bg-orange-500/15',
    text: 'text-orange-300',
    border: 'border-orange-500/30',
    dotColor: 'bg-orange-400',
  },
  info: {
    bg: 'bg-sky-500/10',
    text: 'text-sky-400',
    border: 'border-sky-500/20',
    dotColor: 'bg-sky-400',
  },
  purple: {
    bg: 'bg-white/10',
    text: 'text-ink-200',
    border: 'border-white/15',
    dotColor: 'bg-white',
  },
  studio: {
    bg: 'bg-white/10',
    text: 'text-white',
    border: 'border-white/20',
    dotColor: 'bg-white',
  },
  neutral: {
    bg: 'bg-white/5',
    text: 'text-ink-400',
    border: 'border-white/10',
    dotColor: 'bg-ink-400',
  },
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-xs font-medium',
  lg: 'px-3 py-1.5 text-sm font-medium',
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  className = '',
  title,
}) => {
  const v = variantStyles[variant];
  const s = sizeStyles[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${v.bg} ${v.text} ${v.border} ${s} transition-colors tracking-wide ${className}`}
      title={title}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${v.dotColor} motion-shimmer`} />}
      {children}
    </span>
  );
};
