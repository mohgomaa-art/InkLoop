import React, { useEffect, useState } from 'react';
import { ToastProvider } from './components/common/Toast';
import { Header } from './components/common/Header';
import { Sidebar, NavTab } from './components/common/Sidebar';
import { WorkspaceView } from './views/WorkspaceView';
import { StoryBibleView } from './views/StoryBibleView';
import { NarrativeTimelineView } from './views/NarrativeTimelineView';
import { GenerationStudioView } from './views/GenerationStudioView';
import { RunsHistoryView } from './views/RunsHistoryView';
import { VerificationLabView } from './views/VerificationLabView';
import { AssetLibraryView } from './views/AssetLibraryView';
import { CatalogueView } from './views/CatalogueView';
import { BudgetsView } from './views/BudgetsView';
import { BenchmarksView } from './views/BenchmarksView';
import { SettingsView } from './views/SettingsView';
import { AgentStudioView } from './views/AgentStudioView';
import { ManualEditorView } from './views/ManualEditorView';
import { CreativeDirectorView } from './views/CreativeDirectorView';
import { StyleCopierView } from './views/StyleCopierView';
import { CharacterCopierView } from './views/CharacterCopierView';
import { ObjectStudioView } from './views/ObjectStudioView';
import { apiClient } from './api/client';
import type { AgentStatusResponse } from './types/agent';
import { useReducedMotion } from './hooks/useReducedMotion';
import { executeViewTransition } from './utils/motion';

export const App: React.FC = () => {
  const [currentProject, setCurrentProject] = useState(() => {
    try {
      return localStorage.getItem('inkloop_current_project') || 'default_project';
    } catch {
      return 'default_project';
    }
  });
  const [projects, setProjects] = useState<Array<{ project_id: string; title: string; bible_version: number; canon_hash: string; characters?: string[] }>>([]);
  const [activeTab, setActiveTab] = useState<NavTab>('agent');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [agentMode, setAgentMode] = useState<AgentStatusResponse['mode'] | null>(null);
  const [activeRuns, setActiveRuns] = useState(0);

  // Initialize unified motion preferences & accessibility tokens
  useReducedMotion();

  // Keep the creator's last project as the startup selection. A project list
  // arriving later must not silently switch back to the default project.
  useEffect(() => {
    try {
      localStorage.setItem('inkloop_current_project', currentProject);
    } catch {
      // The selected project still works for this tab if storage is unavailable.
    }
  }, [currentProject]);

  // Sync with URL hash
  useEffect(() => {
    const handleHashChange = () => {
      // Canvas deep links keep the workspace route and a saved page query in
      // the hash, e.g. #/editor?page=page_123. Resolve the tab separately so
      // the editor can then load the exact persisted page ID.
      const hash = window.location.hash.replace('#/', '').split('?')[0] as NavTab;
      const validTabs: NavTab[] = [
        'workspace',
        'agent',
        'bible',
        'timeline',
        'studio',
        'batches',
        'verification',
        'assets',
        'catalogue',
        'budgets',
        'benchmarks',
        'settings',
        'editor',
        'creative',
        'location-studio',
        'style-copier',
        'character-copier',
        'object-studio',
      ];
      if (validTabs.includes(hash)) {
        setActiveTab(hash);
      }
    };

    if (window.location.hash) {
      handleHashChange();
    }
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleSelectTab = (tab: NavTab) => {
    executeViewTransition(() => {
      setActiveTab(tab);
      window.location.hash = `#/${tab}`;
    });
  };

  const refreshProjects = async (nextProject?: string) => {
    const next = await apiClient.listProjects();
    setProjects(next);
    if (nextProject) setCurrentProject(nextProject);
    else if (!next.some((item) => item.project_id === currentProject)) setCurrentProject(next[0]?.project_id || 'default_project');
  };

  // Initial telemetry load
  useEffect(() => {
    const fetchSystemState = async () => {
      try {
        const [health, agentStatus, projs] = await Promise.all([
          apiClient.getHealth().catch(() => null),
          apiClient.getAgentStatus().catch(() => null),
          apiClient.listProjects().catch(() => []),
        ]);

        if (health) {
          setBackendHealthy(true);
        } else {
          setBackendHealthy(false);
        }

        setAgentMode(agentStatus?.mode ?? null);

        if (projs && projs.length > 0) {
          setProjects(projs);
          const rememberedProject = (() => {
            try { return localStorage.getItem('inkloop_current_project'); } catch { return null; }
          })();
          if (rememberedProject && projs.some((p) => p.project_id === rememberedProject)) {
            setCurrentProject(rememberedProject);
          } else if (!projs.some((p) => p.project_id === currentProject)) {
            setCurrentProject(projs[0].project_id);
          }
        }
      } catch {
        setBackendHealthy(false);
      }
    };

    fetchSystemState();
  }, []);

  return (
    <ToastProvider>
      <div className="app-shell min-h-screen bg-ink-950 text-ink-100 flex flex-col font-sans">
        <Header
          currentProject={currentProject}
          onSelectProject={setCurrentProject}
          projects={projects}
          onCreateProject={async (title) => { const created = await apiClient.createProject(title); await refreshProjects(created.project_id); }}
          onRenameProject={async (title) => { const active = projects.find((item) => item.project_id === currentProject); if (!active) return; await apiClient.renameProject(currentProject, title, active.bible_version); await refreshProjects(); }}
          onArchiveProject={async () => { await apiClient.archiveProject(currentProject); await refreshProjects(); }}
          backendHealthy={backendHealthy}
          agentMode={agentMode}
          activeRunCount={activeRuns}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
        />

        <div className="app-body flex flex-1 overflow-hidden h-full">
          <div
            className={`transition-[width] overflow-hidden shrink-0 h-full flex flex-row ${
              sidebarOpen ? 'w-[268px]' : 'w-0'
            }`}
            style={{
              transitionDuration: 'var(--motion-duration-slow)',
              transitionTimingFunction: 'var(--motion-ease-standard)',
            }}
            aria-hidden={!sidebarOpen}
          >
            <Sidebar activeTab={activeTab} onSelectTab={handleSelectTab} onClose={() => setSidebarOpen(false)} />
          </div>

          <main className={`app-main flex-1 overflow-y-auto ${activeTab === 'agent' || activeTab === 'editor' ? 'p-0 overflow-hidden' : 'p-6 md:p-8'}`}>
            <div className={`${activeTab === 'agent' || activeTab === 'editor' ? 'h-full' : 'page-content max-w-7xl mx-auto pb-12'}`}>
              {activeTab === 'workspace' && (
                <WorkspaceView currentProject={currentProject} onNavigate={handleSelectTab} />
              )}
              <div className={activeTab === 'agent' ? 'h-full' : 'hidden'}>
                <AgentStudioView currentProject={currentProject} projects={projects} onSelectProject={setCurrentProject} />
              </div>
              {activeTab === 'creative' && (
                <CreativeDirectorView currentProject={currentProject} onNavigate={handleSelectTab} />
              )}
              {activeTab === 'location-studio' && (
                <CreativeDirectorView currentProject={currentProject} onNavigate={handleSelectTab} initialTab="locations" />
              )}
              {activeTab === 'style-copier' && (
                <StyleCopierView currentProject={currentProject} />
              )}
              {activeTab === 'character-copier' && (
                <CharacterCopierView currentProject={currentProject} />
              )}
              {activeTab === 'object-studio' && (
                <ObjectStudioView currentProject={currentProject} />
              )}
              <div className={activeTab === 'editor' ? 'h-full' : 'hidden'}>
                <ManualEditorView projectId={currentProject} />
              </div>
              {activeTab === 'bible' && (
                <StoryBibleView currentProject={currentProject} />
              )}
              {activeTab === 'timeline' && (
                <NarrativeTimelineView currentProject={currentProject} />
              )}
              {activeTab === 'studio' && (
                <GenerationStudioView currentProject={currentProject} />
              )}
              {activeTab === 'batches' && (
                <RunsHistoryView currentProject={currentProject} />
              )}
              {activeTab === 'verification' && (
                <VerificationLabView currentProject={currentProject} />
              )}
              {activeTab === 'assets' && (
                <AssetLibraryView currentProject={currentProject} />
              )}
              {activeTab === 'catalogue' && (
                <CatalogueView currentProject={currentProject} />
              )}
              {activeTab === 'budgets' && (
                <BudgetsView currentProject={currentProject} />
              )}
              {activeTab === 'benchmarks' && (
                <BenchmarksView currentProject={currentProject} />
              )}
              {activeTab === 'settings' && (
                <SettingsView currentProject={currentProject} />
              )}
            </div>
          </main>
        </div>
      </div>
    </ToastProvider>
  );
};

export default App;
