import React, { useState, useEffect } from 'react';
import { Plus, Pencil, Archive, X, AlertCircle } from 'lucide-react';

export type ProjectModalMode = 'create' | 'rename' | 'archive' | null;

interface ProjectModalProps {
  mode: ProjectModalMode;
  currentProject: string;
  currentTitle?: string;
  onClose: () => void;
  onCreate: (title: string) => Promise<void>;
  onRename: (title: string) => Promise<void>;
  onArchive: () => Promise<void>;
}

export const ProjectModal: React.FC<ProjectModalProps> = ({
  mode,
  currentProject,
  currentTitle = '',
  onClose,
  onCreate,
  onRename,
  onArchive,
}) => {
  const [title, setTitle] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (mode === 'rename') {
      setTitle(currentTitle || currentProject);
    } else {
      setTitle('');
    }
    setError('');
  }, [mode, currentTitle, currentProject]);

  if (!mode) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const trimmed = title.trim();

    if ((mode === 'create' || mode === 'rename') && !trimmed) {
      setError('Please enter a project title');
      return;
    }

    try {
      setSubmitting(true);
      if (mode === 'create') {
        await onCreate(trimmed);
      } else if (mode === 'rename') {
        await onRename(trimmed);
      } else if (mode === 'archive') {
        await onArchive();
      }
      onClose();
    } catch (err: any) {
      setError(err?.message || err?.payload?.message || 'Operation failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-md bg-ink-900 border border-white/10 rounded-2xl shadow-2xl p-6 text-ink-100"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            {mode === 'create' && <Plus className="w-5 h-5 text-ink-400" />}
            {mode === 'rename' && <Pencil className="w-5 h-5 text-ink-400" />}
            {mode === 'archive' && <Archive className="w-5 h-5 text-ink-400" />}
            <h2 className="text-lg font-semibold text-white">
              {mode === 'create' && 'Create New Project'}
              {mode === 'rename' && 'Rename Project'}
              {mode === 'archive' && 'Archive Project'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-ink-400 hover:text-white hover:bg-ink-800 transition"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 text-sm text-rose-300 bg-rose-950/60 border border-rose-800/80 rounded-lg">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {mode === 'create' && (
            <div>
              <label htmlFor="create-project-title" className="block text-xs uppercase tracking-wider text-ink-400 font-medium mb-1">
                Project Title
              </label>
              <input
                id="create-project-title"
                type="text"
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. My comic project"
                className="w-full px-3 py-2 bg-ink-950 border border-white/10 rounded-lg text-sm text-white placeholder-ink-500 focus:outline-none focus:border-white/30"
              />
              <p className="mt-1 text-xs text-ink-500">
                A starter Story Bible with an example character will be initialized. You can edit its canon before creating your story.
              </p>
            </div>
          )}

          {mode === 'rename' && (
            <div>
              <label htmlFor="rename-project-title" className="block text-xs uppercase tracking-wider text-ink-400 font-medium mb-1">
                New Project Title
              </label>
              <input
                id="rename-project-title"
                type="text"
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 bg-ink-950 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-white/30"
              />
              <p className="mt-1 text-xs text-ink-500">
                The internal project identifier (<code>{currentProject}</code>) and Canon identity remain unchanged.
              </p>
            </div>
          )}

          {mode === 'archive' && (
            <div className="space-y-2">
              <p className="text-sm text-ink-300">
                Are you sure you want to archive <strong>{currentTitle || currentProject}</strong>?
              </p>
              <div className="p-3 bg-ink-950 border border-white/10 rounded-lg text-xs text-ink-400">
                This project will be hidden from the active list. All underlying files, generated assets, revision artifacts, and execution histories are permanently retained.
              </div>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-sm text-ink-400 hover:text-white transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm font-semibold bg-[#eee] hover:bg-white text-[#141414] rounded-lg transition disabled:opacity-50 flex items-center gap-2 shadow-sm"
            >
              {submitting ? 'Processing...' : (
                mode === 'create' ? 'Create Project' :
                mode === 'rename' ? 'Save Title' :
                'Confirm Archive'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
