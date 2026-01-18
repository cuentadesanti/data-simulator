import type { ProjectVersion } from '../../types/project';
import { useProjectStore, selectHasUnsavedChanges } from '../../stores/projectStore';

interface VersionItemProps {
  projectId: string;
  version: ProjectVersion;
  isSelected: boolean;
}

export function VersionItem({ projectId, version, isSelected }: VersionItemProps) {
  const hasUnsavedChanges = useProjectStore(selectHasUnsavedChanges);
  const selectVersion = useProjectStore((s) => s.selectVersion);

  const handleClick = async () => {
    if (isSelected) return;

    // Warn about unsaved changes
    if (hasUnsavedChanges) {
      const confirmed = window.confirm(
        'You have unsaved changes. Do you want to discard them and switch versions?'
      );
      if (!confirmed) return;
    }

    try {
      await selectVersion(projectId, version.id);
    } catch (error) {
      console.error('Failed to select version:', error);
    }
  };

  // Format relative time
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div
      onClick={handleClick}
      className={`
        flex items-center gap-2 px-3 py-1.5 cursor-pointer text-sm
        ${isSelected ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-100 text-gray-600'}
      `}
    >
      {/* Current version indicator */}
      {version.is_current && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0"
          title="Current version"
        />
      )}
      {!version.is_current && <span className="w-1.5 flex-shrink-0" />}

      {/* Version info */}
      <span className="font-medium">v{version.version_number}</span>
      <span className="text-xs text-gray-400 flex-1 truncate">
        {formatRelativeTime(version.created_at)}
      </span>
    </div>
  );
}
