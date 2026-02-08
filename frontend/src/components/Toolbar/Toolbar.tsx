import React, { useState } from 'react';
import { CheckCircle, Download, Upload, Trash2, Save, ArrowUpRight } from 'lucide-react';
import { SignInButton, UserButton, useAuth } from '@clerk/clerk-react';
import { useDAGStore, selectActiveMainTab } from '../../stores/dagStore';
import { useProjectStore } from '../../stores/projectStore';
import { dagApi, downloadBlob } from '../../services/api';
import { useToast } from '../common';
import { AddNodeDropdown } from './AddNodeDropdown';
import { GenerateButton } from './GenerateButton';
import { ValidationStatus } from './ValidationStatus';
import { isAuthBypassed } from '../../utils/auth';

import { NewProjectDialog } from '../ProjectSidebar/NewProjectDialog';

export const Toolbar: React.FC = () => {
  const { isSignedIn } = useAuth();
  const authBypassed = isAuthBypassed();
  const [isValidating, setIsValidating] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isNewProjectDialogOpen, setIsNewProjectDialogOpen] = useState(false);
  const [isSaveAsNewDialogOpen, setIsSaveAsNewDialogOpen] = useState(false);
  const [showStructuralChangeDialog, setShowStructuralChangeDialog] = useState(false);
  const [versionName, setVersionName] = useState('');
  const [versionDescription, setVersionDescription] = useState('');
  const [versionNameError, setVersionNameError] = useState<string | null>(null);
  const { addToast } = useToast();

  const {
    exportDAG,
    importDAG,
    clearDAG,
    setValidationErrors,
    setStructuredErrors,
    setPreviewData,
    setEdgeStatuses,
    setLastValidationResult,
  } = useDAGStore();

  const saveCurrentVersion = useProjectStore((s) => s.saveCurrentVersion);
  const saveNewVersion = useProjectStore((s) => s.saveNewVersion);
  const isSaving = useProjectStore((s) => s.isSaving);
  const hasUnsavedChanges = useProjectStore((s) => s.hasUnsavedChanges);
  const hasStructuralChanges = useProjectStore((s) => s.hasStructuralChanges);
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const currentVersionId = useProjectStore((s) => s.currentVersionId);

  const activeMainTab = useDAGStore(selectActiveMainTab);
  const isDagTab = activeMainTab === 'dag';

  const handleSaveCurrent = async () => {
    // If no project is selected, open the New Project dialog
    if (!currentProjectId) {
      setIsNewProjectDialogOpen(true);
      return;
    }

    try {
      await saveCurrentVersion();
      addToast('success', 'Project saved successfully');
    } catch (error) {
      addToast('error', 'Failed to save project');
      console.error(error);
    }
  };

  const handleSave = async () => {
    if (!currentProjectId) {
      setIsNewProjectDialogOpen(true);
      return;
    }

    if (!currentVersionId) {
      handleSaveAsNew();
      return;
    }

    if (hasStructuralChanges()) {
      setShowStructuralChangeDialog(true);
      return;
    }

    await handleSaveCurrent();
  };

  const handleSaveAsNew = async () => {
    if (!currentProjectId) {
      setIsNewProjectDialogOpen(true);
      return;
    }
    setVersionName('');
    setVersionDescription('');
    setVersionNameError(null);
    setIsSaveAsNewDialogOpen(true);
  };

  const handleSubmitSaveAsNew = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!versionName.trim()) {
      setVersionNameError('Version name is required');
      return;
    }

    try {
      await saveNewVersion(versionName.trim(), versionDescription.trim() || undefined);
      setIsSaveAsNewDialogOpen(false);
      addToast('success', 'New version created');
    } catch (error) {
      addToast('error', 'Failed to create new version');
      console.error(error);
    }
  };

  // Validate DAG
  const handleValidate = async () => {
    setIsValidating(true);
    setLastValidationResult('pending');
    try {
      const dag = exportDAG();
      const result = await dagApi.validate(dag);

      // Always update edge statuses from validation result
      setEdgeStatuses(result.edge_statuses || [], result.missing_edges || []);

      // If backend sanitized/migrated IDs, update local state
      if (result.sanitized_dag?.was_migrated) {
        importDAG(result.sanitized_dag);
      }

      if (result.valid) {
        setValidationErrors([]);
        setStructuredErrors([]);
        setLastValidationResult('valid');
        addToast('success', 'DAG is valid!');
      } else {
        setValidationErrors(result.errors);
        setStructuredErrors(result.structured_errors || []);
        setLastValidationResult('invalid');
        addToast('error', `Validation failed: ${result.errors.length} error(s)`);
      }
    } catch (error) {
      console.error('Validation error:', error);
      setEdgeStatuses([], []); // Clear edge statuses on error
      setLastValidationResult('invalid');
      addToast(
        'error',
        `Validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    } finally {
      setIsValidating(false);
    }
  };

  // Generate preview data
  const handlePreview = async () => {
    setIsPreviewing(true);
    try {
      const dag = exportDAG();
      const result = await dagApi.preview(dag);
      setPreviewData(result.data, result.columns);

      // If backend sanitized/migrated IDs, update local state
      if (result.sanitized_dag?.was_migrated) {
        importDAG(result.sanitized_dag);
      }

      addToast('success', `Preview generated: ${result.rows} rows`);
    } catch (error) {
      console.error('Preview error:', error);
      addToast(
        'error',
        `Preview failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    } finally {
      setIsPreviewing(false);
    }
  };

  // Export DAG to JSON
  const handleExportJSON = () => {
    try {
      const dag = exportDAG();
      const json = JSON.stringify(dag, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      downloadBlob(blob, 'dag-definition.json');
      addToast('success', 'DAG exported successfully');
    } catch (error) {
      console.error('Export error:', error);
      addToast(
        'error',
        `Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  };

  // Import DAG from JSON
  const handleImportJSON = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const dag = JSON.parse(text);
        importDAG(dag);
        addToast('success', 'DAG imported successfully!');
      } catch (error) {
        console.error('Import error:', error);
        addToast(
          'error',
          `Import failed: ${error instanceof Error ? error.message : 'Invalid JSON file'}`
        );
      }
    };
    input.click();
  };

  // Clear DAG with confirmation
  const handleClear = () => {
    if (window.confirm('Are you sure you want to clear the entire DAG? This cannot be undone.')) {
      clearDAG();
      addToast('info', 'DAG cleared');
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-2">
      <NewProjectDialog
        open={isNewProjectDialogOpen}
        onClose={() => setIsNewProjectDialogOpen(false)}
      />
      {isSaveAsNewDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setIsSaveAsNewDialogOpen(false)}
          />
          <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Save New Version</h2>
              <button
                onClick={() => setIsSaveAsNewDialogOpen(false)}
                className="p-1 hover:bg-gray-100 rounded text-gray-500"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <form onSubmit={handleSubmitSaveAsNew}>
              <div className="px-4 py-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Version name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={versionName}
                    onChange={(e) => {
                      setVersionName(e.target.value);
                      setVersionNameError(null);
                    }}
                    placeholder="e.g. Add income model"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={isSaving}
                    autoFocus
                  />
                  {versionNameError && (
                    <p className="text-sm text-red-600 mt-1">{versionNameError}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description <span className="text-gray-400">(optional)</span>
                  </label>
                  <textarea
                    value={versionDescription}
                    onChange={(e) => setVersionDescription(e.target.value)}
                    placeholder="What changed in this version?"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={3}
                    disabled={isSaving}
                  />
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => setIsSaveAsNewDialogOpen(false)}
                  className="px-3 py-1.5 text-gray-600 hover:text-gray-800"
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save New Version'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {showStructuralChangeDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowStructuralChangeDialog(false)}
          />
          <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Big Change Detected</h2>
              <button
                onClick={() => setShowStructuralChangeDialog(false)}
                className="p-1 hover:bg-gray-100 rounded text-gray-500"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <div className="px-4 py-4 text-sm text-gray-700">
              You added or removed nodes/edges. This is a big change. Do you want to save
              as a new version?
            </div>
            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200">
              <button
                type="button"
                onClick={async () => {
                  setShowStructuralChangeDialog(false);
                  await handleSaveCurrent();
                }}
                className="px-3 py-1.5 text-gray-600 hover:text-gray-800"
                disabled={isSaving}
              >
                Save Current Version
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowStructuralChangeDialog(false);
                  handleSaveAsNew();
                }}
                className="px-4 py-1.5 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
                disabled={isSaving}
              >
                Save as New Version
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="flex items-center gap-2">
        {/* DAG-specific controls - only show on DAG tab */}
        {isDagTab && (
          <>
            {/* Add Node Dropdown */}
            <AddNodeDropdown />

            {/* Divider */}
            <div className="h-6 w-px bg-gray-300" />

            {/* Save Split Button */}
            <div className="flex">
              <button
                onClick={handleSave}
                disabled={isSaving || (!!currentProjectId && !hasUnsavedChanges)}
                className="flex items-center gap-2 px-3 py-1.5 bg-green-600 text-white rounded-l hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                title={
                  !currentProjectId
                    ? 'Save as new project'
                    : !hasUnsavedChanges
                      ? 'No changes to save'
                      : 'Save current version'
                }
              >
                <Save size={16} />
                <span className="text-sm font-medium">{isSaving ? 'Saving...' : 'Save'}</span>
              </button>
              <button
                onClick={handleSaveAsNew}
                disabled={isSaving || (!!currentProjectId && !hasUnsavedChanges)}
                className="flex items-center px-2 py-1.5 bg-green-700 text-white rounded-r hover:bg-green-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                title={
                  !currentProjectId
                    ? 'Save as new project'
                    : !hasUnsavedChanges
                      ? 'No changes to save'
                      : 'Save as new version'
                }
              >
                <ArrowUpRight size={16} />
              </button>
            </div>

            {/* Validate Button */}
            <button
              onClick={handleValidate}
              disabled={isValidating}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              <CheckCircle size={16} />
              <span className="text-sm font-medium">
                {isValidating ? 'Validating...' : 'Validate'}
              </span>
            </button>
          </>
        )}

        {/* Generate (Split Button) replaces Preview */}
        <GenerateButton onGeneratePreview={handlePreview} isPreviewing={isPreviewing} />

        {/* Divider */}
        <div className="h-6 w-px bg-gray-300" />

        {/* Export JSON */}
        <button
          onClick={handleExportJSON}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
        >
          <Download size={16} />
          <span className="text-sm font-medium">Export JSON</span>
        </button>

        {/* Import JSON */}
        <button
          onClick={handleImportJSON}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
        >
          <Upload size={16} />
          <span className="text-sm font-medium">Import JSON</span>
        </button>

        {/* Clear Button */}
        <button
          onClick={handleClear}
          className="flex items-center gap-2 px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
        >
          <Trash2 size={16} />
          <span className="text-sm font-medium">Clear</span>
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Validation Status */}
        <ValidationStatus />

        {/* Auth */}
        <div className="ml-2 pl-2 border-l border-gray-200 flex items-center">
          {authBypassed && (
            <span className="px-2 py-1 text-xs font-medium rounded bg-amber-100 text-amber-800">
              Local Auth Bypass
            </span>
          )}
          {!authBypassed && !isSignedIn && (
            <SignInButton mode="modal">
              <button className="px-3 py-1.5 bg-gray-900 text-white text-sm font-medium rounded hover:bg-gray-800 transition-colors">
                Sign In
              </button>
            </SignInButton>
          )}
          {!authBypassed && isSignedIn && (
            <UserButton />
          )}
        </div>
      </div>
    </div>
  );
};
