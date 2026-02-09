import { Save, Share2, CheckCircle2 } from 'lucide-react';
import { UserButton } from '@clerk/clerk-react';
import { useProjectStore, selectCurrentProject } from '../../stores/projectStore';
import { useToast } from '../common';
import { useShareVersion } from '../../hooks/useShareVersion';
import { trackFeedbackLatencyOnNextPaint } from '../../services/telemetry';

export const GlobalHeader = () => {
  const saveCurrentVersion = useProjectStore((state) => state.saveCurrentVersion);
  const isSaving = useProjectStore((state) => state.isSaving);
  const hasUnsavedChanges = useProjectStore((state) => state.hasUnsavedChanges);
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const currentVersionId = useProjectStore((state) => state.currentVersionId);
  const currentProject = useProjectStore(selectCurrentProject);
  const { addToast } = useToast();
  const { isSharing, shareVersion } = useShareVersion();

  const handleSave = async () => {
    if (!currentProjectId) {
      addToast('info', 'Create a project first');
      return;
    }
    const started = performance.now();
    trackFeedbackLatencyOnNextPaint('project.save_current', started, {
      feedback_type: 'button_loading',
      user_initiated: true,
    });
    try {
      await saveCurrentVersion();
      addToast('success', 'Saved');
    } catch (error) {
      addToast('error', error instanceof Error ? error.message : 'Failed to save');
    }
  };

  const handleShare = async () => {
    await shareVersion(currentProjectId, currentVersionId);
  };

  return (
    <header className="flex h-12 items-center justify-between border-b border-gray-200 bg-white px-4">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-gray-900">
          {currentProject?.name ?? 'Task Workspace'}
        </h1>
        <span className="text-xs text-gray-400">Source → Transform → Model → Publish</span>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          {hasUnsavedChanges ? <Save size={14} /> : <CheckCircle2 size={14} />}
          {isSaving ? 'Saving...' : hasUnsavedChanges ? 'Save' : 'Saved'}
        </button>
        <button
          type="button"
          onClick={handleShare}
          disabled={isSharing}
          className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          <Share2 size={14} />
          Share
        </button>
        <UserButton />
      </div>
    </header>
  );
};
