import React from 'react';
import {
  AgentStatusState,
  StaticPoseId,
  AnimatedPoseId,
  MonochromeThemeId,
  CharacterSize,
} from './types';
import { AgentCharacter, SIZE_MAP } from './AgentCharacter';

export interface StatusMeta {
  state: AgentStatusState;
  label: string;
  dotColor: string;
  staticPose: StaticPoseId;
  animatedPose: AnimatedPoseId;
  description: string;
}

export const STATUS_DEFINITIONS: Record<AgentStatusState, StatusMeta> = {
  idle: {
    state: 'idle',
    label: 'Ready & Idle',
    dotColor: '#A1A1AA',
    staticPose: 'pose-neutral',
    animatedPose: 'anim-breathing',
    description: 'Agent is standby, monitoring project context and ready for tasks.',
  },
  thinking: {
    state: 'thinking',
    label: 'Analyzing & Planning',
    dotColor: '#FAFAFA',
    staticPose: 'pose-thinking',
    animatedPose: 'anim-zen-float',
    description: 'Agent is pondering story bible constraints and synthesizing next steps.',
  },
  working: {
    state: 'working',
    label: 'Executing Pipeline',
    dotColor: '#FFFFFF',
    staticPose: 'pose-confident',
    animatedPose: 'anim-waddle-walk',
    description: 'Agent is active, dispatching tools, rendering pages, or generating scripts.',
  },
  inspecting: {
    state: 'inspecting',
    label: 'Inspecting Asset',
    dotColor: '#D4D4D8',
    staticPose: 'pose-thinking',
    animatedPose: 'anim-peekaboo',
    description: 'Scanning visual assets, checking character fidelity and line continuity.',
  },
  waiting_approval: {
    state: 'waiting_approval',
    label: 'Awaiting Approval',
    dotColor: '#E4E4E7',
    staticPose: 'pose-shy',
    animatedPose: 'anim-cheek-squish',
    description: 'High-impact tool execution proposed; waiting for creator confirmation.',
  },
  success: {
    state: 'success',
    label: 'Task Complete',
    dotColor: '#FFFFFF',
    staticPose: 'pose-wave',
    animatedPose: 'anim-happy-hop',
    description: 'Requested chapter run or generation finished successfully.',
  },
  sleeping: {
    state: 'sleeping',
    label: 'Offline / Standby',
    dotColor: '#52525B',
    staticPose: 'pose-sleeping',
    animatedPose: 'anim-sleepy-nod',
    description: 'Agent runtime is asleep or detached from provider.',
  },
  error: {
    state: 'error',
    label: 'Interrupted / Error',
    dotColor: '#71717A',
    staticPose: 'pose-shy',
    animatedPose: 'anim-fluff-shiver',
    description: 'An exception or validation gate blocked the execution flow.',
  },
};

export interface AgentStatusProps {
  state?: AgentStatusState;
  mode?: 'badge' | 'avatar' | 'card';
  size?: CharacterSize;
  theme?: MonochromeThemeId;
  animated?: boolean;
  customLabel?: string;
  customDescription?: string;
  className?: string;
  onClick?: () => void;
}

export const AgentStatus: React.FC<AgentStatusProps> = ({
  state = 'idle',
  mode = 'badge',
  size = 'sm',
  theme = 'ink-dark',
  animated = true,
  customLabel,
  customDescription,
  className = '',
  onClick,
}) => {
  const meta = STATUS_DEFINITIONS[state] || STATUS_DEFINITIONS['idle'];
  const pixelSize = typeof size === 'number' ? size : SIZE_MAP[size] || 24;

  const characterElement = (
    <AgentCharacter
      pose={animated ? undefined : meta.staticPose}
      animation={animated ? meta.animatedPose : undefined}
      theme={theme}
      size={pixelSize}
      showFurTexture={pixelSize >= 32}
      strokeScale={pixelSize < 24 ? 1.25 : 1}
    />
  );

  // MODE 1: Compact Pill Badge (for Header / Title bar)
  if (mode === 'badge') {
    return (
      <div
        className={`agent-status-badge inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-zinc-900/90 border border-zinc-800 text-xs text-zinc-200 select-none backdrop-blur-sm transition-all hover:border-zinc-700 ${
          onClick ? 'cursor-pointer hover:bg-zinc-800' : ''
        } ${className}`}
        onClick={onClick}
        title={`${meta.label}: ${meta.description}`}
      >
        <span className="w-6 h-6 flex items-center justify-center shrink-0">
          <AgentCharacter
            pose={animated ? undefined : meta.staticPose}
            animation={animated ? meta.animatedPose : undefined}
            theme={theme}
            size={22}
            strokeScale={1.1}
          />
        </span>
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0 animate-pulse"
          style={{ backgroundColor: meta.dotColor }}
        />
        <span className="font-medium text-[11px] text-zinc-100">
          {customLabel || meta.label}
        </span>
      </div>
    );
  }

  // MODE 2: Circular Profile Avatar with status ring/dot
  if (mode === 'avatar') {
    return (
      <div
        className={`agent-status-avatar relative inline-flex items-center justify-center rounded-2xl bg-zinc-900 border border-zinc-700/80 p-1 shadow-inner ${
          onClick ? 'cursor-pointer hover:border-zinc-500' : ''
        } ${className}`}
        style={{ width: pixelSize + 8, height: pixelSize + 8 }}
        onClick={onClick}
        title={`${meta.label} — ${meta.description}`}
      >
        {characterElement}
        <span
          className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-zinc-950 animate-pulse"
          style={{ backgroundColor: meta.dotColor }}
        />
      </div>
    );
  }

  // MODE 3: Detailed Status Card
  return (
    <div
      className={`agent-status-card p-4 rounded-2xl bg-zinc-900/80 border border-zinc-800/90 shadow-xl flex items-center gap-4 ${
        onClick ? 'cursor-pointer hover:border-zinc-700' : ''
      } ${className}`}
      onClick={onClick}
    >
      <div className="w-16 h-16 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-center shrink-0 p-1">
        <AgentCharacter
          pose={animated ? undefined : meta.staticPose}
          animation={animated ? meta.animatedPose : undefined}
          theme={theme}
          size={56}
          showFurTexture
        />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: meta.dotColor }}
          />
          <h4 className="text-sm font-semibold text-white truncate">
            {customLabel || meta.label}
          </h4>
        </div>
        <p className="text-xs text-zinc-400 mt-1 line-clamp-2 leading-relaxed">
          {customDescription || meta.description}
        </p>
      </div>
    </div>
  );
};
