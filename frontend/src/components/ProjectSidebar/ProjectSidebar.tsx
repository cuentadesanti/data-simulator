import { useEffect, useState } from 'react';
import {
  useProjectStore,
  selectProjects,
  selectSidebarOpen,
  selectIsLoadingProjects,
} from '../../stores/projectStore';
import { ProjectItem } from './ProjectItem';
import { NewProjectDialog } from './NewProjectDialog';

interface ProjectSidebarProps {
  initializeOnMount?: boolean;
}

export function ProjectSidebar({ initializeOnMount = true }: ProjectSidebarProps) {
  const projects = useProjectStore(selectProjects);
  const sidebarOpen = useProjectStore(selectSidebarOpen);
  const isLoading = useProjectStore(selectIsLoadingProjects);
  const fetchProjects = useProjectStore((s) => s.fetchProjects);
  const restoreCurrentProject = useProjectStore((s) => s.restoreCurrentProject);
  const toggleSidebar = useProjectStore((s) => s.toggleSidebar);

  const [showNewProjectDialog, setShowNewProjectDialog] = useState(false);

  // Fetch projects and restore current project on mount
  useEffect(() => {
    if (!initializeOnMount) return;
    const init = async () => {
      await fetchProjects();
      await restoreCurrentProject();
    };
    void init();
  }, [fetchProjects, initializeOnMount, restoreCurrentProject]);

  // Sort projects by updated_at descending
  const sortedProjects = [...projects].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  return (
    <>
      {/* Collapsed sidebar toggle */}
      {!sidebarOpen && (
        <button
          onClick={toggleSidebar}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-20 bg-white border border-l-0 border-gray-200 rounded-r-lg p-2 shadow-sm hover:bg-gray-50"
          title="Open projects panel"
        >
          <svg
            className="w-4 h-4 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      )}

      {/* Main sidebar */}
      <aside
        className={`
          flex-shrink-0 bg-gray-50 border-r border-gray-200 flex flex-col
          transition-all duration-200 ease-in-out
          ${sidebarOpen ? 'w-60' : 'w-0 overflow-hidden'}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-3 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-2">
            <button
              onClick={toggleSidebar}
              className="p-1 hover:bg-gray-100 rounded"
              title="Collapse sidebar"
            >
              <svg
                className="w-4 h-4 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <span className="font-medium text-sm text-gray-700">Projects</span>
          </div>
          <button
            onClick={() => setShowNewProjectDialog(true)}
            className="p-1 hover:bg-gray-100 rounded text-gray-600"
            title="New project"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
          </button>
        </div>

        {/* Project list */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <svg className="w-5 h-5 animate-spin text-gray-400" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
          ) : sortedProjects.length === 0 ? (
            <div className="px-3 py-8 text-center text-sm text-gray-500">
              <p>No projects yet</p>
              <button
                onClick={() => setShowNewProjectDialog(true)}
                className="mt-2 text-blue-600 hover:text-blue-700"
              >
                Create your first project
              </button>
            </div>
          ) : (
            <div className="py-1">
              {sortedProjects.map((project) => (
                <ProjectItem key={project.id} project={project} />
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* New Project Dialog */}
      <NewProjectDialog
        open={showNewProjectDialog}
        onClose={() => setShowNewProjectDialog(false)}
      />
    </>
  );
}
