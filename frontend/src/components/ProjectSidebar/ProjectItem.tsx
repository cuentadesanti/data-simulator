import { useState, useRef, useEffect } from 'react';
import type { Project } from '../../types/project';
import {
  useProjectStore,
  selectCurrentProjectId,
  selectCurrentVersionId,
  selectExpandedProjectIds,
  selectHasUnsavedChanges,
} from '../../stores/projectStore';
import { VersionItem } from './VersionItem';

interface ProjectItemProps {
  project: Project;
}

export function ProjectItem({ project }: ProjectItemProps) {
  const currentProjectId = useProjectStore(selectCurrentProjectId);
  const currentVersionId = useProjectStore(selectCurrentVersionId);
  const expandedProjectIds = useProjectStore(selectExpandedProjectIds);
  const hasUnsavedChanges = useProjectStore(selectHasUnsavedChanges);
  const selectProject = useProjectStore((s) => s.selectProject);
  const deleteProject = useProjectStore((s) => s.deleteProject);
  const updateProject = useProjectStore((s) => s.updateProject);
  const toggleProjectExpanded = useProjectStore((s) => s.toggleProjectExpanded);
  const fetchVersions = useProjectStore((s) => s.fetchVersions);

  const [showMenu, setShowMenu] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(project.name);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const isSelected = currentProjectId === project.id;
  const isExpanded = expandedProjectIds.has(project.id);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showMenu]);

  // Focus input when editing
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  // Fetch versions when expanded
  useEffect(() => {
    if (isExpanded && !project.versions) {
      fetchVersions(project.id);
    }
  }, [isExpanded, project.id, project.versions, fetchVersions]);

  const handleSelectProject = async () => {
    if (isSelected) return;

    // Warn about unsaved changes
    if (hasUnsavedChanges) {
      const confirmed = window.confirm(
        'You have unsaved changes. Do you want to discard them and switch projects?'
      );
      if (!confirmed) return;
    }

    try {
      await selectProject(project.id);
    } catch (error) {
      console.error('Failed to select project:', error);
    }
  };

  const handleToggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    toggleProjectExpanded(project.id);
  };

  const handleRename = () => {
    setShowMenu(false);
    setIsEditing(true);
    setEditName(project.name);
  };

  const handleSaveRename = async () => {
    if (editName.trim() && editName !== project.name) {
      try {
        await updateProject(project.id, editName.trim());
      } catch (error) {
        console.error('Failed to rename project:', error);
      }
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveRename();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
      setEditName(project.name);
    }
  };

  const handleDelete = async () => {
    setShowDeleteConfirm(false);
    setIsDeleting(true);
    try {
      await deleteProject(project.id);
    } catch (error) {
      console.error('Failed to delete project:', error);
    }
    setIsDeleting(false);
  };

  return (
    <div className={`${isDeleting ? 'opacity-50 pointer-events-none' : ''}`}>
      {/* Project header row */}
      <div
        className={`
          flex items-center gap-1 px-2 py-1.5 cursor-pointer group
          ${isSelected ? 'bg-blue-50' : 'hover:bg-gray-100'}
        `}
        onClick={handleSelectProject}
      >
        {/* Expand/collapse toggle */}
        <button
          onClick={handleToggleExpand}
          className="p-0.5 hover:bg-gray-200 rounded flex-shrink-0"
        >
          <svg
            className={`w-3 h-3 text-gray-500 transition-transform ${
              isExpanded ? 'rotate-90' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        {/* Project name */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <input
              ref={inputRef}
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={handleSaveRename}
              onKeyDown={handleKeyDown}
              className="w-full px-1 py-0.5 text-sm border border-blue-400 rounded outline-none"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span
              className={`text-sm truncate block ${
                isSelected ? 'text-blue-700 font-medium' : 'text-gray-700'
              }`}
            >
              {project.name}
            </span>
          )}
        </div>

        {/* Menu button */}
        <div ref={menuRef} className="relative flex-shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className="p-1 opacity-0 group-hover:opacity-100 hover:bg-gray-200 rounded"
          >
            <svg className="w-3 h-3 text-gray-500" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="5" r="2" />
              <circle cx="12" cy="12" r="2" />
              <circle cx="12" cy="19" r="2" />
            </svg>
          </button>

          {/* Dropdown menu */}
          {showMenu && (
            <div className="absolute right-0 top-full mt-1 w-32 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
              <button
                onClick={handleRename}
                className="w-full px-3 py-1.5 text-left text-sm text-gray-700 hover:bg-gray-100"
              >
                Rename
              </button>
              <button
                onClick={() => {
                  setShowMenu(false);
                  setShowDeleteConfirm(true);
                }}
                className="w-full px-3 py-1.5 text-left text-sm text-red-600 hover:bg-red-50"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Version list (when expanded) */}
      {isExpanded && (
        <div className="ml-4 border-l border-gray-200">
          {project.versions?.map((version) => (
            <VersionItem
              key={version.id}
              projectId={project.id}
              version={version}
              isSelected={currentVersionId === version.id}
            />
          )) ?? <div className="px-3 py-2 text-xs text-gray-400">Loading versions...</div>}
        </div>
      )}

      {/* Delete confirmation dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 max-w-sm mx-4 shadow-xl">
            <h3 className="font-medium text-gray-900">Delete project?</h3>
            <p className="mt-2 text-sm text-gray-600">
              Are you sure you want to delete "{project.name}"? This action cannot be undone.
            </p>
            <div className="mt-4 flex gap-2 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="px-3 py-1.5 text-sm text-white bg-red-600 hover:bg-red-700 rounded"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
