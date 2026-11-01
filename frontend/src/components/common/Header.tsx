import React, { useState } from 'react';
import { ChevronDown, CircleHelp, Cpu, PanelLeftClose, PanelLeftOpen, Plus, Pencil, Archive, FolderGit2 } from 'lucide-react';
import { Badge } from './Badge';
import { ProjectModal, ProjectModalMode } from './ProjectModal';
import { AgentStatus } from '../agent/character/AgentStatus';
import { MetaLogo } from '../agent/ModelLogos';
import type { AgentStatusResponse } from '../../types/agent';

interface HeaderProps {
  currentProject: string;
  onSelectProject: (projectId: string) => void;
  projects: Array<{ project_id: string; title?: string; bible_version: number; canon_hash: string }>;
  onCreateProject: (title: string) => Promise<void>;
  onRenameProject: (title: string) => Promise<void>;
  onArchiveProject: () => Promise<void>;
  backendHealthy: boolean | null;
  agentMode: AgentStatusResponse['mode'] | null;
  activeRunCount: number;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentProject,
  onSelectProject,
  projects,
  onCreateProject,
  onRenameProject,
  onArchiveProject,
  backendHealthy,
  agentMode,
  activeRunCount,
  sidebarOpen,
  onToggleSidebar,
}) => {
  const [modalMode, setModalMode] = useState<ProjectModalMode>(null);
  const activeProj = projects.find((p) => p.project_id === currentProject);

  return (
    <>
      <header className="app-header">
        <div className="header-brand flex items-center gap-3">
          <button
            className="icon-button sidebar-toggle"
            onClick={onToggleSidebar}
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            aria-expanded={sidebarOpen}
            title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            {sidebarOpen ? <PanelLeftClose /> : <PanelLeftOpen />}
          </button>
          <span className="brand-name">InkLoop</span>
        </div>

        <div className="header-project-maker flex items-center bg-zinc-900/90 hover:bg-zinc-800/60 border border-white/10 hover:border-white/20 rounded-lg shadow-sm transition pl-3 pr-1 py-1 gap-2">
          {/* Project Icon & Label */}
          <div className="flex items-center gap-2 select-none">
            <FolderGit2 size={14} className="text-zinc-400 shrink-0" />
            <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">
              Project
            </span>
          </div>

          {/* Project Dropdown Selector */}
          <div className="relative flex items-center">
            <select
              value={currentProject}
              onChange={(e) => onSelectProject(e.target.value)}
              aria-label="Select project"
              className="appearance-none bg-transparent text-white font-medium text-xs pr-5 pl-0.5 focus:outline-none cursor-pointer max-w-[220px] truncate"
            >
              {projects.length === 0 && (
                <option value={currentProject} className="bg-zinc-900 text-white">
                  {currentProject}
                </option>
              )}
              {projects.map((p) => (
                <option key={p.project_id} value={p.project_id} className="bg-zinc-900 text-white">
                  {p.title || p.project_id} · v{p.bible_version}
                </option>
              ))}
            </select>
            <ChevronDown size={13} className="text-zinc-400 pointer-events-none absolute right-0" />
          </div>

          {/* Divider */}
          <div className="w-[1px] h-4 bg-white/10 mx-0.5" />

          {/* Project Management Actions */}
          <div className="flex items-center gap-0.5">
            <button
              type="button"
              className="w-7 h-7 flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/10 rounded-md transition-colors motion-interactive cursor-pointer"
              aria-label="Create project"
              title="Create new project"
              onClick={() => setModalMode('create')}
            >
              <Plus size={14} />
            </button>
            <button
              type="button"
              className="w-7 h-7 flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/10 rounded-md transition-colors motion-interactive cursor-pointer"
              aria-label="Rename project"
              title="Rename current project"
              onClick={() => setModalMode('rename')}
            >
              <Pencil size={13} />
            </button>
            <button
              type="button"
              className="w-7 h-7 flex items-center justify-center text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors motion-interactive cursor-pointer"
              aria-label="Archive project"
              title="Archive current project (history and assets are retained)"
              onClick={() => setModalMode('archive')}
            >
              <Archive size={13} />
            </button>
          </div>
        </div>

        <div className="header-status flex items-center gap-2.5">
          <AgentStatus
            mode="badge"
            state={
              activeRunCount > 0
                ? 'working'
                : backendHealthy === false
                ? 'sleeping'
                : 'idle'
            }
            theme="ink-dark"
          />
          <div className="connection-state">
            <span className={`status-dot ${backendHealthy === false ? 'offline' : backendHealthy === null ? 'checking' : ''}`} />
            <span>{backendHealthy === true ? 'Connected' : backendHealthy === false ? 'Offline' : 'Connecting'}</span>
          </div>
          <span className="header-status-divider" />
          <div
            className="provider-state flex items-center gap-1.5"
            title={
              agentMode === 'offline_explicit'
                ? 'Deterministic offline test mode is explicitly enabled.'
                : agentMode === 'live_configured'
                ? 'Meta Muse Spark 1.3 connected; active creative reasoning model.'
                : agentMode === 'provider_unavailable'
                ? 'No model provider credentials are configured.'
                : 'Checking Agent runtime configuration.'
            }
          >
            {agentMode === 'live_configured' ? (
              <MetaLogo className="w-3.5 h-3.5 text-[#0081FB]" />
            ) : (
              <Cpu />
            )}
            {agentMode === 'offline_explicit'
              ? 'Offline Mode'
              : agentMode === 'live_configured'
              ? 'Meta Muse Spark 1.3'
              : agentMode === 'provider_unavailable'
              ? 'Provider Unavailable'
              : 'Checking Mode'}
          </div>
          {activeRunCount > 0 && <Badge variant="info" size="sm" dot>{activeRunCount} active</Badge>}
          <button className="icon-button header-help" aria-label="Help"><CircleHelp /></button>
        </div>
      </header>

      <ProjectModal
        mode={modalMode}
        currentProject={currentProject}
        currentTitle={activeProj?.title}
        onClose={() => setModalMode(null)}
        onCreate={onCreateProject}
        onRename={onRenameProject}
        onArchive={onArchiveProject}
      />
    </>
  );
};
