import { useEffect, useMemo, useState } from 'react';
import {
  useProjectStore,
  selectProjects,
  selectCurrentProjectId,
  selectCurrentVersionId,
  selectCurrentProject,
  selectHasUnsavedChanges,
} from '../../stores/projectStore';
import { Dropdown, type DropdownOption } from '../common';
import { NewProjectDialog } from '../ProjectSidebar/NewProjectDialog';

export const ProjectSessionPicker = () => {
  const [showNewProjectDialog, setShowNewProjectDialog] = useState(false);
  const [versionError, setVersionError] = useState<string | null>(null);
  const projects = useProjectStore(selectProjects);
  const currentProjectId = useProjectStore(selectCurrentProjectId);
  const currentVersionId = useProjectStore(selectCurrentVersionId);
  const currentProject = useProjectStore(selectCurrentProject);
  const hasUnsavedChanges = useProjectStore(selectHasUnsavedChanges);
  const selectProject = useProjectStore((state) => state.selectProject);
  const selectVersion = useProjectStore((state) => state.selectVersion);
  const fetchVersions = useProjectStore((state) => state.fetchVersions);

  useEffect(() => {
    if (!currentProjectId || currentProject?.versions) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- clear error before async fetch
    setVersionError(null);
    void fetchVersions(currentProjectId).catch((error) => {
      console.error('Failed to load project versions:', error);
      setVersionError('Failed to load versions');
    });
  }, [currentProject?.versions, currentProjectId, fetchVersions]);

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()),
    [projects]
  );

  const versions = useMemo(() => {
    if (!currentProject) return [];
    if (currentProject.versions && currentProject.versions.length > 0) {
      return currentProject.versions;
    }
    if (currentProject.current_version) {
      return [currentProject.current_version];
    }
    return [];
  }, [currentProject]);

  const projectOptions = useMemo<DropdownOption<string>[]>(
    () => [
      { value: '', label: 'Select project' },
      ...sortedProjects.map((project) => ({
        value: project.id,
        label: project.name,
      })),
    ],
    [sortedProjects]
  );

  const versionOptions = useMemo<DropdownOption<string>[]>(() => {
    if (versions.length === 0) {
      return [{ value: '', label: 'No versions', disabled: true }];
    }
    return versions.map((version) => ({
      value: version.id,
      label: `v${version.version_number}${version.is_current ? ' (current)' : ''}`,
    }));
  }, [versions]);

  const handleProjectChange = async (projectId: string) => {
    if (!projectId || projectId === currentProjectId) return;
    if (hasUnsavedChanges) {
      const confirmed = window.confirm(
        'You have unsaved changes. Discard them and switch projects?'
      );
      if (!confirmed) return;
    }
    await selectProject(projectId);
  };

  const handleVersionChange = async (versionId: string) => {
    if (!currentProjectId || !versionId || versionId === currentVersionId) return;
    await selectVersion(currentProjectId, versionId);
  };

  return (
    <>
      <div className="flex items-center gap-2">
        <Dropdown
          options={projectOptions}
          value={currentProjectId ?? ''}
          onChange={(value) => void handleProjectChange(String(value))}
          size="sm"
          className="w-52"
        />
        <Dropdown
          options={versionOptions}
          value={currentVersionId ?? ''}
          onChange={(value) => void handleVersionChange(String(value))}
          disabled={!currentProjectId || versions.length === 0}
          size="sm"
          className="w-44"
        />
        {versionError && (
          <span className="text-xs text-red-500">{versionError}</span>
        )}
        <button
          type="button"
          onClick={() => setShowNewProjectDialog(true)}
          className="rounded-md border border-gray-200 bg-white px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          New
        </button>
      </div>
      <NewProjectDialog open={showNewProjectDialog} onClose={() => setShowNewProjectDialog(false)} />
    </>
  );
};
