import React, { useState } from 'react';
import {
  PanelLeftClose,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Layers,
  Wand2,
  BookOpen,
  GitFork,
  Compass,
  UserRound,
  Palette,
  FolderArchive,
  GalleryHorizontalEnd,
  ShieldCheck,
  Library,
  Coins,
  Activity,
  Sliders,
  BarChart3,
  MapPin,
  Package,
} from 'lucide-react';
import { TabCharacterIcon } from '../agent/character/TabCharacterIcon';
import { AgentLogo } from '../agent/character/AgentLogo';

export type NavTab =
  | 'workspace'
  | 'agent'
  | 'bible'
  | 'timeline'
  | 'studio'
  | 'batches'
  | 'verification'
  | 'assets'
  | 'catalogue'
  | 'budgets'
  | 'benchmarks'
  | 'settings'
  | 'editor'
  | 'creative'
  | 'style-copier'
  | 'character-copier'
  | 'location-studio'
  | 'object-studio';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  onClose: () => void;
}

// Map each tab to its unique, recognizable functional icon
const TAB_ICONS: Record<NavTab, React.ComponentType<{ className?: string; size?: number }>> = {
  agent: Sparkles,
  editor: Layers,
  studio: Wand2,
  bible: BookOpen,
  timeline: GitFork,
  creative: Compass,
  'character-copier': UserRound,
  'style-copier': Palette,
  assets: FolderArchive,
  batches: GalleryHorizontalEnd,
  verification: ShieldCheck,
  catalogue: Library,
  budgets: Coins,
  benchmarks: Activity,
  settings: Sliders,
  workspace: BarChart3,
  'location-studio': MapPin,
  'object-studio': Package,
};

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onSelectTab, onClose }) => {
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const mainSections: { label: string; items: { id: NavTab; label: string }[] }[] = [
    {
      label: 'Agent Co-Pilot',
      items: [{ id: 'agent', label: 'Create, Plan & Review' }],
    },
    {
      label: 'Canvas Studio',
      items: [
        { id: 'editor', label: 'Page Editor' },
        { id: 'studio', label: 'Generation Studio' },
      ],
    },
    {
      label: 'Story & Assets',
      items: [
        { id: 'bible', label: 'Story Bible & Canon' },
        { id: 'character-copier', label: 'Character Studio' },
        { id: 'object-studio', label: 'Object Studio' },
        { id: 'style-copier', label: 'Style Studio' },
        { id: 'location-studio', label: 'Location Studio' },
        { id: 'timeline', label: 'Continuity Timeline' },
        { id: 'creative', label: 'Story Builder' },
      ],
    },
    {
      label: 'Library & Publishing',
      items: [
        { id: 'assets', label: 'Asset Library' },
        { id: 'batches', label: 'Runs History' },
      ],
    },
  ];

  const advancedItems: { id: NavTab; label: string }[] = [
    { id: 'verification', label: 'Quality Inspector (Critic)' },
    { id: 'budgets', label: 'Studio Fuel & Costs' },
    { id: 'catalogue', label: 'Manga Encyclopedia' },
    { id: 'benchmarks', label: 'Drift Benchmarks' },
    { id: 'settings', label: 'System Diagnostics' },
    { id: 'workspace', label: 'Studio KPI' },
  ];

  const isAdvancedActive = advancedItems.some((item) => item.id === activeTab);

  return (
    <>
      <aside className="app-sidebar">
        <div className="sidebar-project-switcher">
          <div className="flex items-center gap-3">
            <AgentLogo
              variant="silhouette"
              size={44}
              theme="ink-dark"
            />
            <div className="sidebar-project-name">
              <strong className="text-sm font-bold text-white tracking-wide">InkLoop</strong>
            </div>
          </div>
          <button
            className="icon-button sidebar-close"
            onClick={onClose}
            aria-label="Close sidebar"
            title="Close sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {mainSections.map((section) => (
            <div className="nav-section" key={section.label}>
              <div className="nav-section-title">{section.label}</div>
              {section.items.map((item) => {
                const IconComponent = TAB_ICONS[item.id] || Sparkles;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id)}
                    className={`nav-item ${isActive ? 'active' : ''}`}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <div className={`nav-icon-box ${isActive ? 'active' : ''}`}>
                      <IconComponent size={18} className="nav-icon" />
                    </div>
                    <span className="nav-label">{item.label}</span>
                    {isActive && (
                      <div className="nav-active-pill" title="Studio Co-Pilot active">
                        <TabCharacterIcon tab={item.id} active size={24} />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          ))}

          {/* Collapsible Pro Tools Group with Smooth Grid Accordion */}
          <div className="nav-section">
            <button
              type="button"
              className="w-full flex items-center justify-between nav-section-title hover:text-white transition-colors py-1 text-left cursor-pointer select-none"
              onClick={() => setAdvancedOpen((open) => !open)}
              aria-expanded={advancedOpen || isAdvancedActive}
            >
              <span>Pro Tools</span>
              <span
                className="inline-flex items-center justify-center transition-transform duration-200"
                style={{
                  transform: advancedOpen || isAdvancedActive ? 'rotate(90deg)' : 'rotate(0deg)',
                  transitionTimingFunction: 'var(--motion-ease-standard)',
                }}
              >
                <ChevronRight size={14} />
              </span>
            </button>

            <div
              className={`motion-accordion-content ${
                advancedOpen || isAdvancedActive ? 'open' : 'closed'
              }`}
            >
              <div className="motion-accordion-inner space-y-1 mt-1">
                {advancedItems.map((item) => {
                  const IconComponent = TAB_ICONS[item.id] || Sliders;
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => onSelectTab(item.id)}
                      className={`nav-item ${isActive ? 'active' : ''}`}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <div className={`nav-icon-box ${isActive ? 'active' : ''}`}>
                        <IconComponent size={18} className="nav-icon" />
                      </div>
                      <span className="nav-label">{item.label}</span>
                      {isActive && (
                        <div className="nav-active-pill" title="Studio Co-Pilot active">
                          <TabCharacterIcon tab={item.id} active size={24} />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </nav>

      </aside>
    </>
  );
};
