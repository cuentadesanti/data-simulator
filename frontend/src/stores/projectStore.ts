import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { enableMapSet } from 'immer';
import type { CreateProjectRequest, Project, ProjectVersion } from '../types/project';
import { projectsApi } from '../services/api';
import { useDAGStore } from './dagStore';

// Enable Immer support for Map and Set
enableMapSet();

// LocalStorage key for persisting current project
const CURRENT_PROJECT_KEY = 'data-simulator-current-project';

interface ProjectState {
  // Project list
  projects: Project[];
  isLoadingProjects: boolean;
  projectsError: string | null;

  // Current project
  currentProjectId: string | null;
  currentVersionId: string | null;

  // Dirty state (unsaved changes)
  hasUnsavedChanges: boolean;
  lastSavedState: string | null; // JSON snapshot for comparison

  // Sidebar UI
  sidebarOpen: boolean;
  expandedProjectIds: Set<string>;

  // Operation states
  isSaving: boolean;
  isDeleting: boolean;
}

interface ProjectActions {
  // Fetch operations
  fetchProjects: () => Promise<void>;
  restoreCurrentProject: () => Promise<void>;

  // Project operations
  selectProject: (projectId: string) => Promise<void>;
  selectVersion: (projectId: string, versionId: string) => Promise<void>;
  createProject: (name: string, description?: string) => Promise<Project>;
  deleteProject: (projectId: string) => Promise<void>;
  updateProject: (projectId: string, name: string, description?: string) => Promise<void>;

  // Version operations
  saveVersion: () => Promise<void>;
  fetchVersions: (projectId: string) => Promise<ProjectVersion[]>;

  // Dirty state
  setHasUnsavedChanges: (value: boolean) => void;
  markAsSaved: () => void;
  checkForChanges: () => boolean;

  // UI
  toggleSidebar: () => void;
  toggleProjectExpanded: (projectId: string) => void;
  closeSidebar: () => void;
  openSidebar: () => void;

  // Clear state
  clearCurrentProject: () => void;
}

export const useProjectStore = create<ProjectState & ProjectActions>()(
  immer((set, get) => ({
    // Initial state
    projects: [],
    isLoadingProjects: false,
    projectsError: null,
    currentProjectId: null,
    currentVersionId: null,
    hasUnsavedChanges: false,
    lastSavedState: null,
    sidebarOpen: true,
    expandedProjectIds: new Set<string>(),
    isSaving: false,
    isDeleting: false,

    // Fetch all projects
    fetchProjects: async () => {
      set((state) => {
        state.isLoadingProjects = true;
        state.projectsError = null;
      });

      try {
        const projects = await projectsApi.list();
        set((state) => {
          state.projects = projects;
          state.isLoadingProjects = false;
        });
      } catch (error) {
        set((state) => {
          state.projectsError = error instanceof Error ? error.message : 'Failed to load projects';
          state.isLoadingProjects = false;
        });
      }
    },

    // Restore current project from localStorage
    restoreCurrentProject: async () => {
      const savedProjectId = localStorage.getItem(CURRENT_PROJECT_KEY);
      if (!savedProjectId) return;

      try {
        await get().selectProject(savedProjectId);
      } catch (error) {
        // Project might have been deleted, clear the saved state
        localStorage.removeItem(CURRENT_PROJECT_KEY);
        console.warn('Failed to restore project:', error);
      }
    },

    // Select a project and load its current version
    selectProject: async (projectId: string) => {
      const dagStore = useDAGStore.getState();

      try {
        const project = await projectsApi.get(projectId);

        // Load the DAG if available
        if (project.current_dag) {
          dagStore.importDAG(project.current_dag);
        } else {
          dagStore.clearDAG();
        }

        // Save the current state as the "saved" snapshot
        const dagSnapshot = JSON.stringify(dagStore.exportDAG());

        set((state) => {
          state.currentProjectId = projectId;
          state.currentVersionId = project.current_version?.id || null;
          state.hasUnsavedChanges = false;
          state.lastSavedState = dagSnapshot;
          // Expand the project in the sidebar
          state.expandedProjectIds.add(projectId);
        });

        // Persist to localStorage
        localStorage.setItem(CURRENT_PROJECT_KEY, projectId);
      } catch (error) {
        console.error('Failed to load project:', error);
        throw error;
      }
    },

    // Select a specific version
    selectVersion: async (projectId: string, versionId: string) => {
      const dagStore = useDAGStore.getState();

      try {
        const version = await projectsApi.getVersion(projectId, versionId);

        if (version.dag_definition) {
          dagStore.importDAG(version.dag_definition);
        } else {
          dagStore.clearDAG();
        }

        const dagSnapshot = JSON.stringify(dagStore.exportDAG());

        set((state) => {
          state.currentProjectId = projectId;
          state.currentVersionId = versionId;
          state.hasUnsavedChanges = false;
          state.lastSavedState = dagSnapshot;
        });
      } catch (error) {
        console.error('Failed to load version:', error);
        throw error;
      }
    },

    // Create a new project (starts with empty DAG)
    createProject: async (name: string, description?: string) => {
      const dagStore = useDAGStore.getState();

      // Clear the current DAG to start fresh
      dagStore.clearDAG();

      // Get the empty DAG state
      const dag = dagStore.exportDAG();

      const payload: CreateProjectRequest = {
        name,
        description,
      };
      if (dag.nodes.length > 0) {
        payload.dag_definition = dag;
      }

      const project = await projectsApi.create(payload);

      // Refresh project list
      await get().fetchProjects();

      // Select the new project
      const dagSnapshot = JSON.stringify(dag);
      set((state) => {
        state.currentProjectId = project.id;
        state.currentVersionId = project.current_version?.id || null;
        state.hasUnsavedChanges = false;
        state.lastSavedState = dagSnapshot;
        state.expandedProjectIds.add(project.id);
      });

      return project;
    },

    // Delete a project
    deleteProject: async (projectId: string) => {
      set((state) => {
        state.isDeleting = true;
      });

      try {
        await projectsApi.delete(projectId);

        set((state) => {
          state.projects = state.projects.filter((p) => p.id !== projectId);
          state.expandedProjectIds.delete(projectId);

          // Clear current if deleted
          if (state.currentProjectId === projectId) {
            state.currentProjectId = null;
            state.currentVersionId = null;
            state.hasUnsavedChanges = false;
            state.lastSavedState = null;
          }

          state.isDeleting = false;
        });
      } catch (error) {
        set((state) => {
          state.isDeleting = false;
        });
        throw error;
      }
    },

    // Update project metadata
    updateProject: async (projectId: string, name: string, description?: string) => {
      const updated = await projectsApi.update(projectId, { name, description });

      set((state) => {
        const index = state.projects.findIndex((p) => p.id === projectId);
        if (index !== -1) {
          state.projects[index] = { ...state.projects[index], ...updated };
        }
      });
    },

    // Save current DAG as new version
    saveVersion: async () => {
      const { currentProjectId } = get();
      if (!currentProjectId) {
        throw new Error('No project selected');
      }

      set((state) => {
        state.isSaving = true;
      });

      try {
        const dagStore = useDAGStore.getState();
        const dag = dagStore.exportDAG();

        const version = await projectsApi.createVersion(currentProjectId, { dag_definition: dag });

        // Update local state
        const dagSnapshot = JSON.stringify(dag);

        set((state) => {
          state.currentVersionId = version.id;
          state.hasUnsavedChanges = false;
          state.lastSavedState = dagSnapshot;
          state.isSaving = false;

          // Update the project's current version in the list
          const project = state.projects.find((p) => p.id === currentProjectId);
          if (project) {
            project.current_version = version;
            project.updated_at = new Date().toISOString();
          }
        });

        // Refresh project to get updated version list
        await get().fetchProjects();
      } catch (error) {
        set((state) => {
          state.isSaving = false;
        });
        throw error;
      }
    },

    // Fetch versions for a project
    fetchVersions: async (projectId: string) => {
      const versions = await projectsApi.listVersions(projectId);

      // Update the project's versions in the list
      set((state) => {
        const project = state.projects.find((p) => p.id === projectId);
        if (project) {
          project.versions = versions;
        }
      });

      return versions;
    },

    // Set unsaved changes flag
    setHasUnsavedChanges: (value: boolean) => {
      set((state) => {
        state.hasUnsavedChanges = value;
      });
    },

    // Mark current state as saved
    markAsSaved: () => {
      const dagStore = useDAGStore.getState();
      const dagSnapshot = JSON.stringify(dagStore.exportDAG());

      set((state) => {
        state.hasUnsavedChanges = false;
        state.lastSavedState = dagSnapshot;
      });
    },

    // Check if DAG has changed from saved state
    checkForChanges: () => {
      const { lastSavedState, currentProjectId } = get();
      if (!currentProjectId || !lastSavedState) {
        return false;
      }

      const dagStore = useDAGStore.getState();
      const currentState = JSON.stringify(dagStore.exportDAG());

      return currentState !== lastSavedState;
    },

    // Toggle sidebar visibility
    toggleSidebar: () => {
      set((state) => {
        state.sidebarOpen = !state.sidebarOpen;
      });
    },

    closeSidebar: () => {
      set((state) => {
        state.sidebarOpen = false;
      });
    },

    openSidebar: () => {
      set((state) => {
        state.sidebarOpen = true;
      });
    },

    // Toggle project expansion
    toggleProjectExpanded: (projectId: string) => {
      set((state) => {
        if (state.expandedProjectIds.has(projectId)) {
          state.expandedProjectIds.delete(projectId);
        } else {
          state.expandedProjectIds.add(projectId);
        }
      });
    },

    // Clear current project selection
    clearCurrentProject: () => {
      set((state) => {
        state.currentProjectId = null;
        state.currentVersionId = null;
        state.hasUnsavedChanges = false;
        state.lastSavedState = null;
      });
      localStorage.removeItem(CURRENT_PROJECT_KEY);
    },
  }))
);

// Selectors
export const selectProjects = (state: ProjectState & ProjectActions) => state.projects;
export const selectCurrentProjectId = (state: ProjectState & ProjectActions) =>
  state.currentProjectId;
export const selectCurrentVersionId = (state: ProjectState & ProjectActions) =>
  state.currentVersionId;
export const selectHasUnsavedChanges = (state: ProjectState & ProjectActions) =>
  state.hasUnsavedChanges;
export const selectSidebarOpen = (state: ProjectState & ProjectActions) => state.sidebarOpen;
export const selectExpandedProjectIds = (state: ProjectState & ProjectActions) =>
  state.expandedProjectIds;
export const selectIsLoadingProjects = (state: ProjectState & ProjectActions) =>
  state.isLoadingProjects;
export const selectIsSaving = (state: ProjectState & ProjectActions) => state.isSaving;
export const selectIsDeleting = (state: ProjectState & ProjectActions) => state.isDeleting;

// Get current project from list
export const selectCurrentProject = (state: ProjectState & ProjectActions) => {
  if (!state.currentProjectId) return null;
  return state.projects.find((p) => p.id === state.currentProjectId) || null;
};

// Subscribe to DAG changes to update unsaved changes status
useDAGStore.subscribe(() => {
  const projectStore = useProjectStore.getState();

  // Only check if we have a project loaded
  if (projectStore.currentProjectId) {
    const hasChanges = projectStore.checkForChanges();

    // Only update if value changed to avoid infinite loops
    if (hasChanges !== projectStore.hasUnsavedChanges) {
      projectStore.setHasUnsavedChanges(hasChanges);
    }
  }
});
